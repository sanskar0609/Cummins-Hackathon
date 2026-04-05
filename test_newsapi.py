import asyncio
import sys
import aiohttp
sys.path.append('c:/Users/SIDDHI SAPKAL/OneDrive/Desktop/ByteCoders/Cummins-Hackathon/backend')
from app.services.agents.demand_agent_service import fetch_news

async def main():
    intent1 = {"news_query": "induction stove"}
    intent2 = {"news_query": "india LPG"}
    async with aiohttp.ClientSession() as session:
        n1 = await fetch_news(session, intent1)
        print(f"Induction stove news count: {len(n1)}")
        print(n1[:2])
        n2 = await fetch_news(session, intent2)
        print(f"India LPG news count: {len(n2)}")
        print(n2[:2])

if __name__ == "__main__":
    asyncio.run(main())
