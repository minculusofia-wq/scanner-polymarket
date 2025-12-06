import httpx
import asyncio
from datetime import datetime, timezone
import json

async def check_sniper():
    print("--- DEBUG SNIPER STRATEGY ---")
    now = datetime.now(timezone.utc)
    print(f"Current Time (UTC): {now}")
    
    async with httpx.AsyncClient() as client:
        # Fetch a few markets
        url = "https://gamma-api.polymarket.com/markets?limit=20&active=true&closed=false"
        try:
            resp = await client.get(url)
            markets = resp.json()
            print(f"Fetched {len(markets)} markets.")
            
            sniper_count = 0
            for m in markets:
                end_date_str = m.get("endDateIso")
                question = m.get("question")
                
                if not end_date_str:
                    continue
                    
                try:
                    # REPLICATE SIGNAL.PY LOGIC EXACTLY
                    end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                    delta = end_date - now
                    hours_left = delta.total_seconds() / 3600
                    
                    if 0 < hours_left < 24:
                        print(f"[MATCH] {question[:50]}...")
                        print(f"  Prices: {m.get('outcomePrices')}")
                        print(f"  Ends: {end_date_str} -> {hours_left:.2f} hours left")
                        sniper_count += 1
                    elif hours_left < 0:
                         pass # Expired
                    else:
                        # Print one that Failed to double check why
                        if sniper_count == 0 and hours_left < 48:
                             print(f"[SKIP] {question[:20]}... Ends in {hours_left:.2f}h")
                except Exception as e:
                    print(f"Error parsing {end_date_str}: {e}")
                    
            print(f"Total Sniper Matches Found: {sniper_count}")
            
        except Exception as e:
            print(f"API Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_sniper())
