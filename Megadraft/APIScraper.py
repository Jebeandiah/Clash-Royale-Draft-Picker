import asyncio
import aiohttp
import time
import boardGenerator as bg
from urllib.parse import quote
import sqlite3
import dBManager



API_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiIsImtpZCI6IjI4YTMxOGY3LTAwMDAtYTFlYi03ZmExLTJjNzQzM2M2Y2NhNSJ9.eyJpc3MiOiJzdXBlcmNlbGwiLCJhdWQiOiJzdXBlcmNlbGw6Z2FtZWFwaSIsImp0aSI6Ijg1MjVhZDQyLTgzMmEtNDMxNS04NDJhLWNjZDMxZTNmOTFlOCIsImlhdCI6MTc2MTY4NDAxNywic3ViIjoiZGV2ZWxvcGVyL2VhY2E4OWQzLWUyYjYtZDU2NC1iNTQ2LWMxMzY4NTZkNzA5OCIsInNjb3BlcyI6WyJyb3lhbGUiXSwibGltaXRzIjpbeyJ0aWVyIjoiZGV2ZWxvcGVyL3NpbHZlciIsInR5cGUiOiJ0aHJvdHRsaW5nIn0seyJjaWRycyI6WyIxMzQuMTczLjU2LjIyNyIsIjEzNC4xNzMuMTkyLjc2Il0sInR5cGUiOiJjbGllbnQifV19.v-biGRJboJybMK0XE7Vn8vv8zVV4o5RCNfjrhUiLUuhMrN4wwofPHf-xYzaY_F-h8t41s9lLQvEkBichWY_FvA"

HEADERS = {
    "Accept": "application/json",
    "Authorization": f"Bearer {API_TOKEN}"
}

# --- CONFIGURABLE LIMITS ---
MAX_CONCURRENT_REQUESTS = 9    # max simultaneous requests
REQUESTS_PER_SECOND = 120       # max requests per second

# --- ASYNC HELPERS ---

async def safe_get(session, url, retries=3, timeout=500):
    """GET request with retry on failure or 429"""
    for attempt in range(retries):
        try:
            async with session.get(url, headers=HEADERS, timeout=timeout) as resp:
                if resp.status == 429:
                    # wait a bit and retry
                    wait = 0.5
                    print(f"⚠️ Rate limited, waiting {wait}s...")
                    await asyncio.sleep(wait)
                    continue
                resp.raise_for_status()
                return await resp.json()
        except asyncio.TimeoutError:
            print(f"⏳ Timeout on {url}, retry {attempt+1}/{retries}")
        except Exception as e:
            print(f"⚠️ Request failed ({attempt+1}/{retries}): {e}")
        await asyncio.sleep(1 + attempt)
    return None

async def fetch_top_clans(session, limit=10):
    url = f"https://api.clashroyale.com/v1/locations/global/rankings/clans?limit={limit}"
    return (await safe_get(session, url))["items"]

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

# --- FILTER AND EXTRACT ---

def is_mega_draft(battle):
    return battle.get("deckSelection", "").upper() == "PICK"

def extract_battle_data(battle):
    team = battle["team"][0]
    opp = battle["opponent"][0]

    tdeck = [bg.card_str_to_id(c["name"]) for c in team.get("cards", [])]
    odeck = [bg.card_str_to_id(c["name"]) for c in opp.get("cards", [])]
    # print(team.get("cards", []))
    # print(opp.get("cards", []))
    winner = team if team["crowns"] > opp["crowns"] else opp
    wtower_healths = (winner.get("princessTowersHitPoints") or []) + [winner.get("kingTowerHitPoints", 0)]   
     # print([winner["kingTowerHitPoints"]])
    # print(wtower_healths)
    wlowtowerhealth =0
    for i in range(abs(team["crowns"] - opp["crowns"])):
        wlowtowerhealth+=min(wtower_healths)
        wtower_healths.remove(min(wtower_healths))
    if winner != team:
        wlowtowerhealth*=-1
    #wlowtowhealth = min([hp for hp in wtower_healths if hp != 0], default=0)
    battle_id = f"{team["tag"]}_{battle["battleTime"]}"
    # print(battle_id)

    return (battle_id,  wlowtowerhealth, str(tdeck), str(odeck))

# def write_battle_data(battle, player_tag, db):
#     team = battle["team"][0]
#     opp = battle["opponent"][0]
#     return {
#         "player_deck": ", ".join([c["name"] for c in team.get("cards", [])]),
#         "opponent_deck": ", ".join([c["name"] for c in opp.get("cards", [])]),
#         "player_won": int(team["crowns"] > opp["crowns"]),
#         "player_crowns": team["crowns"],
#         "opponent_crowns": opp["crowns"]
#     }
# --- RATE-LIMITER HELPERS ---

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

# --- MAIN SCRAPER ---

async def collect_megadraft_from_top_clans(top_n_clans=5, dbname=dBManager.dbname):
    rate_limiter = RateLimiter(REQUESTS_PER_SECOND)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    con = sqlite3.connect(f'{dbname}.db')
    cur = con.cursor()
    async with aiohttp.ClientSession() as session:
        clans = await fetch_top_clans(session, top_n_clans)
        if not clans:
            print("❌ Failed to fetch top clans.")
            return

        all_players = []
        for c in clans:
            async with semaphore:
                await rate_limiter.wait()
                members = await fetch_clan_members(session, c["tag"])
                all_players.extend([m["tag"] for m in members])
                # await asyncio.sleep(random.uniform(0.05, 0.15))  # small random delay

        print(f"✅ Got {len(all_players)} players from {len(clans)} clans.")

        

        async def fetch_player(player_tag, idx):
            async with semaphore:
                await rate_limiter.wait()
                battles = await fetch_battlelog(session, player_tag)
                count = 0
                for b in battles:
                    if is_mega_draft(b):
                        row = extract_battle_data(b)
                        cur.execute("""
                            INSERT OR IGNORE INTO battles 
                            (battle_id,  low_tower_dif, player_deck, opp_deck)
                            VALUES (?,  ?, ?, ?)
                        """, row)
                        con.commit()

                        # writer.writerow(row)
                        count += 1
                print(f"🔹 [{idx+1}/{len(all_players)}] {player_tag}: {count} Mega Draft matches")
                # await asyncio.sleep(random.uniform(0.05, 0.15))

        tasks = [fetch_player(tag, i) for i, tag in enumerate(all_players)]
        await asyncio.gather(*tasks)

 # print(f"\n✅ Done! Mega Draft data saved to {output_csv}")
import ast  # for safely converting string representation of lists back to Python lists



# --- RUN ---
if __name__ == "__main__":

    # reset_db("testdb")
    asyncio.run(collect_megadraft_from_top_clans(top_n_clans=50))
