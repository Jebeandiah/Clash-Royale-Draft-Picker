import torch
import cardhelpers as ch
from trainer import ValueNet  # or wherever your ValueNet class is

# -----------------------
# Config
# -----------------------
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MODEL_PATH = "value_net_best.pth"

# -----------------------
# Helper to convert a deck to bit vector
# -----------------------
def deck_to_vector(deck):
    """
    deck: list of card names, e.g. ['Archer', 'Giant', ...]
    Returns: torch tensor of shape [len(ch.card_list)*2]
    """
    vec = torch.zeros(len(ch.card_list), dtype=torch.float32, device=DEVICE)
    for card in deck:
        idx = ch.name_to_id[card.lower()]
        vec[idx] = 1.0  # your first 8-card deck
    return vec

# -----------------------
# Load model
# -----------------------
model = ValueNet().to(DEVICE)
model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE))
model.eval()

# -----------------------
# Scoring function
# -----------------------
def score_matchup(deck1, deck2):
    vec1 = deck_to_vector(deck1).unsqueeze(0)  # [1, num_cards]
    vec2 = deck_to_vector(deck2).unsqueeze(0)  # [1, num_cards]
    with torch.no_grad():
        score = model(vec1, vec2)
    return score.item()

# -----------------------
# Example usage
# -----------------------
if __name__ == "__main__":
    deck_a = ['the log', 'cannon', 'goblin barrel', 'goblin gang', 'princess', 'dart goblin', 'skeletons', 'arrows']
    deck_b = ['goblins', 'tornado', 'goblin gang', 'hog rider', 'arrows', 'guards', 'the log', 'Valkyrie']
    # deck_b = ['hog rider', 'Cannon', 'Ice Spirit', 'Skeletons', 'Fire Spirit', 'Mini P.E.K.K.A', 'Arrows', 'Valkyrie']
    # deck_b = ['arrows', 'ice spirit', 'hog rider', 'the log', 'hunter', 'earthquake', 'skeletons', 'mini p.e.k.k.a']
    scorea = score_matchup(deck_a, deck_b)
    scoreb= score_matchup(deck_b, deck_a)
    # result = score_matchup(deck_a, deck_b)-score_matchup(deck_b, deck_a)
    print(f"Predicted matchup score (Deck A vs Deck B): {scorea} {scoreb}")
