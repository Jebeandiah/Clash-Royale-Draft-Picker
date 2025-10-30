import sqlite3
import ast

dbname = "testdb"
def format_db(dbname):
    """Completely clear and recreate the battles table."""
    con = sqlite3.connect(f'{dbname}.db')
    cursor = con.cursor()
    
    # Drop the old table if it exists
    cursor.execute("DROP TABLE IF EXISTS battles")
    
    # Create the new table
    cursor.execute('''
        CREATE TABLE battles (
            battle_id TEXT PRIMARY KEY,
            player_crowns INTEGER NOT NULL,
            opp_crowns INTEGER NOT NULL,
            winner_low_tower INTEGER NOT NULL,
            player_deck TEXT NOT NULL,
            opp_deck TEXT NOT NULL
        )
    ''')
    cursor.execute("DROP TABLE IF EXISTS training")
    
    # Create the new table
    cursor.execute('''
        CREATE TABLE training (
            cards BLOB NOT NULL,
            pick_step INTEGER NOT NULL,
            score INTEGER NOT NULL
        )
    ''')
    con.commit()
    
    # Optional: shrink the database file to reclaim space
    con.execute("VACUUM")
    
    con.close()
    print(f"✅ Database '{dbname}.db' has been reset and cleared.")

def read_battles(dbname=dbname, limit=None):
    """
    Reads battles from the database.
    
    Returns a list of dictionaries:
        {
            'id': list of ints,
            'player_crowns': int,
            'opp_crowns': int,
            'winner_low_tower': int,
            'player_deck': list of ints,
            'opp_deck': list of ints
        }
    """
    con = sqlite3.connect(f"{dbname}.db")
    cursor = con.cursor()

    query = "SELECT * FROM battles"
    if limit:
        query += f" LIMIT {limit}"
    
    cursor.execute(query)
    rows = cursor.fetchall()
    con.close()

    battles = []
    for row in rows:
        # row: (id, player_crowns, opp_crowns, winner_low_tower, player_deck, opp_deck)
        battle = {
            "id": row[0],
            "player_crowns": row[1],
            "opp_crowns": row[2],
            "winner_low_tower": row[3],
            "player_deck": ast.literal_eval(row[4]),  # convert string back to list
            "opp_deck": ast.literal_eval(row[5])
        }
        battles.append(battle)
    
    return battles

if __name__ == "__main__":
    # print(read_battles(dbname, 1)[0])
    format_db("testdb")
    pls = "stop"