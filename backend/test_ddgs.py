from duckduckgo_search import DDGS

try:
    with DDGS() as ddgs:
        results = ddgs.text("Tata Motors product catalog", max_results=5)
        for r in results:
            print(f"Title: {r['title']}")
except Exception as e:
    print(f"FAILED: {e}")
