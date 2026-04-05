from ddgs import DDGS

try:
    with DDGS() as ddgs:
        # Example of new ddgs structure
        results = [r for r in ddgs.text("Tata Motors product catalog", max_results=5)]
        for r in results:
            print(f"Title: {r['title']}")
except Exception as e:
    import traceback
    traceback.print_exc()
