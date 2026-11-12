import torch
import cardhelpers as ch
import trainer  # or wherever your ValueNet class is
from itertools import combinations
import math
import random
# -----------------------
# Config
# -----------------------
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MATCHUP_MODE = "concat"  # "concat" or "difference"
TARGET_MODE = "win"      # "win" (BCE) or "health_diff" (MSE)
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
def load_model():
    matchup_mode = MATCHUP_MODE
    target_mode = TARGET_MODE
    path = f"value_net_{matchup_mode}_{target_mode}_best.pth"

    model = trainer.OptimizedValueNet(
        matchup_mode=matchup_mode,
        target_mode=target_mode,
    ).to(DEVICE)
    model.load_state_dict(torch.load(path, map_location=DEVICE))
    model.eval()
    print(f"Loaded {path}")
    return model


model = load_model()


model.load_state_dict(torch.load(f"value_net_{MATCHUP_MODE}_{TARGET_MODE}_best.pth", map_location=DEVICE))
model.eval()

# -----------------------
# Scoring function
# -----------------------
def score_matchup(deck1, deck2):
    vec1 = deck_to_tensor(deck1)  # [1, num_cards]
    vec2 = deck_to_tensor(deck2) # [1, num_cards]W
    return score_matchup_tensors(vec1, vec2)
    # return score.item()
def score_matchup_tensors(deck1, deck2):
    with torch.no_grad():
        logit = model(trainer.vectorize_deck(deck1), trainer.vectorize_deck(deck2))
        return torch.sigmoid(logit).item()
# -----------------------
# Example usage
# -----------------------

matchups = [
    (
        "Splash and spells vs swarm",
        ["valkyrie", "wizard", "baby dragon", "bomber",
            "arrows", "mother witch", "hog rider", "cannon"],
        ["skeletons", "goblins", "skeleton army", "bats",
            "minion horde", "goblin gang", "miner", "goblin barrel"],
    ),
    (
        "Air-heavy deck vs almost no anti-air",
        ["balloon", "lava hound", "baby dragon", "mega minion",
            "minions", "tombstone", "arrows", "fireball"],
        ["knight", "valkyrie", "mini p.e.k.k.a", "bomber",
            "skeleton army", "goblins", "the log", "zap"],
    ),
    (
        "Tank killers vs expensive ground tanks",
        ["p.e.k.k.a", "inferno tower", "mini p.e.k.k.a", "skeleton army",
            "musketeer", "zap", "fireball", "hog rider"],
        ["golem", "giant", "royal giant", "goblin giant",
            "electro giant", "elixir golem", "knight", "bomber"],
    ),
    (
        "A favored | Air pressure vs ground-only defense",
        ["lava hound", "balloon", "mega minion", "baby dragon",
            "tombstone", "guards", "arrows", "fireball"],
        ["golem", "prince", "mini p.e.k.k.a", "valkyrie",
            "bomber", "cannon", "goblins", "the log"],
    ),
    (
        "A favored | Multiple splash answers vs swarm bait",
        ["hog rider", "valkyrie", "baby dragon", "bomber",
            "cannon", "arrows", "the log", "fireball"],
        ["goblin barrel", "skeleton barrel", "skeleton army", "goblin gang",
            "minion horde", "bats", "knight", "zap"],
    ),
    (
        "A favored | Tank killers vs slow ground push",
        ["p.e.k.k.a", "inferno tower", "musketeer", "guards",
            "hog rider", "ice spirit", "fireball", "zap"],
        ["golem", "giant", "bowler", "knight",
            "baby dragon", "mega minion", "tornado", "arrows"],
    ),
    (
        "Roughly even | Two Hog-style cycle decks",
        ["hog rider", "musketeer", "cannon", "ice golem",
            "skeletons", "ice spirit", "fireball", "the log"],
        ["ram rider", "archers", "skeletons", "knight",
            "goblins", "electro spirit", "poison", "barbarian barrel"],
    ),
    (
        "Roughly even | Two Miner control decks",
        ["miner", "wall breakers", "knight", "bats",
            "bomb tower", "spear goblins", "poison", "the log"],
        ["miner", "goblin barrel", "valkyrie", "archers",
            "cannon", "skeletons", "fireball", "barbarian barrel"],
    ),
    (
        "Roughly even | Two ground beatdown decks",
        ["giant", "prince", "dark prince", "mega minion",
            "musketeer", "fireball", "zap", "guards"],
        ["goblin giant", "mini p.e.k.k.a", "valkyrie", "minions",
            "hunter", "poison", "arrows", "goblins"],
    ),
]




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

