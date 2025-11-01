# tester_state_value.py
import torch
from boardGenerator import Board, card_list
import testmodel   # optional: can use ValueNet class defined below instead of testmodel

MODEL_PATH = "value_net_best.pth"   # adjust to final filename
INPUT_LEN = 357
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

draftorder = [1,2,2,2,2,2,2,2,1]

# If you have the ValueNet defined in trainer file, you can import or redefine here.

model = testmodel.ValueNet().to(device)
state = torch.load(MODEL_PATH, map_location=device)
model.load_state_dict(state, strict=False)
model.eval()

# helper: encode state where picker_deck is first (deck0)
def encode_state(picker_deck, other_deck, pool, draft_idx):
    vec = torch.zeros(INPUT_LEN, dtype=torch.float32)
    # picker deck (0..115)
    for card in picker_deck:
        if card in card_list:
            vec[card_list.index(card)] = 1.0
    # other deck (116..231)
    off = 116
    for card in other_deck:
        if card in card_list:
            vec[off + card_list.index(card)] = 1.0
    # pool (232..347)
    off = 232
    for card in pool:
        if card in card_list:
            vec[off + card_list.index(card)] = 1.0
    # draft step one-hot (348..356)
    off = 348
    if draft_idx < 9:
        vec[off + draft_idx] = 1.0
    return vec.unsqueeze(0).to(device)

# evaluate all candidate picks at once (fast)
def best_pick_for_state(picker_deck, other_deck, pool, draft_idx):
    # produce a batch of states, one per candidate card
    states = []
    candidate_cards = []
    for card in pool:
        # copy decks & pool
        pd = list(picker_deck)
        od = list(other_deck)
        p_copy = list(pool)
        # simulate pick: remove card from pool and add to picker deck
        p_copy.remove(card)
        pd.append(card)
        s = encode_state(pd, od, p_copy, draft_idx)  # using picker first encoding
        states.append(s)
        candidate_cards.append(card)

    if len(states) == 0:
        return None, None

    batch = torch.cat(states, dim=0)  # shape [N, 357]
    with torch.no_grad():
        vals = model(batch)   # shape [N]
    best_idx = torch.argmax(vals).item()
    return candidate_cards[best_idx], vals[best_idx].item()

# simulate full megadraft with model selecting for both players
def simulate_self_play():
    board = Board()
    pool = board.board.copy()
    p1, p2 = [], []
    cumulative_pick = 9
    for turn_idx, pick_count in enumerate(draftorder):
        picker = 0 if turn_idx % 2 == 0 else 1
        for pick_i in range(pick_count):
            # ensure picker_deck is first
            picker_deck = p1 if picker == 0 else p2
            other_deck = p2 if picker == 0 else p1
            # choose best pick
            best_card, val = best_pick_for_state(picker_deck, other_deck, pool, cumulative_pick)
            if best_card is None:
                break
            # apply
            picker_deck.append(best_card)
            pool.remove(best_card)
            print(f"Turn {cumulative_pick}: Player {picker+1} picked {best_card} (value {val:.4f}), remaining {len(pool)}")
        cumulative_pick -= 1
    print("Final decks:")
    print("P1:", p1)
    print("P2:", p2)

# single-pick example (manual)
def demo_one_board():
    board = Board()
    pool = board.board.copy()
    p1, p2 = [], []
    print("Board pool:", pool)
    # example: let model pick for player2 on first picker turn
    # assume picker is player1 first; let's show best pick for player1
    best_card, val = best_pick_for_state([], [], pool, 0)
    print("Best pick (empty decks) according to model:", best_card, val)

if __name__ == "__main__":
    # demo_one_board()
    simulate_self_play()
