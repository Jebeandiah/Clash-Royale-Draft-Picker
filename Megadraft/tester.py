import torch
from boardGenerator import Board, card_list
import testmodel  # optional: can use ValueNet class defined below instead of testmodel

MODEL_PATH = "value_net_best.pth"   # adjust to final filename
INPUT_LEN = 357
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

draftorder = [1,2,2,2,2,2,2,2,1]

# Load model
model = testmodel.ValueNet().to(device)
state = torch.load(MODEL_PATH, map_location=device)
model.load_state_dict(state, strict=False)
model.eval()

# -----------------------
# Helper: encode state
# -----------------------
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

# -----------------------
# Evaluate all candidate picks and return full score distribution
# -----------------------
def pick_scores_for_state(picker_deck, other_deck, pool, draft_idx):
    states = []
    candidate_cards = []
    for card in pool:
        pd = list(picker_deck)
        od = list(other_deck)
        p_copy = list(pool)
        p_copy.remove(card)
        pd.append(card)
        s = encode_state(pd, od, p_copy, draft_idx)
        states.append(s)
        candidate_cards.append(card)

    if len(states) == 0:
        return [], []

    batch = torch.cat(states, dim=0)
    with torch.no_grad():
        vals = model(batch)  # shape [N]
    return candidate_cards, vals.cpu().tolist()

# -----------------------
# Simulate full megadraft with score distribution at each pick
# -----------------------
def simulate_self_play():
    board = Board()
    pool = board.board.copy()
    p1, p2 = [], []
    cumulative_pick = 8

    for turn_idx, pick_count in enumerate(draftorder):
        picker = 0 if turn_idx % 2 == 0 else 1
        for pick_i in range(pick_count):
            picker_deck = p1 if picker == 0 else p2
            other_deck = p2 if picker == 0 else p1

            candidate_cards, scores = pick_scores_for_state(picker_deck, other_deck, pool, cumulative_pick)
            if not candidate_cards:
                break

            # Sort by score descending
            sorted_cards = sorted(zip(candidate_cards, scores), key=lambda x: x[1], reverse=True)

            # Display rectangularly
            print(f"Draft step {cumulative_pick}, Player {picker+1} pick {pick_i+1}:")
            row_len = 4  # number of cards per row
            for i in range(0, len(sorted_cards), row_len):
                row = sorted_cards[i:i+row_len]
                print("  " + " | ".join(f"{c}:{s:.4f}" for c, s in row))
            print()

            # Pick best card
            best_card = sorted_cards[0][0]
            picker_deck.append(best_card)
            pool.remove(best_card)
            print(f"  -> Selected: {best_card}\n")
        cumulative_pick -= 1

    print("Final decks:")
    print("P1:", p1)
    print("P2:", p2)

def simulate_vs_human():
    board = Board()
    pool = board.board.copy()
    human, ai = [], []
    cumulative_pick = 8

    for turn_idx, pick_count in enumerate(draftorder):
        is_human_turn = (turn_idx % 2 == 0)  # Human is Player 1
        picker_deck = human if is_human_turn else ai
        other_deck = ai if is_human_turn else human

        for pick_i in range(pick_count):
            candidate_cards, scores = pick_scores_for_state(picker_deck, other_deck, pool, cumulative_pick)
            if not candidate_cards:
                break

            sorted_cards = sorted(zip(candidate_cards, scores), key=lambda x: x[1], reverse=True)

            print(f"\nDraft step {cumulative_pick}, {'Human' if is_human_turn else 'AI'} pick {pick_i+1}:")
            row_len = 4
            for i in range(0, len(sorted_cards), row_len):
                row = sorted_cards[i:i+row_len]
                print("  " + " | ".join(f"{c}:{s:.4f}" for c, s in row))
            print()

            if is_human_turn:
                # Ask human to pick a card
                while True:
                    pick = input("Choose your card from pool: ").strip()
                    if pick in pool:
                        selected = pick
                        break
                    print("Invalid card. Try again.")
            else:
                # AI picks best card
                selected = sorted_cards[0][0]

            picker_deck.append(selected)
            pool.remove(selected)
            print(f"  -> Selected: {selected}")

        cumulative_pick -= 1

    print("\nFinal decks:")
    print("Human:", human)
    print("AI   :", ai)

# -----------------------
if __name__ == "__main__":
    # simulate_vs_human()
    simulate_self_play()