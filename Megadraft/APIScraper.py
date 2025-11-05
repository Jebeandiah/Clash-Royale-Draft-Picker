import asyncio
import aiohttp
import time
import boardGenerator as bg
from urllib.parse import quote
import sqlite3
import dBManager
import os

# --- API CONFIGURATION ---

API_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiIsImtpZCI6IjI4YTMxOGY3LTAwMDAtYTFlYi03ZmExLTJjNzQzM2M2Y2NhNSJ9.eyJpc3MiOiJzdXBlcmNlbGwiLCJhdWQiOiJzdXBlcmNlbGw6Z2FtZWFwaSIsImp0aSI6Ijg1MjVhZDQyLTgzMmEtNDMxNS04NDJhLWNjZDMxZTNmOTFlOCIsImlhdCI6MTc2MTY4NDAxNywic3ViIjoiZGV2ZWxvcGVyL2VhY2E4OWQzLWUyYjYtZDU2NC1iNTQ2LWMxMzY4NTZkNzA5OCIsInNjb3BlcyI6WyJyb3lhbGUiXSwibGltaXRzIjpbeyJ0aWVyIjoiZGV2ZWxvcGVyL3NpbHZlciIsInR5cGUiOiJ0aHJvdHRsaW5nIn0seyJjaWRycyI6WyIxMzQuMTczLjU2LjIyNyIsIjEzNC4xNzMuMTkyLjc2Il0sInR5cGUiOiJjbGllbnQifV19.v-biGRJboJybMK0XE7Vn8vv8zVV4o5RCNfjrhUiLUuhMrN4wwofPHf-xYzaY_F-h8t41s9lLQvEkBichWY_FvA"  # Replace with your Clash Royale API token

# HTTP headers required by the Clash Royale API
HEADERS = {
    "Accept": "application/json",
    "Authorization": f"Bearer {API_TOKEN}"
}

# --- SCRAPER LIMITS ---
MAX_CONCURRENT_REQUESTS = 9     # Maximum number of requests running in parallel
REQUESTS_PER_SECOND = 120       # Maximum allowed request rate (for rate limiting)
NEW_CLANS_FILE = "new_clans.txt"  # File to store newly discovered clan tags


# ===============================================================
# =============== ASYNCHRONOUS REQUEST HELPERS ==================
# ===============================================================

async def safe_get(session, url, retries=3, timeout=500):
    """
    Safely perform a GET request to the Clash Royale API.

    Automatically retries the request if:
      - API rate limits are hit (HTTP 429)
      - A timeout occurs
      - A general network error happens

    Returns JSON data on success, or None on failure.
    """
    for attempt in range(retries):
        try:
            async with session.get(url, headers=HEADERS, timeout=timeout) as resp:
                # If we hit the API's rate limit, wait briefly and retry
                if resp.status == 429:
                    print(f"⚠️ Rate limited, waiting 0.5s...")
                    await asyncio.sleep(0.5)
                    continue
                # Raise an exception for any other non-success status
                resp.raise_for_status()
                return await resp.json()

        except asyncio.TimeoutError:
            print(f"⏳ Timeout on {url}, retry {attempt+1}/{retries}")
        except Exception as e:
            print(f"⚠️ Request failed ({attempt+1}/{retries}): {e}")

        # Wait a bit before retrying
        await asyncio.sleep(1 + attempt)

    return None


# --- DATA FETCHERS ---

async def fetch_top_clans(session, limit=10):
    """
    Fetch the top global clans using the Clash Royale API.
    """
    url = f"https://api.clashroyale.com/v1/locations/global/rankings/clans?limit={limit}"
    data = await safe_get(session, url)
    return data["items"] if data else []


async def fetch_clan_members(session, clan_tag):
    """
    Fetch all members of a given clan by its tag.
    """
    encoded = quote(clan_tag)
    url = f"https://api.clashroyale.com/v1/clans/{encoded}/members"
    data = await safe_get(session, url)
    return data["items"] if data else []


async def fetch_battlelog(session, player_tag):
    """
    Fetch the battle log (recent matches) for a specific player.
    """
    encoded = quote(player_tag)
    url = f"https://api.clashroyale.com/v1/players/{encoded}/battlelog"
    data = await safe_get(session, url)
    return data if data else []


