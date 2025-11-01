import torch
from boardGenerator import Board, card_list
import testmodel

MODEL_PATH = "draft_mlp_score_dropout_norm.pth"
INPUT_LEN = 357
OUTPUT_LEN = 116
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

draftorder = [1, 2, 2, 2, 2, 2, 2, 2, 1]  # picks per turn, player 1 starts

# -----------------------
# Load model
# -----------------------
model = testmodel.DraftMLP().to(device)
model.load_state_dict(torch.load(MODEL_PATH, map_location=device), strict=False)
model.eval()

# -----------------------
# Encode current state to 357-long input
# -----------------------
def encode_state(picker_deck, other_deck, pool, draft_idx):
    vec = torch.zeros(INPUT_LEN, dtype=torch.float32)

    # Picker deck (0-115)
    for card in picker_deck:
        if card in card_list:
            vec[card_list.index(card)] = 1.0

    # Other deck (116-231)
    offset = 116
    for card in other_deck:
        if card in card_list:
            vec[offset + card_list.index(card)] = 1.0

    # Pool (232-347)
    offset = 232
    for card in pool:
        if card in card_list:
            vec[offset + card_list.index(card)] = 1.0

    # Draft step one-hot (348-356)
    offset = 348
    if draft_idx < 9:
        vec[offset + draft_idx] = 1.0

    return vec.unsqueeze(0).to(device)  # batch dim

# -----------------------
# Manual vs Model megadraft
# -----------------------
def simulate_megadraft():
    board = Board()
    pool = board.board.copy()
    player1_deck, player2_deck = [], []

    print("Starting Board Pool:")
    print(pool)
    print("\nDrafting cards...\n")

    cumulative_pick = 8
    for turn_idx, pick_count in enumerate(draftorder):
        player = 0 if turn_idx % 2 == 0 else 1  # player 1 starts
        deck = player1_deck if player == 0 else player2_deck

        for pick_num in range(pick_count):
            if not pool:
                break

            if player == 0:
                # --- Player 1 manual pick ---
                print("\nCurrent Pool:", pool)
                pick = input(f"Player 1, pick card {pick_num+1} of {pick_count}: ").strip()
                while pick not in pool:
                    pick = input("Invalid card. Pick again: ").strip()
                picked_card = pick
            else:
                # --- Player 2 model pick ---
                input_vec = encode_state(player2_deck, player1_deck, pool, cumulative_pick)
                with torch.no_grad():
                    logits = model(input_vec)
                    sorted_indices = torch.argsort(logits, descending=True)[0]
                    for idx in sorted_indices:
                        card_name = card_list[idx.item()]
                        if card_name in pool:
                            picked_card = card_name
                            break

            deck.append(picked_card)
            pool.remove(picked_card)
            print(f"Player {player+1} picked: {picked_card} | Remaining pool: {len(pool)} cards")

            cumulative_pick -= 1

    print("\nFinal Decks:")
    print("Player 1:", player1_deck)
    print("Player 2:", player2_deck)


# -----------------------
# Model vs Model self-play
# -----------------------
def simulate_self_play():
    board = Board()
    pool = board.board.copy()
    player1_deck, player2_deck = [], []

    print("Starting Board Pool (Self-Play):")
    print(pool)
    print("\nDrafting cards...\n")

    cumulative_pick = 8
    for turn_idx, pick_count in enumerate(draftorder):
        player = 0 if turn_idx % 2 == 0 else 1
        deck = player1_deck if player == 0 else player2_deck
        other_deck = player2_deck if player == 0 else player1_deck

        for pick_num in range(pick_count):
            if not pool:
                break

            # Model picks for both players
            input_vec = encode_state(deck, other_deck, pool, cumulative_pick)
            with torch.no_grad():
                logits = model(input_vec)
                sorted_indices = torch.argsort(logits, descending=True)[0]
                for idx in sorted_indices:
                    card_name = card_list[idx.item()]
                    if card_name in pool:
                        picked_card = card_name
                        break

            deck.append(picked_card)
            pool.remove(picked_card)
            print(f"Player {player+1} picked: {picked_card} | Remaining pool: {len(pool)} cards")

            cumulative_pick -= 1

    print("\nFinal Decks (Self-Play):")
    print("Player 1:", player1_deck)
    print("Player 2:", player2_deck)


if __name__ == "__main__":
    # Uncomment one of these to run
    # simulate_megadraft()    # Manual vs Model
    simulate_self_play()      # Model vs Model
