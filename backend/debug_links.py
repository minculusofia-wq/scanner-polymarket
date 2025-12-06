import asyncio
import httpx
import json

async def check_links():
    async with httpx.AsyncClient() as client:
        # Fetch a sample of markets
        print("Fetching markets...")
        url = "https://gamma-api.polymarket.com/markets?limit=100&active=true&closed=false"
        resp = await client.get(url)
        markets = resp.json()

        print(f"Checking {len(markets)} markets...")
        
        for market in markets[:50]:
            market_slug = market.get("slug", "")
            event_slug = ""
            if market.get("events"):
                event_slug = market["events"][0].get("slug", "")
            
            # Print if they differ
            if market_slug and event_slug and market_slug != event_slug:
                print(f"\n⚠️ Mismatch for: {market.get('question')}")
                print(f"Market Slug: {market_slug}")
                print(f"Event Slug : {event_slug}")
                
                # Test Market Slug
                url_m = f"https://polymarket.com/event/{market_slug}"
                try:
                    r_m = await client.head(url_m, follow_redirects=True)
                    print(f"   [Market URL] {r_m.status_code} {url_m}")
                except: pass
                
                # Test Event Slug
                url_e = f"https://polymarket.com/event/{event_slug}"
                try:
                    r_e = await client.head(url_e, follow_redirects=True)
                    print(f"   [Event URL ] {r_e.status_code} {url_e}")
                except: pass
            
            # Also test the one we currently use
            final_slug = market_slug or event_slug
            if not final_slug: continue
            
            # If we didn't test above
            if not (market_slug and event_slug and market_slug != event_slug):
                 url = f"https://polymarket.com/event/{final_slug}"
                 # ... (simplified check)

if __name__ == "__main__":
    asyncio.run(check_links())
