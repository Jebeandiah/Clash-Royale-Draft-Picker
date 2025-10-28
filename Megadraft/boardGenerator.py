import random
import copy

######################################################################

####################
# Global Variables #
####################

"""
Dictionary containing the different classes of cards used
by the megadraft board generation algorithm. Each class is
a set that contains all the cards within that class.

Some cards are in multiple classes:
    Ex: ice golem is in tank, mini_tank, and distraction
"""
cards = {
    "tank": ["ice golem", "knight", "miner", "elixir golem", "valkyrie", "rune giant",
             "goblin drill", "giant", "rascals", "bowler", "goblin demolisher", "royal giant",
             "giant skeleton", "goblin giant", "royal recruits", "megaknight", "electro giant",
             "lavahound", "golem"],
    "anti_air": ["spear goblins", "bats", "archers", "minions", "mega minion", "dart goblin",
                "princess", "firecracker", "ice wizard", "musketeer", "skeleton dragons",
                "flying machine", "baby dragon", "zappies", "hunter", "inferno dragon", 
                "electro wizard", "phoenix", "magic archer", "night witch", "mother witch",
                "wizard", "witch", "minion horde", "electro dragon", "executioner"],
    "distraction": ["skeletons", "fire sprit", "electro spirit", "ice spirit", "heal spirit",
                    "goblins", "spear goblins", "bomber", "ice golem", "berserker", "minions",
                    "skeleton army", "guards", "goblin gang"],
    "damage_spell": ["zap", "giant snowball", "barbarian barrel", "the log", "rage",
                    "goblin curse", "arrows", "earthquake", "royal delivery", "void", "fireball", 
                    "poison", "rocket", "lightning"],
    "win_condition": ["wallbreakers", "suspicious bush", "goblin barrel", "skeleton barrel", 
                      "miner", "elixir golem", "battle ram", "hog rider", "rune giant", 
                      "goblin drill", "giant", "royal hogs", "balloon", "ram rider", "graveyard",
                      "royal giant", "goblin giant", "three musketeers"],
    "second_spell": ["zap", "giant snowball", "barbarian barrel", "the log",
                    "goblin curse", "arrows", "earthquake", "tornado", "fireball", 
                    "freeze", "poison", "rocket", "lightning"],
    "mini_tank": ["berserker", "knight", "miner", "royal ghost", "bandit", "fisherman",
                  "mini pekka", "goblin cage", "valkyrie", "dark prince", "battle healer", 
                  "prince", "rascals", "cannon cart"],
    "anti_tank": ["cannon", "mini pekka", "goblin cage", "bomb tower", "tesla", "hunter", 
                  "inferno dragon", "lumberjack", "barbarians", "inferno tower", "witch",
                  "rascals", "cannon cart", "elite barbarians", "sparky", "pekka"],
    "champion": ["little prince", "skeleton king", "golden knight", "mighty miner",
                 "archer queen", "monk", "goblinstein", "boss bandit"], 
    "building": ["tombstone", "cannon", "goblin hut", "goblin cage", "bomb tower", "mortar",
                 "tesla", "furnace", "inferno tower", "barbarian hut", "xbow",
                 "elixir collector"]
}

"""
Flattened version of cards, so just a set of all cards
"""
all_cards = set().union(*cards.values())

#####################################################################

"""
Class that contains all the cards on a randomized megadraft board
"""
class Board:
    def __init__(self):
        self.cards = copy.deepcopy(cards)
        self.available_cards = copy.deepcopy(all_cards)
        self.board = self._generate_board()

    def reset(self):
        # Same as __init__
        self.cards = copy.deepcopy(cards)
        self.available_cards = copy.deepcopy(all_cards)
        self.board = self._generate_board()

    """
    Helper function that chooses a card numTimes from 
    the available pool given the passed cardType. Updates
    pool as needed to account for no repeats
    """
    def _pick_cards(self, cardType, numTimes):
        # Samples numTimes cards from specified pool 
        picked_cards = random.sample(self.cards[cardType], numTimes)
        
        # Removes picked cards from available pools
        for card in picked_cards:
            self.available_cards.remove(card)
            for cardType in self.cards:
                self.cards[cardType] = list(self.available_cards.intersection(set(self.cards[cardType])))

        return picked_cards

    """
    Returns a list containing 36 cards
    """
    def _generate_board(self):
        # Picks cards based on the correct ratios 
        tanks = Board._pick_cards(self, "tank", 4)
        anti_air = Board._pick_cards(self, "anti_air", 4)
        distraction = Board._pick_cards(self, "distraction", 4)
        damage_spell = Board._pick_cards(self, "damage_spell", 4)
        win_condition = Board._pick_cards(self, "win_condition", 6)
        second_spell = Board._pick_cards(self, "second_spell", 2)
        mini_tank = Board._pick_cards(self, "mini_tank", 3)
        anti_tank = Board._pick_cards(self, "anti_tank", 3)
        champion = Board._pick_cards(self, "champion", 3)
        building = Board._pick_cards(self, "building", 3)

        return tanks + anti_air + distraction + damage_spell + win_condition + \
            second_spell + mini_tank + anti_tank + champion + building

    """
    Printing a `Board()` prints the cards
    inside self.cards formatted in a table
    """
    def __str__(self):
        card_count = 0
        tab_count = 1
        print_string = ""
        for card in self.board:
            card_count += 1
            tab_count =  3- (len(card) // 8)
            print_string += card + (tab_count * "\t")
            if card_count % 6 == 0:
                print_string += "\n"

        return print_string




    

