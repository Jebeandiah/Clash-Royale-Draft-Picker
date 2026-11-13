import cardhelpers as ch
import sqlite3
import dBManager
from trainer import blob_to_tensor
import torch
    # see if any cards in DB (table has multihot deck encoding) are underepresented or arent even in the pool sean
    # read from DB like trainer.py
def print_card_distribution():
    con = sqlite3.connect(f'{dBManager.DB_NAME}.db')
    cur = con.cursor()
    cur.execute("SELECT packed_decks, low_tower_dif FROM battles")
    rows = cur.fetchall()
    con.close()

    if len(rows) == 0:
        raise RuntimeError("No battle rows found in database.")

    num_cards = len(ch.card_list)
    running_counts = torch.zeros(num_cards)

    for packed_blob, low_tower_dif in rows:
        # 1. Unpack bits from bytes
        packed = torch.tensor(list(packed_blob), dtype=torch.uint8)
        t = packed.view(-1, 1)
        bits = ((t & (1 << torch.arange(8))) > 0).to(torch.float32)
        bits = torch.flip(bits, dims=[1]).flatten()[:num_cards * 2]

        # 2. Slice out the two 120-dim multi-hot vectors (NO re-encoding needed!)
        p_multi_hot, o_multi_hot = blob_to_tensor(packed_blob)
        running_counts+=p_multi_hot+o_multi_hot

    counts_to_card_id ={}
    for card_id in range(num_cards):
        # print(f"{ch.card_list[card_id].name} appeared {running_counts[card_id]} times")
        if(int(running_counts[card_id]) in counts_to_card_id):
            counts_to_card_id[int(running_counts[card_id])]+=[ch.card_list[card_id].name]
        else:
            counts_to_card_id[int(running_counts[card_id])]=[ch.card_list[card_id].name]
    descending_counts =  dict(sorted(counts_to_card_id.items(), reverse=True))
    for count, cards in descending_counts.items():
        print(f"{count}: {', '.join(cards)}")

    return
    



if __name__ == "__main__":
    
    print_card_distribution()
    pls = "noerror"

