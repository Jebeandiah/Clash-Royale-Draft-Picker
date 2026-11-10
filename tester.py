import torch
import cardhelpers as ch
import trainer  # or wherever your ValueNet class is
import random
# -----------------------
# Config
# -----------------------
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MODEL_PATH = "value_net_best.pth"

# -----------------------
# Helper to convert a deck to bit vector
# -----------------------
def deck_to_tensor(deck):
    """
    deck: list of card names, e.g. ['Archer', 'Giant', ...]
    Returns: torch tensor of shape [len(ch.card_list)*2]
    """
    vec = torch.zeros(len(ch.card_list), dtype=torch.float32, device=DEVICE)
    for card in deck:
        idx = ch.name_to_id[card.lower()]
        vec[idx] = 1.0  # your first 8-card deck
    return vec.flatten()

# -----------------------
# Load model
# -----------------------
model = trainer.OptimizedValueNet().to(DEVICE)
model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE))
model.eval()

# -----------------------
# Scoring function
# -----------------------
def score_matchup(deck1, deck2):
    vec1 = deck_to_tensor(deck1)  # [1, num_cards]
    vec2 = deck_to_tensor(deck2) # [1, num_cards]W
    with torch.no_grad():
        score = model(trainer.vectorize_deck(vec1), trainer.vectorize_deck(vec2))
    return score.item()

# -----------------------
# Example usage
# -----------------------
# if __name__ == "__main__":
#     matchups = [
#     (
#         "Splash and spells vs swarm",
#         ["valkyrie", "wizard", "baby dragon", "bomber",
#          "arrows", "mother witch", "hog rider", "cannon"],
#         ["skeletons", "goblins", "skeleton army", "bats",
#          "minion horde", "goblin gang", "miner", "goblin barrel"],
#     ),
#     (
#         "Air-heavy deck vs almost no anti-air",
#         ["balloon", "lava hound", "baby dragon", "mega minion",
#          "minions", "bats", "arrows", "fireball"],
#         ["knight", "valkyrie", "skeletons", "bomber",
#          "skeleton army", "goblins", "the log", "golem"],
#     ),
#     (
#         "Tank killers vs expensive ground tanks",
#         ["p.e.k.k.a", "inferno tower", "mini p.e.k.k.a", "skeleton army",
#          "musketeer", "zap", "fireball", "hog rider"],
#         ["golem", "giant", "royal giant", "goblin giant",
#          "electro giant", "elixir golem", "knight", "bomber"],
#     ),
# ]

#     for name, deck_a, deck_b in matchups:
#         ab = score_matchup(deck_a, deck_b)
#         ba = score_matchup(deck_b, deck_a)
#         print(f"{name}: A vs B {ab:+.4f} | B vs A {ba:+.4f}")


def random_matchup(rng):
    # Fill categories with fewer spare cards first.
    categories = sorted(
        ch.category_totals,
        key=lambda category: (
            len(ch.categorized_cards[category]) - ch.category_totals[category]
        ),
    )

    for _ in range(100):
        pool = set()

        for category in categories:
            count = ch.category_totals[category]
            candidates = sorted(
                {card.name for card in ch.categorized_cards[category]} - pool
            )

            if len(candidates) < count:
                break

            pool.update(rng.sample(candidates, count))
        else:
            picks = rng.sample(sorted(pool), 16)
            return picks[:8], picks[8:]

    raise ValueError("Could not fill the draft pool with unique cards.")


if __name__ == "__main__":
    rng = random.Random()  # Use random.Random(42) for repeatable matchups.
    deck_a, deck_b = random_matchup(rng)

    print("Deck A:", ", ".join(deck_a))
    print("Deck B:", ", ".join(deck_b))
    print(f"A vs B: {score_matchup(deck_a, deck_b):+.4f}")
    print(f"B vs A: {score_matchup(deck_b, deck_a):+.4f}")