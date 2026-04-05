import asyncio
from app.services.agents.product_researcher import research_products_via_search
import os

# Set environment manually for test if needed, but it should pick from .env
async def test():
    print("Testing for Tata Motors...")
    result = await research_products_via_search("Tata Motors")
    print(f"Result count: {result.get('count')}")
    if result.get('skus'):
        for s in result['skus'][:3]:
            print(f"- {s['name']}")
    else:
        print("ERROR: No SKUs found!")
        print(f"Full result: {result}")

if __name__ == "__main__":
    asyncio.run(test())
