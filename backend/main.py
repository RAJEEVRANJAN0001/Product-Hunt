from fastapi import FastAPI, Query, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from ddgs import DDGS
import logging
import json
import urllib.parse
from typing import List, Optional
from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

# Setup Gemini API key
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    logging.warning("GEMINI_API_KEY not found in environment. Please set it in .env file.")
client = genai.Client(api_key=api_key)

app = FastAPI(title="AI Tools Finder API")

# Enable CORS for the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from datetime import datetime

tools_db = []

def get_domain(url: str) -> str:
    try:
        parsed = urllib.parse.urlparse(url)
        return parsed.netloc
    except:
        return "example.com"

def enrich_and_save_tool(title: str, url: str, snippet: str):
    # Check if exists
    if any(t['url'] == url for t in tools_db):
        return

    # Call Gemini to enrich
    prompt = f"""
    Analyze the following AI tool.
    Title: {title}
    URL: {url}
    Snippet: {snippet}
    
    Return a valid JSON object (NO markdown formatting, just raw JSON) with EXACTLY these 3 keys:
    - "category": choose ONE from [Video, Image, Audio, Writing, Coding, Automation, Productivity, Other]
    - "pricing": choose ONE from [Free, Freemium, Paid, Unknown]
    - "description": Write an engaging, crisp 1-sentence summary of what it does.
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt
        )
        # Strip potential markdown blocks if LLM adds them despite instructions
        clean_json = response.text.strip().removeprefix('```json').removesuffix('```').strip()
        data = json.loads(clean_json)
        
        category = data.get("category", "Other")
        pricing = data.get("pricing", "Unknown")
        description = data.get("description", snippet)
    except Exception as e:
        logging.error(f"Gemini Enrichment Failed for {url}: {e}")
        category = "Other"
        pricing = "Unknown"
        description = snippet

    favicon = f"https://www.google.com/s2/favicons?domain={get_domain(url)}&sz=128"
    
    tools_db.append({
        "id": len(tools_db) + 1,
        "title": title,
        "url": url,
        "description": description,
        "category": category,
        "pricing": pricing,
        "favicon": favicon,
        "upvotes": 0,
        "created_at": datetime.utcnow().isoformat()
    })

def run_scraping_job(topic: str):
    import time
    logging.info(f"Starting background scrape for topic: {topic}")
    search_query = f"{topic} ai tool software platform"
    try:
        with DDGS() as ddgs:
            ddgs_results = ddgs.text(search_query, max_results=15)
            for r in ddgs_results:
                title = r.get('title', '')
                url = r.get('href', '')
                snippet = r.get('body', '')
                if url:
                    enrich_and_save_tool(title, url, snippet)
                    time.sleep(5)  # 15 RPM free tier limit = 1 req per 4s minimum
    except Exception as e:
        logging.error(f"Scraping job failed: {e}")

@app.post("/api/admin/scrape")
async def start_scraping(topic: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_scraping_job, topic)
    return {"message": f"Started scraping for '{topic}' in the background."}

class SubmitToolRequest(BaseModel):
    url: str

@app.post("/api/tools/submit")
async def submit_tool(req: SubmitToolRequest):
    import requests
    from bs4 import BeautifulSoup
    try:
        response = requests.get(req.url, timeout=5)
        soup = BeautifulSoup(response.content, 'html.parser')
        title = soup.title.string.strip() if soup.title else req.url
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        snippet = meta_desc['content'].strip() if meta_desc and meta_desc.get('content') else ""
        enrich_and_save_tool(title, req.url, snippet)
        return {"message": "Tool submitted and enriched successfully"}
    except Exception as e:
        logging.error(f"Submit Tool Error: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to process URL: {str(e)}")

@app.get("/api/search")
async def live_search(q: str = Query(..., min_length=1)):
    prompt = f"""
    The user is searching for AI tools related to: "{q}".
    Provide a list of up to 6 highly relevant, real AI tools.
    Return a valid JSON array of objects (NO markdown formatting).
    Each object must have EXACTLY these keys:
    - "title": Name of the tool
    - "url": Official website URL (must be a valid https link)
    - "description": A crisp 1-sentence summary of what it does
    - "category": choose ONE from [Video, Image, Audio, Writing, Coding, Automation, Productivity, Other]
    - "pricing": choose ONE from [Free, Freemium, Paid, Unknown]
    """
    
    try:
        response = client.models.generate_content(model='gemini-1.5-flash', contents=prompt)
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        enriched_data = json.loads(clean_json)
    except Exception as e:
        logging.error(f"Gemini Search Failed ({e}). Falling back to DuckDuckGo.")
        enriched_data = []
        try:
            with DDGS() as ddgs:
                search_query = f"{q} official site AI tool software -blog -listicle"
                raw_results = list(ddgs.text(search_query, max_results=6))
                for r in raw_results:
                    enriched_data.append({
                        "title": r.get('title', 'Unknown Tool'),
                        "url": r.get('href', ''),
                        "description": r.get('body', ''),
                        "category": "Other",
                        "pricing": "Unknown"
                    })
        except Exception as ddg_err:
            logging.error(f"DDGS Fallback Failed: {ddg_err}")
            raise HTTPException(status_code=500, detail="Search engine failed on both AI and Web. Please try again.")

    if not enriched_data:
        return []

    final_results = []
    for data in enriched_data:
        url = data.get('url', '')
        title = data.get('title', 'Unknown Tool')
        desc = data.get('description', '')
        cat = data.get('category', 'Other')
        pri = data.get('pricing', 'Unknown')
        favicon = f"https://www.google.com/s2/favicons?domain={get_domain(url)}&sz=128"

        existing_tool = next((t for t in tools_db if t['url'] == url), None)
        if existing_tool:
            final_results.append(existing_tool)
        else:
            new_tool = {
                "id": len(tools_db) + 1,
                "title": title,
                "url": url,
                "description": desc,
                "category": cat,
                "pricing": pri,
                "favicon": favicon,
                "upvotes": 0,
                "created_at": datetime.utcnow().isoformat()
            }
            tools_db.append(new_tool)
            final_results.append(new_tool)
            
    return final_results

@app.get("/api/tools")
async def get_tools(
    search: Optional[str] = None,
    category: Optional[str] = None,
    pricing: Optional[str] = None,
    sort: Optional[str] = "highest_rated"
):
    filtered_tools = tools_db.copy()
    
    if search:
        search_lower = search.lower()
        filtered_tools = [t for t in filtered_tools if search_lower in str(t.get('title', '')).lower() or search_lower in str(t.get('description', '')).lower()]
        
    if category and category != "All":
        filtered_tools = [t for t in filtered_tools if t['category'] == category]
        
    if pricing and pricing != "All":
        filtered_tools = [t for t in filtered_tools if t['pricing'] == pricing]
        
    if sort == "highest_rated":
        filtered_tools.sort(key=lambda x: (x['upvotes'], x['created_at']), reverse=True)
    else:
        filtered_tools.sort(key=lambda x: x['created_at'], reverse=True)
        
    return filtered_tools

@app.post("/api/tools/{tool_id}/upvote")
async def upvote_tool(tool_id: int):
    try:
        tool = next((t for t in tools_db if t['id'] == tool_id), None)
        if tool:
            tool['upvotes'] = int(tool.get('upvotes', 0)) + 1
            return {"message": "Upvoted", "upvotes": tool['upvotes']}
        raise HTTPException(status_code=404, detail="Tool not found")
    except Exception as e:
        logging.error(f"Upvote failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to upvote tool")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
