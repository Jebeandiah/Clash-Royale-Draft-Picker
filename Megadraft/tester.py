import torch
from boardGenerator import Board, card_list
import testmodel  # your file that defines StructuredValueNet

MODEL_PATH = "value_net_best.pth"
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

draftorder = [1, 2, 2, 2, 2, 2, 2, 2, 1]

# -----------------------
# Load model
# -----------------------
model = testmodel.StructuredValueNet().to(device)
state = torch.load(MODEL_PATH, map_location=device)
model.load_state_dict(state, strict=False)
model.eval()

# -----------------------
# Encode state (structured)
# -----------------------
def encode_state_structured(picker_deck, other_deck, pool, draft_idx):
    cards_vec = torch.zeros(116*3, dtype=torch.float32)
    # other_vec = torch.zeros(116, dtype=torch.float32)
    # pool_vec = torch.zeros(116, dtype=torch.float32)
    draft_vec = torch.zeros(9, dtype=torch.float32)

    for card in picker_deck:
        if card in card_list:
            cards_vec[card_list.index(card)] = 1.0
    for card in other_deck:
        if card in card_list:
            cards_vec[card_list.index(card)+116] = 1.0
    for card in pool:
        if card in card_list:
            cards_vec[card_list.index(card)+232] = 1.0
    if draft_idx < 9:
        draft_vec[draft_idx] = 1.0

    return (
        cards_vec.unsqueeze(0).to(device),
        # other_vec.unsqueeze(0).to(device),
        # pool_vec.unsqueeze(0).to(device),
        draft_vec.unsqueeze(0).to(device),
    )

# -----------------------
# Evaluate all candidate picks
# -----------------------
def pick_scores(picker_deck, other_deck, pool, draft_idx):
    all_card, all_draft = [],  []
    candidate_cards = []

    for card in pool:
        pd = list(picker_deck) + [card]
        od = list(other_deck)
        p_copy = [c for c in pool if c != card]

        c_vec,  d_vec = encode_state_structured(pd, od, p_copy, draft_idx)
        all_card.append(c_vec)
        # all_picker.append(p_vec)
        # all_other.append(o_vec)
        # all_pool.append(pool_vec)
        all_draft.append(d_vec)
        candidate_cards.append(card)

    if not candidate_cards:
        return [], []

    card_batch = torch.cat(all_card, dim=0)
    # other_batch = torch.cat(all_other, dim=0)
    # pool_batch = torch.cat(all_pool, dim=0)
    draft_batch = torch.cat(all_draft, dim=0)

    with torch.no_grad():
        vals = model(card_batch,  draft_batch)

    return candidate_cards, vals.squeeze(-1).cpu().tolist()

# -----------------------
# Minimax selection
# -----------------------
def pick_minimax_scores(deck, other_deck, pool, draft_idx):
    card_to_score = {}

    for my_card in pool:
        remaining_pool = [c for c in pool if c != my_card]
        worst_case_score = float("inf")

        for opp_card in remaining_pool:
            my_next = deck + [my_card]
            opp_next = other_deck + [opp_card]
            pool_after_opp = [c for c in remaining_pool if c != opp_card]

            candidate_cards, vals = pick_scores(opp_next, my_next, pool_after_opp, draft_idx - 1)
            score = max(vals) if vals else 0.0
            if score < worst_case_score:
                worst_case_score = score

        card_to_score[my_card] = worst_case_score

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
                if pick_i == pick_count - 1:
                    selected, scores_dict = pick_minimax_scores(deck, other_deck, pool, cumulative_pick)
                    print(f"Turn {cumulative_pick}, AI picked: {selected}")
                else:
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
# AI vs AI
# -----------------------
def play_against_itself():
    board = Board()
    pool = board.board.copy()
    ai1, ai2 = [], []
    cumulative_pick = 8

    print("\n=== AI vs AI Draft ===")

    for turn_idx, pick_count in enumerate(draftorder):
        is_ai1_turn = (turn_idx % 2 == 0)
        deck = ai1 if is_ai1_turn else ai2
        other_deck = ai2 if is_ai1_turn else ai1
        current_ai = "AI1" if is_ai1_turn else "AI2"

        for pick_i in range(pick_count):
            if not pool:
                break

            if pick_i == pick_count - 1:
                selected, _ = pick_minimax_scores(deck, other_deck, pool, cumulative_pick)
                print(f"Turn {cumulative_pick}, {current_ai} (minimax) picked: {selected}")
            else:
                candidate_cards, scores = pick_scores(deck, other_deck, pool, cumulative_pick)
                selected = candidate_cards[scores.index(max(scores))]
                print(f"Turn {cumulative_pick}, {current_ai} (greedy) picked: {selected}")

            deck.append(selected)
            pool.remove(selected)

        cumulative_pick -= 1

    print("\nFinal decks:")
    print("AI1:", ai1)
    print("AI2:", ai2)

# -----------------------
if __name__ == "__main__":
    # play_against_human()
    play_against_itself()
