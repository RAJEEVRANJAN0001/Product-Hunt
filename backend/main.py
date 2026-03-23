from fastapi import FastAPI, Query, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from ddgs import DDGS
import sqlite3
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

DB_FILE = "tools_v2.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tools (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            description TEXT,
            category TEXT,
            pricing TEXT,
            favicon TEXT,
            upvotes INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Initialize DB immediately
init_db()

def get_domain(url: str) -> str:
    try:
        parsed = urllib.parse.urlparse(url)
        return parsed.netloc
    except:
        return "example.com"

def enrich_and_save_tool(title: str, url: str, snippet: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Check if exists
    cursor.execute("SELECT id FROM tools WHERE url=?", (url,))
    if cursor.fetchone():
        conn.close()
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
    
    try:
        cursor.execute('''
            INSERT INTO tools (title, url, description, category, pricing, favicon, upvotes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (title, url, description, category, pricing, favicon, 0))
        conn.commit()
    except sqlite3.IntegrityError:
        pass # URL might have been inserted concurrently
    finally:
        conn.close()

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
    # Filter out listicles, domains that compile lists, and explicitly look for standard tools
    search_query = f"{q} official site AI tool software -blog -top -best -list -listicle -alternatives"
    try:
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(search_query, max_results=100))
    except Exception as e:
        logging.error(f"DDGS Error: {e}")
        raise HTTPException(status_code=500, detail="Search engine failed or rate limited.")

    if not raw_results:
        return []

    tools_data = []
    for i, r in enumerate(raw_results):
        tools_data.append(f"[{i}] Title: {r.get('title')} | URL: {r.get('href')} | Snippet: {r.get('body')}")
    
    prompt = "Analyze these AI tools and return a JSON array of objects (in the exact same order, 0 to N). For each tool, provide exactly 3 keys: 'category' (e.g. Video, Audio, Coding, Writing, Productivity, Other), 'pricing' (Free, Freemium, Paid, Unknown), and 'description' (a crisp 1-sentence summary). Ignore that they resemble search results, just evaluate each one.\n\n" + "\n".join(tools_data)

    enriched_data = []
    try:
        response = client.models.generate_content(model='gemini-1.5-flash', contents=prompt)
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        enriched_data = json.loads(clean_json)
    except Exception as e:
        logging.error(f"Batch Gemini Failed: {e}")

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    final_results = []
    
    for i, r in enumerate(raw_results):
        url = r.get('href', '')
        title = r.get('title', '')
        favicon = f"https://www.google.com/s2/favicons?domain={get_domain(url)}&sz=128"
        
        cat = "Other"
        pri = "Unknown"
        desc = r.get('body', '')
        
        if i < len(enriched_data) and isinstance(enriched_data, list):
            cat = enriched_data[i].get("category", "Other")
            pri = enriched_data[i].get("pricing", "Unknown")
            desc = enriched_data[i].get("description", desc)
        
        upvotes = 0
        tool_id = 0
        try:
            cursor.execute('''
                INSERT INTO tools (title, url, description, category, pricing, favicon, upvotes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (title, url, desc, cat, pri, favicon, 0))
            tool_id = cursor.lastrowid
        except sqlite3.IntegrityError:
            cursor.execute("SELECT id, upvotes FROM tools WHERE url=?", (url,))
            row = cursor.fetchone()
            if row:
                tool_id = row[0]
                upvotes = row[1]

        final_results.append({
            "id": tool_id, "title": title, "url": url,
            "description": desc, "category": cat,
            "pricing": pri, "favicon": favicon, "upvotes": upvotes
        })
        
    conn.commit()
    conn.close()
    return final_results

@app.get("/api/tools")
async def get_tools(
    search: Optional[str] = None,
    category: Optional[str] = None,
    pricing: Optional[str] = None,
    sort: Optional[str] = "highest_rated"
):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = "SELECT * FROM tools WHERE 1=1"
    params = []
    
    if search:
        query += " AND (title LIKE ? OR description LIKE ?)"
        search_term = f"%{search}%"
        params.extend([search_term, search_term])
        
    if category and category != "All":
        query += " AND category = ?"
        params.append(category)
        
    if pricing and pricing != "All":
        query += " AND pricing = ?"
        params.append(pricing)
        
    if sort == "highest_rated":
        query += " ORDER BY upvotes DESC, created_at DESC"
    else:
        query += " ORDER BY created_at DESC"
        
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

@app.post("/api/tools/{tool_id}/upvote")
async def upvote_tool(tool_id: int):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("UPDATE tools SET upvotes = upvotes + 1 WHERE id = ?", (tool_id,))
        conn.commit()
        
        cursor.execute("SELECT upvotes FROM tools WHERE id = ?", (tool_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {"message": "Upvoted", "upvotes": row[0]}
        raise HTTPException(status_code=404, detail="Tool not found")
    except Exception as e:
        logging.error(f"Upvote failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to upvote tool")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
