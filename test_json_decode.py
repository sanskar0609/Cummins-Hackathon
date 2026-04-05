import asyncio
import sys
import json
sys.path.append('c:/Users/SIDDHI SAPKAL/OneDrive/Desktop/ByteCoders/Cummins-Hackathon/backend')
from app.services.agents.demand_agent_service import *
from app.core.gemini_rotator import async_generate_with_retry

async def main():
    intent = await extract_intent("demand for induction stove")
    print(f"Intent parsed: {intent.get('primary_product')}")
    prompt = f"Today is test.\nYou are a supply chain demand analyst.\nRespond ONLY with JSON:\n{{\n\"demand_trend_pct\": 0\n}}"
    try:
        res = await async_generate_with_retry(prompt)
        print("Raw Gemini Response Bytes:", res.encode('utf-8'))
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    asyncio.run(main())
