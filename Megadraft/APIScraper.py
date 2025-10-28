import requests
import csv
import time
import random
from urllib.parse import quote

API_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiIsImtpZCI6IjI4YTMxOGY3LTAwMDAtYTFlYi03ZmExLTJjNzQzM2M2Y2NhNSJ9.eyJpc3MiOiJzdXBlcmNlbGwiLCJhdWQiOiJzdXBlcmNlbGw6Z2FtZWFwaSIsImp0aSI6Ijg1MjVhZDQyLTgzMmEtNDMxNS04NDJhLWNjZDMxZTNmOTFlOCIsImlhdCI6MTc2MTY4NDAxNywic3ViIjoiZGV2ZWxvcGVyL2VhY2E4OWQzLWUyYjYtZDU2NC1iNTQ2LWMxMzY4NTZkNzA5OCIsInNjb3BlcyI6WyJyb3lhbGUiXSwibGltaXRzIjpbeyJ0aWVyIjoiZGV2ZWxvcGVyL3NpbHZlciIsInR5cGUiOiJ0aHJvdHRsaW5nIn0seyJjaWRycyI6WyIxMzQuMTczLjU2LjIyNyIsIjEzNC4xNzMuMTkyLjc2Il0sInR5cGUiOiJjbGllbnQifV19.v-biGRJboJybMK0XE7Vn8vv8zVV4o5RCNfjrhUiLUuhMrN4wwofPHf-xYzaY_F-h8t41s9lLQvEkBichWY_FvA"
HEADERS = {
    "Accept": "application/json",
    "Authorization": f"Bearer {API_TOKEN}"
}

# --- API HELPERS ---

def safe_get(url, retries=3, timeout=5):
    """GET with retry and timeout."""
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            if r.status_code == 429:
                # Rate limit: wait and retry
                wait = int(r.headers.get("Retry-After", 5))
                print(f"⚠️ Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r
        except requests.exceptions.Timeout:
            print(f"⏳ Timeout on {url}, retry {attempt+1}/{retries}")
        except Exception as e:
            print(f"⚠️ Request failed ({attempt+1}/{retries}): {e}")
        time.sleep(1 + attempt)
    return None

def fetch_top_clans(limit=10):
    url = f"https://api.clashroyale.com/v1/locations/global/rankings/clans?limit={limit}"
    r = safe_get(url)
    return r.json()["items"] if r else []

def fetch_clan_members(clan_tag):
    encoded = quote(clan_tag)
    url = f"https://api.clashroyale.com/v1/clans/{encoded}/members"
    r = safe_get(url)
    return r.json()["items"] if r else []

def fetch_battlelog(player_tag):
    encoded = quote(player_tag)
    url = f"https://api.clashroyale.com/v1/players/{encoded}/battlelog"
    r = safe_get(url)
    if not r:
        return []
    if r.status_code == 404:
        return []
    return r.json()

# --- FILTERS AND EXTRACTION ---

def is_mega_draft(battle):
    # The type might also be "megaDraft" in some cases
    return battle.get("deckSelection", "").upper() == "PICK"

def extract_battle_data(battle, player_tag):
    team = battle["team"][0]
    opp = battle["opponent"][0]
    return {
        # "player_tag": player_tag,
        # "player_name": team["name"],
        "player_deck": ", ".join([c["name"] for c in team.get("cards", [])]),
        # "pool": ", ".join([c["name"] for c in team.get("supportCards", [])]),

        # "opponent_name": opp["name"],
        "opponent_deck": ", ".join([c["name"] for c in opp.get("cards", [])]),
        # "testpool": ", ".join([c["name"] for c in opp.get("supportCards", [])]),

        "player_won": int(team["crowns"] > opp["crowns"]),
        "player_crowns": team["crowns"],
        "opponent_crowns": opp["crowns"],
        # "battle_time": battle.get("battleTime", ""),
        # "arena": battle.get("arena", {}).get("name", ""),
        # "mode": battle.get("type", "")
    }

# --- MAIN LOOP ---

def collect_megadraft_from_top_clans(top_n_clans=5, output_csv="mega_draft_matches.csv"):
    clans = fetch_top_clans(top_n_clans)
    if not clans:
        print("❌ Failed to fetch top clans. Check your token or IP access.")
        return

    all_players = []
    for c in clans:
        print(f"🏆 Fetching members from {c['name']} ({c['tag']})...")
        members = fetch_clan_members(c["tag"])
        all_players.extend([m["tag"] for m in members])
        time.sleep(0.3)

    print(f"✅ Got {len(all_players)} total players from {len(clans)} clans.")

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "player_won", "player_crowns", "opponent_crowns","player_deck", "opponent_deck"
            
        ])
        writer.writeheader()

        for i, tag in enumerate(all_players):
            print(f"🔹 [{i+1}/{len(all_players)}] Fetching {tag}...")
            battles = fetch_battlelog(tag)
            count = 0
            for b in battles:
                # print(b.get("deckSelection", "").upper() )
                if is_mega_draft(b):
                    row = extract_battle_data(b, tag)
                    writer.writerow(row)
                    count += 1
            if count > 0:
                print(f"   🟩 Found {count} Mega Draft matches!")
            else:
                print(f"   ⬜ No Mega Draft matches.")
            # Random small delay to stay below rate limits
            time.sleep(random.uniform(0.5, 1.2))

    print(f"\n✅ Done! Mega Draft data saved to {output_csv}")

# --- RUN ---
if __name__ == "__main__":
    #print(fetch_battlelog('#GOPYJJY'))
    # tag = '#8VCGL2UJ2'
    # battles = fetch_battlelog(tag)
    # print(battles)
    # count = 0
    # for b in battles:
    #     print(b.get("deckSelection", "").upper() )
       
    # #Random small delay to stay below rate limits
    # time.sleep(random.uniform(0.5, 1.2))
    collect_megadraft_from_top_clans(top_n_clans=10)