# ===============================================================
# ================== BATTLE DATA HANDLING ========================
# ===============================================================

def is_mega_draft(battle):
    """
    Check if the given battle is a Mega Draft match.
    Mega Draft battles have 'deckSelection' set to 'PICK'.
    """
    return battle.get("deckSelection", "").upper() == "PICK"


def extract_battle_data(battle):
    """
    Extract relevant fields from a battle log entry for database insertion.

    Returns a tuple containing:
        - battle_id (unique key)
        - low_tower_dif (numeric difference measure)
        - player_deck (list of card IDs)
        - opponent_deck (list of card IDs)
    """
    team = battle["team"][0]
    opp = battle["opponent"][0]

    # Convert card names into unique card IDs using boardGenerator
    tdeck = [bg.card_str_to_id(c["name"]) for c in team.get("cards", [])]
    odeck = [bg.card_str_to_id(c["name"]) for c in opp.get("cards", [])]

    # Determine winner and collect tower healths
    winner = team if team["crowns"] > opp["crowns"] else opp
    wtower_healths = (winner.get("princessTowersHitPoints") or []) + [winner.get("kingTowerHitPoints", 0)]

    # Compute a "low tower health" metric — how close the win/loss was
    wlowtowerhealth = 0
    for i in range(abs(team["crowns"] - opp["crowns"])):
        wlowtowerhealth += min(wtower_healths)
        wtower_healths.remove(min(wtower_healths))
    if winner != team:
        wlowtowerhealth *= -1  # Negative if player lost

    # Build a unique battle ID using player tag + timestamp
    battle_id = f"{team['tag']}_{battle['battleTime']}"

    return (battle_id, wlowtowerhealth, str(tdeck), str(odeck))


# ===============================================================
# ===================== RATE LIMITER CLASS ======================
# ===============================================================

class RateLimiter:
    """
    Simple rate limiter to ensure we don't exceed the API's
    requests-per-second limit.
    """
    def __init__(self, rate_per_sec):
        self.delay = 1 / rate_per_sec
        self._lock = asyncio.Lock()
        self._last_time = 0

    async def wait(self):
        """
        Wait the necessary amount of time between requests to
        maintain the defined rate.
        """
        async with self._lock:
            now = time.time()
            elapsed = now - self._last_time
            wait_time = max(0, self.delay - elapsed)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            self._last_time = time.time()


# ===============================================================
# ===================== NEW CLAN TRACKING =======================
# ===============================================================

def save_new_clan(clan_tag):
    """
    Store newly discovered clan tags in a text file.

    Ensures:
        - No duplicates
        - Clan tags are valid (#-prefixed)
    """
    if not clan_tag or not clan_tag.startswith("#"):
        return

    # Create file if missing
    if not os.path.exists(NEW_CLANS_FILE):
        with open(NEW_CLANS_FILE, "w") as f:
            f.write("")

    # Append only if it's not already in file
    with open(NEW_CLANS_FILE, "r+") as f:
        existing = set(line.strip() for line in f.readlines())
        if clan_tag not in existing:
            f.write(clan_tag + "\n")
            print(f"📁 New clan found: {clan_tag}")

def read_clan_file(file_path):
    """Read clan tags from a file (one per line)."""
    if not os.path.exists(file_path):
        return []
    with open(file_path, "r") as f:
        return [line.strip() for line in f.readlines() if line.strip()]

# ===============================================================
# ======================= MAIN SCRAPER ==========================
# ===============================================================

