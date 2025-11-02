import torch
from boardGenerator import Board, card_list
import testmodel

MODEL_PATH = "value_net_best.pth"
INPUT_LEN = 357
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

draftorder = [1, 2, 2, 2, 2, 2, 2, 2, 1]

# -----------------------
# Load model
# -----------------------
model = testmodel.ValueNet().to(device)
state = torch.load(MODEL_PATH, map_location=device)
model.load_state_dict(state, strict=False)
model.eval()

# -----------------------
# Encode state
# -----------------------
def encode_state(picker_deck, other_deck, pool, draft_idx):
    vec = torch.zeros(INPUT_LEN, dtype=torch.float32)
    for card in picker_deck:
        if card in card_list:
            vec[card_list.index(card)] = 1.0
    offset = 116
    for card in other_deck:
        if card in card_list:
            vec[offset + card_list.index(card)] = 1.0
    offset = 232
    for card in pool:
        if card in card_list:
            vec[offset + card_list.index(card)] = 1.0
    offset = 348
    if draft_idx < 9:
        vec[offset + draft_idx] = 1.0
    return vec.unsqueeze(0).to(device)

# -----------------------
# Evaluate all candidate picks
# -----------------------
def pick_scores(picker_deck, other_deck, pool, draft_idx):
    states = []
    candidate_cards = []
    for card in pool:
        pd = list(picker_deck) + [card]
        od = list(other_deck)
        p_copy = [c for c in pool if c != card]
        s = encode_state(pd, od, p_copy, draft_idx)
        states.append(s)
        candidate_cards.append(card)

    if not states:
        return [], []

    batch = torch.cat(states, dim=0)
    with torch.no_grad():
        vals = model(batch)
    return candidate_cards, vals.cpu().tolist()

# -----------------------
# Minimax selection returning scores for all candidate cards
# -----------------------
def pick_minimax_scores(deck, other_deck, pool, draft_idx):
    card_to_score = {}

    for my_card in pool:
        remaining_pool = [c for c in pool if c != my_card]
        worst_case_score = float('inf')

        # simulate all possible opponent picks
        for opp_card in remaining_pool:
            my_next_deck = deck + [my_card]
            opp_next_deck = other_deck + [opp_card]
            pool_after_opp = [c for c in remaining_pool if c != opp_card]

            candidate_cards, vals = pick_scores(opp_next_deck, my_next_deck, pool_after_opp, draft_idx - 1)
            score = max(vals) if vals else 0.0
            if score < worst_case_score:
                worst_case_score = score

        card_to_score[my_card] = worst_case_score

    # Pick card with minimal worst-case score
    best_card = min(card_to_score, key=card_to_score.get)
    return best_card, card_to_score

# -----------------------
# Play against human
# -----------------------
def play_against_human():
    board = Board()
    pool = board.board.copy()
    human, ai = [], []
    cumulative_pick = 8

    for turn_idx, pick_count in enumerate(draftorder):
        is_human_turn = (turn_idx % 2 == 0)
        deck = human if is_human_turn else ai
        other_deck = ai if is_human_turn else human

        for pick_i in range(pick_count):
            if not pool:
                break

            if is_human_turn:
                print(f"\nTurn {cumulative_pick}, Human pick {pick_i+1}")
                print("Available cards:", pool)
                while True:
                    pick = input("Pick a card: ").strip()
                    if pick in pool:
                        selected = pick
                        break
                    print("Invalid card. Try again.")
            else:
                # AI turn
                # AI turn
# AI turn
                if pick_i == pick_count - 1:
                    # Compute worst-case scores for each candidate
                    scores_dict = {}
                    for card in pool:
                        remaining_pool = [c for c in pool if c != card]
                        worst_case_score = float('inf')
                        for opp_card in remaining_pool:
                            my_next_deck = deck + [card]
                            opp_next_deck = other_deck + [opp_card]
                            pool_after_opp = [c for c in remaining_pool if c != opp_card]

                            candidate_cards, vals = pick_scores(opp_next_deck, my_next_deck, pool_after_opp, cumulative_pick - 1)
                            score = max(vals) if vals else 0.0
                            if score < worst_case_score:
                                worst_case_score = score
                        scores_dict[card] = worst_case_score

                    # Sort cards by worst-case score ascending
                    sorted_cards = sorted(scores_dict.items(), key=lambda x: x[1])

                    # Print grid
                    print("Candidate cards (best-case against human) sorted best→worst:")
                    row_len = 4
                    for i in range(0, len(sorted_cards), row_len):
                        row = sorted_cards[i:i+row_len]
                        print("  " + " | ".join(f"{c}:{s:.4f}" for c, s in row))

                    # Pick the best card (lowest worst-case score)
                    selected, best_score = sorted_cards[0]
                    print(f"Turn {cumulative_pick}, AI picked: {selected} (score: {best_score:.4f})")

                else:
                    # Regular greedy pick
                    candidate_cards, scores = pick_scores(deck, other_deck, pool, cumulative_pick)
                    selected = candidate_cards[scores.index(max(scores))]
                    print(f"Turn {cumulative_pick}, AI picked: {selected}")


            deck.append(selected)
            pool.remove(selected)

        cumulative_pick -= 1

    print("\nFinal decks:")
    print("Human:", human)
    print("AI   :", ai)

# -----------------------
if __name__ == "__main__":
    play_against_human()
