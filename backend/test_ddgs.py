from duckduckgo_search import DDGS

try:
    with DDGS() as ddgs:
        results = ddgs.text("video generation ai tool software", max_results=2)
        print("RESULTS:", list(results))
except Exception as e:
    print("ERROR:", e)
