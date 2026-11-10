import asyncio
import os
import aiohttp
import time
from urllib.parse import quote
import sqlite3

import torch
import dBManager
import cardhelpers as ch
from trainingPreprocessor import bitpack_tensor
def load_env_file(filepath=".env"):
    try:
        with open(filepath, "r") as f:
            for line in f:
                # Strip whitespace and skip empty lines or comments
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                
                # Split on the first '=' sign
                if "=" in line:
                    key, value = line.split("=", 1)
                    # Remove potential surrounding whitespace or quotes
                    key = key.strip()
                    value = value.strip().strip("'").strip('"')
                    os.environ[key] = value
    except FileNotFoundError:
        print(f"Warning: {filepath} file not found.")

# Load variables into os.environ
load_env_file()

API_TOKEN = os.getenv("CR_API_KEY")
HEADERS = {"Accept": "application/json", "Authorization": f"Bearer {API_TOKEN}"}

MAX_CONCURRENT_REQUESTS = 8
REQUESTS_PER_SECOND = 100
DBNAME = dBManager.dbname
BATCH_COMMIT_SIZE = 25
TOTAL_BATTLE_LIMIT = 100000
MAX_PENDING_CLANS = 10_000

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
async def fetch_top_clans(session, limit=1):
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
def is_draft_competitive(battle):
    return battle.get("deckSelection", "").upper() == "DRAFTCOMPETITIVE"

def extract_battle_data(battle):
    team = battle["team"][0]
    opp = battle["opponent"][0]
    tdeck = [ch.name_to_id[c["name"].lower()] for c in team.get("cards", [])]
    odeck = [ch.name_to_id[c["name"].lower()] for c in opp.get("cards", [])]

    team = battle["team"][0]
    opp = battle["opponent"][0]
    tdeck = [ch.name_to_id[c["name"].lower()] for c in team.get("cards", [])]
    odeck = [ch.name_to_id[c["name"].lower()] for c in opp.get("cards", [])]

    # Build 1D bit vector for both decks: size = 2 * len(card_list)
    num_cards = len(ch.card_list)
    vec = torch.zeros(num_cards * 2, dtype=torch.uint8)
    for card_id in tdeck:
        vec[card_id] = 1
    for card_id in odeck:
        vec[card_id + num_cards] = 1

    # Pack bits into bytes BLOB
    packed_deck = bitpack_tensor(vec)
    winner = team if team["crowns"] > opp["crowns"] else opp
    tower_healths = (winner.get("princessTowersHitPoints") or []) + [winner.get("kingTowerHitPoints", 0)]
    low_tower = 0
    if tower_healths:
        for _ in range(abs(team["crowns"] - opp["crowns"])):
            low_tower += min(tower_healths)
            tower_healths.remove(min(tower_healths))
        if winner != team:
            low_tower *= -1

    tags = sorted([team["tag"], opp["tag"]])
    battle_id = f"{battle['battleTime']}_{tags[0]}_{tags[1]}"
    return (battle_id, low_tower, packed_deck), opp.get("clan", {}).get("tag")

# --- WORKER ---
async def worker(name, session, rate_limiter, con, battle_counter, counter_lock, queue, pending_clans, pending_lock):
    cur = con.cursor()
    try:
        while True:
            # Stop if battle limit reached
            async with counter_lock:
                if battle_counter[0] >= TOTAL_BATTLE_LIMIT:
                    break

            # Atomically claim a pending clan
            cur.execute("SELECT tag FROM found_clans WHERE status='pending' LIMIT 1")
            row = cur.fetchone()
            if not row:
                await asyncio.sleep(0.1)
                continue
            clan_tag = row[0]

            # Update to processed if still pending (atomic claim)
            cur.execute("UPDATE found_clans SET status='processed' WHERE tag=? AND status='pending'", (clan_tag,))
            if cur.rowcount != 1:
                # Another worker claimed it first
                continue

            async with pending_lock:
                pending_clans[0] -= 1

            await rate_limiter.wait()
            members = await fetch_clan_members(session, clan_tag)
            if not members:
                continue

            batch_rows = []
            new_clans_to_enqueue = []

            for m in members:
                player_tag = m["tag"]
                battles = await fetch_battlelog(session, player_tag)

                for b in battles:
                    if not is_draft_competitive(b):
                        continue

                    # Extract battle row
                    battle_row, opp_clan_tag = extract_battle_data(b)
                    batch_rows.append(battle_row)

                    # Update battle counter
                    async with counter_lock:
                        battle_counter[0] += 1
                        if battle_counter[0] >= TOTAL_BATTLE_LIMIT:
                            break

                    # Enqueue opponent clan if not already processed or pending
                    if opp_clan_tag:
                        cur.execute(
                            "SELECT status FROM found_clans WHERE tag=?",
                            (opp_clan_tag,)
                        )
                        status_row = cur.fetchone()
                        async with pending_lock:
                            if pending_clans[0] < MAX_PENDING_CLANS and (status_row is None):
                                cur.execute(
                                    "INSERT INTO found_clans (tag, status) VALUES (?, 'pending')",
                                    (opp_clan_tag,)
                                )
                                pending_clans[0] += 1
                                queue.put_nowait(opp_clan_tag)

            # Commit battles in batches
            if batch_rows:
                cur.executemany(
                    "INSERT OR IGNORE INTO battles (battle_id, low_tower_dif, packed_decks) VALUES (?, ?, ?)",
                    batch_rows
                )
                con.commit()

            print(f"[{name}] Processed clan {clan_tag}, total battles={battle_counter[0]}")

            # Stop immediately if limit reached
            async with counter_lock:
                if battle_counter[0] >= TOTAL_BATTLE_LIMIT:
                    # Push Nones to unblock remaining workers
                    for _ in range(MAX_CONCURRENT_REQUESTS):
                        queue.put_nowait(None)
                    break

            queue.task_done()

    except asyncio.CancelledError:
        print(f"[{name}] Worker cancelled")
        return

# --- MAIN ---
async def crawl_from_top_clan():
    # print("key is", API_TOKEN)
    con = sqlite3.connect(f"{DBNAME}.db")
    con.row_factory = sqlite3.Row
    rate_limiter = RateLimiter(REQUESTS_PER_SECOND)
    battle_counter = [0]
    counter_lock = asyncio.Lock()
    pending_clans = [0]
    pending_lock = asyncio.Lock()
    queue = asyncio.Queue()

    async with aiohttp.ClientSession() as session:
        # enqueue top clan
        clans = await fetch_top_clans(session, 1)
        if not clans:
            print("❌ Failed to fetch top clan")
            return

        top_clan = clans[0]
        cur = con.cursor()
        cur.execute("INSERT OR IGNORE INTO found_clans (tag, status) VALUES (?, 'pending')", (top_clan["tag"],))
        con.commit()
        pending_clans[0] = 1
        queue.put_nowait(top_clan["tag"])

        # start workers
        tasks = [
            asyncio.create_task(worker(f"W{i+1}", session, rate_limiter, con, battle_counter,
                                       counter_lock, queue, pending_clans, pending_lock))
            for i in range(MAX_CONCURRENT_REQUESTS)
        ]

        await asyncio.gather(*tasks)

    con.close()
    print(f"✅ Finished crawling! Total battles collected: {battle_counter[0]}")

# --- RUN ---
if __name__ == "__main__":
    asyncio.run(crawl_from_top_clan())