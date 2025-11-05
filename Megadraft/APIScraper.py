import asyncio
import aiohttp
import time
from urllib.parse import quote
import sqlite3
import dBManager
import cardhelpers as ch


API_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiIsImtpZCI6IjI4YTMxOGY3LTAwMDAtYTFlYi03ZmExLTJjNzQzM2M2Y2NhNSJ9.eyJpc3MiOiJzdXBlcmNlbGwiLCJhdWQiOiJzdXBlcmNlbGw6Z2FtZWFwaSIsImp0aSI6Ijg1MjVhZDQyLTgzMmEtNDMxNS04NDJhLWNjZDMxZTNmOTFlOCIsImlhdCI6MTc2MTY4NDAxNywic3ViIjoiZGV2ZWxvcGVyL2VhY2E4OWQzLWUyYjYtZDU2NC1iNTQ2LWMxMzY4NTZkNzA5OCIsInNjb3BlcyI6WyJyb3lhbGUiXSwibGltaXRzIjpbeyJ0aWVyIjoiZGV2ZWxvcGVyL3NpbHZlciIsInR5cGUiOiJ0aHJvdHRsaW5nIn0seyJjaWRycyI6WyIxMzQuMTczLjU2LjIyNyIsIjEzNC4xNzMuMTkyLjc2Il0sInR5cGUiOiJjbGllbnQifV19.v-biGRJboJybMK0XE7Vn8vv8zVV4o5RCNfjrhUiLUuhMrN4wwofPHf-xYzaY_F-h8t41s9lLQvEkBichWY_FvA"

HEADERS = {
    "Accept": "application/json",
    "Authorization": f"Bearer {API_TOKEN}"
}

# --- CONFIGURABLE LIMITS ---
MAX_CONCURRENT_REQUESTS = 8    # max simultaneous requests
REQUESTS_PER_SECOND = 110       # max requests per second
  # API rate limit
DBNAME = dBManager.dbname
BATCH_COMMIT_SIZE = 25          # commit every N battles per player

# --- RATE LIMITER ---
class RateLimiter:
    def __init__(self, rate_per_sec):
        self.delay = 1 / rate_per_sec
        self._lock = asyncio.Lock()
        self._last_time = 0

    async def wait(self):
        async with self._lock:
            now = time.time()
            elapsed = now - self._last_time
            wait_time = max(0, self.delay - elapsed)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            self._last_time = time.time()

# --- SAFE GET ---
async def safe_get(session, url, retries=3, timeout=30):
    for attempt in range(retries):
        try:
            async with session.get(url, headers=HEADERS, timeout=timeout) as resp:
                if resp.status == 429:
                    await asyncio.sleep(0.5)
                    continue
                resp.raise_for_status()
                return await resp.json()
        except Exception as e:
            print(f"Request failed ({attempt+1}/{retries}): {e}")
            await asyncio.sleep(1 + attempt)
    return None

# --- FETCH HELPERS ---
async def fetch_top_clans(session, limit=10):
    url = f"https://api.clashroyale.com/v1/locations/global/rankings/clans?limit={limit}"
    data = await safe_get(session, url)
    return data["items"] if data else []

async def fetch_clan_members(session, clan_tag):
    encoded = quote(clan_tag)
    url = f"https://api.clashroyale.com/v1/clans/{encoded}/members"
    data = await safe_get(session, url)
    return data["items"] if data else []

async def fetch_battlelog(session, player_tag):
    encoded = quote(player_tag)
    url = f"https://api.clashroyale.com/v1/players/{encoded}/battlelog"
    data = await safe_get(session, url)
    return data if data else []

# --- FILTER & EXTRACT ---
def is_mega_draft(battle):
    return battle.get("deckSelection", "").upper() == "COLLECTION" and battle.get("gameMode", {}).get('name') == 'Ladder'

def extract_battle_data(battle):
    team = battle["team"][0]
    opp = battle["opponent"][0]
    tdeck = [ch.name_to_id[c["name"].lower()] for c in team.get("cards", [])]
    odeck = [ch.name_to_id[c["name"].lower()] for c in opp.get("cards", [])]

    winner = team if team["crowns"] > opp["crowns"] else opp
    wtower_healths = (winner.get("princessTowersHitPoints") or []) + [winner.get("kingTowerHitPoints", 0)]
    wlowtowerhealth = 0
    for i in range(abs(team["crowns"] - opp["crowns"])):
        wlowtowerhealth += min(wtower_healths)
        wtower_healths.remove(min(wtower_healths))
    if winner != team:
        wlowtowerhealth *= -1

    battle_id = f"{team['tag']}_{battle['battleTime']}"
    return (battle_id, wlowtowerhealth, str(tdeck), str(odeck))

# --- WORKER ---
async def worker(name, queue, session, rate_limiter, con):
    cur = con.cursor()
    while True:
        player_tag = await queue.get()
        if player_tag is None:
            queue.task_done()
            break

        await rate_limiter.wait()
        battles = await fetch_battlelog(session, player_tag)
        inserted = 0
        batch_rows = []

        for b in battles:
            if is_mega_draft(b):
                row = extract_battle_data(b)
                batch_rows.append(row)
                inserted += 1

                if len(batch_rows) >= BATCH_COMMIT_SIZE:
                    cur.executemany(
                        "INSERT OR IGNORE INTO battles (battle_id, low_tower_dif, player_deck, opp_deck) VALUES (?, ?, ?, ?)",
                        batch_rows
                    )
                    con.commit()
                    batch_rows = []

        # Commit remaining rows
        if batch_rows:
            cur.executemany(
                "INSERT OR IGNORE INTO battles (battle_id, low_tower_dif, player_deck, opp_deck) VALUES (?, ?, ?, ?)",
                batch_rows
            )
            con.commit()

        print(f"[{name}] {player_tag} -> {inserted} Mega Draft battles")
        queue.task_done()

# --- MAIN ---
async def collect_megadraft_from_top_clans(top_n_clans=10):
    rate_limiter = RateLimiter(REQUESTS_PER_SECOND)
    queue = asyncio.Queue()
    con = sqlite3.connect(f'{DBNAME}.db')

    async with aiohttp.ClientSession() as session:
        # Get top clans
        clans = await fetch_top_clans(session, top_n_clans)
        if not clans:
            print("❌ Failed to fetch top clans")
            return

        all_players = []
        for c in clans:
            members = await fetch_clan_members(session, c["tag"])
            all_players.extend([m["tag"] for m in members])

        print(f"✅ Total players to fetch: {len(all_players)}")

        # Fill queue
        for tag in all_players:
            await queue.put(tag)

        # Start workers
        tasks = []
        for i in range(MAX_CONCURRENT_REQUESTS):
            tasks.append(asyncio.create_task(worker(f"W{i+1}", queue, session, rate_limiter, con)))

        # Wait until queue is fully processed
        await queue.join()

        # Stop workers
        for _ in range(MAX_CONCURRENT_REQUESTS):
            await queue.put(None)
        await asyncio.gather(*tasks)

    con.close()
    print("✅ Finished collecting Mega Draft battles!")

# --- RUN ---
if __name__ == "__main__":
    asyncio.run(collect_megadraft_from_top_clans(top_n_clans=100))