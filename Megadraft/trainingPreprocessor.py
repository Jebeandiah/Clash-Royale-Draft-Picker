import copy
import dBManager
import cardhelpers as ch
import sqlite3
import torch
import ast
def bitpack_tensor(t):
    """
    Safely pack a 1D uint8 tensor of 0/1 bits into bytes.
    Works for any length.
    """
    t = t.flatten().to(torch.uint8)
    n = t.numel()
    if n == 0:
        return b""

    # Pad to multiple of 8
    pad = (8 - n % 8) % 8
    if pad > 0:
        t = torch.cat([t, torch.zeros(pad, dtype=torch.uint8)])

    # Reshape to bytes
    t = t.view(-1, 8)
    # Reverse bits in each byte safely
    t = torch.flip(t, dims=[1])
    packed = t.matmul(2 ** torch.arange(8, dtype=torch.uint8))
    return packed.numpy().tobytes()

def collect_decks(dbname=dBManager.dbname, limit=None):
  

    con = sqlite3.connect(f'{dbname}.db')
    cur = con.cursor()

    query = "SELECT * FROM battles"
    if limit:
        query += f" LIMIT {limit}"
    cur.execute(query)
    battles = cur.fetchall()

    for battle_entry in battles:
        player_deck = ast.literal_eval(battle_entry[2])
        opp_deck= ast.literal_eval(battle_entry[3])
        input_vec = torch.zeros(len(ch.card_list)*2, dtype=torch.uint8)
        for card_id in player_deck:
            input_vec[card_id] = 1
        for card_id in opp_deck:
            input_vec[card_id+len(ch.card_list)] = 1
        input_blob = bitpack_tensor(input_vec)

            # Next card and score
        score = float(battle_entry[1])/(9156)

        # Insert into DB
        cur.execute(
            "INSERT INTO training (input,  score) VALUES (?,  ?)",
            (input_blob,  score)
        )
        
        input_vec = torch.zeros(len(ch.card_list)*2, dtype=torch.uint8)
        for card_id in opp_deck:
            input_vec[card_id] = 1
        for card_id in player_deck:
            input_vec[card_id+len(ch.card_list)] = 1
        input_blob = bitpack_tensor(input_vec)

            # Next card and score
        score = float(-battle_entry[1])/(9156)
        cur.execute(
            "INSERT INTO training (input,  score) VALUES (?,  ?)",
            (input_blob,  score)
        )
    con.commit()
    con.close()

def read_training_data(dbname=dBManager.dbname, limit=None):
    
    con = sqlite3.connect(f'{dbname}.db')
    cur = con.cursor()

    query = "SELECT input,  score FROM training"
    if limit:
        query += f" LIMIT {limit}"
    cur.execute(query)
    rows = cur.fetchall()
    con.close()

    inputs = []
    scores = []

    for input_blob,  score in rows:
        packed = torch.tensor(list(input_blob), dtype=torch.uint8)
        t = packed.view(-1, 1)
        bits = ((t & (1 << torch.arange(8))) > 0).to(torch.uint8)
        bits = torch.flip(bits, dims=[1]).flatten()
        inputs.append(bits)
        scores.append(score)

    return torch.stack(inputs),  torch.tensor(scores)

if __name__ == "__main__":
    
    # collect_decks()
    inputs, scores = read_training_data()
    # print(inputs[0])
    print(len(scores))
    # debug_training_states()
    pls = "noerror"

