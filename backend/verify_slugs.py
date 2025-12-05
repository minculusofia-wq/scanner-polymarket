
import httpx
import asyncio

async def check_slugs():
    url = "https://gamma-api.polymarket.com/markets?limit=100&active=true&closed=false"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url)
            data = resp.json()
            
            missing = 0
            total = len(data)
            
            for m in data:
                slug = m.get("slug")
                event_slug = m.get("events")[0].get("slug") if m.get("events") else None
                
                final_slug = slug or event_slug
                
                if not final_slug:
                    print(f"MISSING SLUG: ID={m.get('id')} Q={m.get('question')}")
                    missing += 1
                else:
                    # Optional: Print first few to verify format
                    if total > 95:
                        print(f"OK: {final_slug}")
            
            print(f"Total: {total}, Missing Slugs: {missing}")
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_slugs())