def best_choice(pool, multi_hot_decks, turn, player):
    turn_player = ((turn+1)//2)%2   
    num_turns = turn%2+1
    if(turn==15):
        num_turns =1
    b_choice =[]
    b_wr = 1
    if(turn_player==player):
        b_wr=0
    temp_choice =[]
    temp_wr = 0
    choices =list(combinations(pool, num_turns))
    for choice in choices:
        sub_pool= pool.copy()
        sub_decks= multi_hot_decks.copy()
        sub_decks[turn_player] = multi_hot_decks[turn_player].clone()
        for card in choice:
            sub_pool.remove(card)
            sub_decks[turn_player][ch.name_to_id[card]] =1.0
        if(turn==15):
            temp_wr = score_matchup_tensors(sub_decks[player], sub_decks[1-player])  #base case
        else:
            temp_choice, temp_wr =best_choice(sub_pool, sub_decks, turn+num_turns, player)
        if(turn_player==player):
            if(temp_wr>b_wr):
                b_wr = temp_wr
                b_choice= choice
        else:
            if(temp_wr<b_wr):
                b_wr = temp_wr
                b_choice= choice
    return b_choice, b_wr


def manual_draft(random_turns= 13, unassisted_turns=0):
    pool = ch.generate_pool()
    decks = [[], []]
    for i in range(2):
        decks[i] = random.sample(list(pool), math.floor((random_turns-1-2*i)/4)+math.floor((random_turns-2*i)/4)+1+i);
        for card in decks[i]:
            pool.remove(card)
    choice =[]
    card =""
    for turn in range(random_turns, 16):
        turn_player = ((turn+1)//2)%2   
        print(f" Pool: {', '.join(pool)}")
        print(f"Player {0}'s deck: {', '.join(decks[0])}")    
        print(f"Player {1}'s deck: {', '.join(decks[1])}")  
        print(f"Player {turn_player}'s turn.") 
        if(turn>=(unassisted_turns+random_turns) or (card not in choice)):
            print("Determining best choice...")
            choice, wr = best_choice(pool, [deck_to_tensor(decks[0]),deck_to_tensor(decks[1])], turn, turn_player)
            print(f"Recommended card/s are {', '.join(choice)} with a worst-case winrate of {wr*100}%")
        card = input("Pick a card: ").strip().lower()
        while card not in pool:
            card = input("Invalid input, pick a card: ").strip().lower()


        decks[turn_player].append(card)
        pool.remove(card)

        print(f"Player {0}'s deck: {', '.join(decks[0])}")    
        print(f"Player {1}'s deck: {', '.join(decks[1])}")  
        # print(player) 


if __name__ == "__main__":
    manual_draft()
    # for name, deck_a, deck_b in matchups:
    #     ab = score_matchup(deck_a, deck_b)
    #     ba = score_matchup(deck_b, deck_a)
    #     print(f"{name}: A vs B {ab*100:.4f}% | B vs A {ba*100:.4f}%")
    # rng = random.Random()  # Use random.Random(42) for repeatable matchups.
    # deck_a, deck_b = random_matchup(rng)

    # print("Deck A:", ", ".join(deck_a))
    # print("Deck B:", ", ".join(deck_b))
    # print(f"A vs B: {score_matchup(deck_a, deck_b)*100:.4f}%")
    # print(f"B vs A: {score_matchup(deck_b, deck_a)*100:.4f}%")