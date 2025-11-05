
import aiohttp
import asyncio
import time

API_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiIsImtpZCI6IjI4YTMxOGY3LTAwMDAtYTFlYi03ZmExLTJjNzQzM2M2Y2NhNSJ9.eyJpc3MiOiJzdXBlcmNlbGwiLCJhdWQiOiJzdXBlcmNlbGw6Z2FtZWFwaSIsImp0aSI6Ijg1MjVhZDQyLTgzMmEtNDMxNS04NDJhLWNjZDMxZTNmOTFlOCIsImlhdCI6MTc2MTY4NDAxNywic3ViIjoiZGV2ZWxvcGVyL2VhY2E4OWQzLWUyYjYtZDU2NC1iNTQ2LWMxMzY4NTZkNzA5OCIsInNjb3BlcyI6WyJyb3lhbGUiXSwibGltaXRzIjpbeyJ0aWVyIjoiZGV2ZWxvcGVyL3NpbHZlciIsInR5cGUiOiJ0aHJvdHRsaW5nIn0seyJjaWRycyI6WyIxMzQuMTczLjU2LjIyNyIsIjEzNC4xNzMuMTkyLjc2Il0sInR5cGUiOiJjbGllbnQifV19.v-biGRJboJybMK0XE7Vn8vv8zVV4o5RCNfjrhUiLUuhMrN4wwofPHf-xYzaY_F-h8t41s9lLQvEkBichWY_FvA"
PLAYER_TAG = "#8VCGL2UJ2"  # any valid tag
URL = f"https://api.clashroyale.com/v1/players/{PLAYER_TAG.replace('#', '%23')}"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

MAX_TOTAL_REQUESTS = 2000  # max requests to attempt
INITIAL_CONCURRENT = 1     # start with 1 concurrent request
STEP_CONCURRENT = 2        # increase by this step
MAX_CONCURRENT = 6        # safety stop

async def fetch(session, idx):
    """Send one request and return the status"""
    async with session.get(URL, headers=HEADERS) as resp:
        return resp.status

async def test_concurrent(session, concurrency, total_requests):
    """Launch `concurrency` requests in parallel until total_requests reached"""
    count = 0
    while count < total_requests:
        batch_size = min(concurrency, total_requests - count)
        tasks = [asyncio.create_task(fetch(session, count + i + 1)) for i in range(batch_size)]
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start_time
        req_per_sec = batch_size / elapsed
        print(f"Batch {batch_size} requests in {elapsed:.2f}s ≈ {req_per_sec:.2f} req/sec")
        results = await asyncio.gather(*tasks)
        count += batch_size

        if any(status == 429 for status in results):
            print(f"⚠️ Rate limit hit at concurrency={concurrency}")
            return False
    print(f"✅ Safe at concurrency={concurrency}")
    return True

async def find_max_rate():
    async with aiohttp.ClientSession() as session:
        concurrency = INITIAL_CONCURRENT
        while concurrency <= MAX_CONCURRENT:
            print(f"\nTesting concurrency={concurrency}...")
            ok = await test_concurrent(session, concurrency, total_requests=20)
            if ok:
                concurrency += STEP_CONCURRENT
            else:
                print(f"\n✅ Estimated safe max concurrency ≈ {concurrency - STEP_CONCURRENT}")
                return
        print(f"\n⚠️ Did not hit limit up to concurrency={MAX_CONCURRENT}")

if __name__ == "__main__":
    asyncio.run(find_max_rate())