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
            low_tower_dif INTEGER NOT NULL,
            player_deck TEXT NOT NULL,
            opp_deck TEXT NOT NULL
        )
    ''')
    cursor.execute("DROP TABLE IF EXISTS training")
    
    # Create the new table
    cursor.execute('''
        CREATE TABLE training (
            input BLOB NOT NULL,
            next_card int NOT NULL,
            score int NOT NULL
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
            'low_tower_dif': int,
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
            "low_tower_dif": row[1],
            "player_deck": ast.literal_eval(row[2]),  # convert string back to list
            "opp_deck": ast.literal_eval(row[3])
        }
        battles.append(battle)
    
    return battles

if __name__ == "__main__":
    # print(read_battles(dbname, 1)[0])
    format_db("testdb")
    print(read_battles())
    pls = "stop"