async def collect_megadraft_from_top_clans(top_n_clans=10, dbname=dBManager.dbname):
    """
    Main asynchronous scraping function.

    1. Fetches top clans.
    2. Gets all players from those clans.
    3. Fetches each player’s battle log.
    4. Filters for Mega Draft matches.
    5. Saves battles to the SQLite database.
    6. Extracts opponent clan tags and saves them to 'new_clans.txt'.
    """
    rate_limiter = RateLimiter(REQUESTS_PER_SECOND)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    con = sqlite3.connect(f"{dbname}.db")
    cur = con.cursor()

    async with aiohttp.ClientSession() as session:
        # Step 1: Fetch the top clans globally
        clans = await fetch_top_clans(session, top_n_clans)
        if not clans:
            print("❌ Failed to fetch top clans.")
            return

        # Step 2: Collect all player tags from these clans
        all_players = []
        for c in clans:
            async with semaphore:
                await rate_limiter.wait()
                members = await fetch_clan_members(session, c["tag"])
                all_players.extend([m["tag"] for m in members])

        print(f"✅ Got {len(all_players)} players from {len(clans)} clans.")

        # Step 3: Define async worker for each player
        async def fetch_player(player_tag, idx):
            """
            For each player:
              - Fetch battle log
              - Filter Mega Draft matches
              - Save to database
              - Collect opponent clan tags
            """
            async with semaphore:
                await rate_limiter.wait()
                battles = await fetch_battlelog(session, player_tag)
                count = 0

                for b in battles:
                    if is_mega_draft(b):
                        # Extract and insert battle data
                        row = extract_battle_data(b)
                        cur.execute("""
                            INSERT OR IGNORE INTO battles 
                            (battle_id, low_tower_dif, player_deck, opp_deck)
                            VALUES (?, ?, ?, ?)
                        """, row)
                        con.commit()
                        count += 1

                        # Step 4: Save opponent’s clan tag (if exists)
                        opp = b["opponent"][0]
                        opp_clan = opp.get("clan", {}).get("tag")
                        if opp_clan:
                            save_new_clan(opp_clan)

                print(f"🔹 [{idx+1}/{len(all_players)}] {player_tag}: {count} Mega Draft matches")

        # Step 5: Run all player tasks concurrently
        tasks = [fetch_player(tag, i) for i, tag in enumerate(all_players)]
        await asyncio.gather(*tasks)

    # Close DB connection and summarize
    con.close()
    print(f"\n✅ Done! Mega Draft data saved to {dbname}.db")
    print(f"🧭 New clans stored in {NEW_CLANS_FILE}")

# ===============================================================
# ===== NEW FUNCTION: SCRAPE MEGA DRAFT FROM CLANS IN FILE ======
# ===============================================================

async def collect_megadraft_from_clan_list(file_path=NEW_CLANS_FILE, dbname=dBManager.dbname):
    """
    Reads all clan tags from the given file and collects Mega Draft data for them.
    While processing, any newly found opponent clans are added to the same file.
    """
    rate_limiter = RateLimiter(REQUESTS_PER_SECOND)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    con = sqlite3.connect(f"{dbname}.db")
    cur = con.cursor()

    clans_to_process = read_clan_file(file_path)
    if not clans_to_process:
        print("❌ No clans found in file.")
        return

    async with aiohttp.ClientSession() as session:
        print(f"🔍 Starting from {len(clans_to_process)} clans listed in {file_path}")

        async def process_clan(clan_tag, idx):
            async with semaphore:
                await rate_limiter.wait()
                members = await fetch_clan_members(session, clan_tag)
                print(f"🏰 [{idx+1}/{len(clans_to_process)}] Clan {clan_tag}: {len(members)} members")

                # For each member, fetch battles
                for m in members:
                    player_tag = m["tag"]
                    await rate_limiter.wait()
                    battles = await fetch_battlelog(session, player_tag)
                    for b in battles:
                        if is_mega_draft(b):
                            row = extract_battle_data(b)
                            cur.execute("""
                                INSERT OR IGNORE INTO battles 
                                (battle_id, low_tower_dif, player_deck, opp_deck)
                                VALUES (?, ?, ?, ?)
                            """, row)
                            con.commit()

                            # Save opponent’s clan tag if found
                            opp = b["opponent"][0]
                            opp_clan = opp.get("clan", {}).get("tag")
                            if opp_clan:
                                save_new_clan(opp_clan)

        tasks = [process_clan(tag, i) for i, tag in enumerate(clans_to_process)]
        await asyncio.gather(*tasks)

    con.close()
    print(f"\n✅ Done scanning {len(clans_to_process)} clans.")
    print(f"🧭 Newly discovered clans saved in {file_path}")


# ===============================================================
# ======================== RUN SCRIPT ===========================
# ===============================================================

if __name__ == "__main__":
    # Run the main collector for the top 600 clans by default
    asyncio.run(collect_megadraft_from_top_clans(top_n_clans=600))
