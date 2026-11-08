

class Card:
     def __init__(self, name, categories, elixer):
        self.name = name
        self.categories = categories
        self.elixer = elixer
        # self.id = 0

     def __str__(self):
        
        print_string = f"Card({self.name}, {self.categories}, {self.elixer})"

        return print_string
     
card_list=[
Card("royal delivery", ['damage_spell'], 3),
Card("hunter", ['anti_air', 'anti_tank'], 4),
Card("prince", ['mini_tank'], 5),
Card("goblin hut", ['building'], 5),
Card("bats", ['anti_air'], 2),
Card("bomber", ['distraction'],2),
Card("wall breakers", ['win_condition'], 2),
Card("suspicious bush", ['win_condition'], 2),
Card("ice wizard", ['anti_air'], 3),
Card("goblins", ['distraction'], 2),
Card("flying machine", ['anti_air'], 4),
Card("lumberjack", ['anti_tank'], 4),
Card("golem", ['tank'], 8),
Card("mega knight", ['tank'], 7),
Card("three musketeers", ['win_condition'], 9),
Card("skeleton barrel", ['win_condition'], 3),
Card("valkyrie", ['tank', 'mini_tank'], 4),
Card("goblinstein", ['champion'], 5),
Card("goblin giant", ['tank', 'win_condition'], 6),
Card("tombstone", ['building'], 3),
Card("mortar", ['building'], 4),
Card("lightning", ['damage_spell', 'second_spell'], 6),
Card("wizard", ['anti_air'], 5),
Card("goblin drill", ['tank', 'win_condition'], 4),
Card("mega minion", ['anti_air'], 3),
Card("hog rider", ['win_condition'], 4),
Card("berserker", ['distraction', 'mini_tank'], 2),
Card("giant skeleton", ['tank'], 6),
Card("fisherman", ['mini_tank'], 3),
Card("barbarian hut", ['building'], 6),
Card("mighty miner", ['champion'], 4),
Card("tesla", ['anti_tank', 'building'], 4),
Card("executioner", ['anti_air'], 5),
Card("bomb tower", ['anti_tank', 'building'], 4),
Card("goblin machine", ['tank', 'mini_tank'], 5),
Card("monk", ['champion'], 5),
Card("archers", ['anti_air'], 3),
Card("electro wizard", ['anti_air'], 4),
Card("minions", ['anti_air', 'distraction'], 3),
Card("phoenix", ['anti_air'], 4),
Card("royal giant", ['tank', 'win_condition'], 6),
Card("little prince", ['champion'], 3),
Card("archer queen", ['champion'], 5),
Card("miner", ['tank', 'win_condition', 'mini_tank'], 3),
Card("sparky", ['anti_tank'], 6),
Card("skeleton dragons", ['anti_air'], 4),
Card("zappies", ['anti_air'], 4),
Card("battle ram", ['win_condition'], 4),
Card("goblin cage", ['mini_tank', 'anti_tank', 'building'], 4),
Card("the log", ['damage_spell', 'second_spell'], 2),
Card("ram rider", ['win_condition'], 5),
Card("ice spirit", ['distraction'], 1),
Card("inferno tower", ['anti_tank', 'building'], 5),
Card("elixir golem", ['tank', 'win_condition'], 3),
Card("void", ['damage_spell'], 3),
Card("skeleton army", ['distraction'], 3),
Card("boss bandit", ['champion'], 6),
Card("knight", ['tank', 'mini_tank'], 3),
Card("minion horde", ['anti_air'], 5),
Card("goblin barrel", ['win_condition'], 3),
Card("cannon cart", ['mini_tank', 'anti_tank'], 5),
Card("firecracker", ['anti_air'], 3),
Card("tornado", ['second_spell'], 3),
Card("freeze", ['second_spell'], 4),
Card("cannon", ['anti_tank', 'building'], 3),
Card("battle healer", ['mini_tank'], 4),
Card("electro dragon", ['anti_air'], 5),
Card("barbarian barrel", ['damage_spell', 'second_spell'], 2),
Card("royal recruits", ['tank'], 7),
Card("bowler", ['tank'], 5),
Card("elixir collector", ['building'], 6),
Card("balloon", ['win_condition'], 5),
Card("goblin curse", ['damage_spell', 'second_spell'], 2),
Card("magic archer", ['anti_air'], 4),
Card("fire spirit", ['distraction'], 1),
Card("mini p.e.k.k.a", ['mini_tank', 'anti_tank'], 4),
Card("x-bow", ['building'], 6),
Card("giant", ['tank', 'win_condition'], 5),
Card("royal ghost", ['mini_tank'], 3),
Card("spear goblins", ['anti_air', 'distraction'], 2),
Card("fireball", ['damage_spell', 'second_spell'], 4),
Card("skeletons", ['distraction'], 1),
Card("ice golem", ['tank', 'distraction'], 2),
Card("poison", ['damage_spell', 'second_spell'], 4),
Card("rune giant", ['tank', 'win_condition'], 4),
Card("heal spirit", ['distraction'], 1),
Card("princess", ['anti_air'], 3),
Card("bandit", ['mini_tank'], 3),
Card("giant snowball", ['damage_spell', 'second_spell'], 2),
Card("elite barbarians", ['anti_tank'], 6),
Card("arrows", ['damage_spell', 'second_spell'], 3),
Card("witch", ['anti_air', 'anti_tank'], 5),
Card("furnace", ['building'], 4),
Card("musketeer", ['anti_air'], 4),
Card("earthquake", ['damage_spell', 'second_spell'], 3),
Card("dark prince", ['mini_tank'], 4),
Card("baby dragon", ['anti_air'], 4),
Card("electro giant", ['tank'], 7),
Card("lava hound", ['tank'], 7),
Card("barbarians", ['anti_tank'], 5),
Card("rocket", ['damage_spell', 'second_spell'], 6),
Card("goblin gang", ['distraction'], 3),
Card("night witch", ['anti_air'], 4),
Card("graveyard", ['win_condition'], 5),
Card("dart goblin", ['anti_air'], 3),
Card("rage", ['damage_spell'], 2),
Card("skeleton king", ['champion'], 4),
Card("zap", ['damage_spell', 'second_spell'], 2),
Card("royal hogs", ['win_condition'], 5),
Card("guards", ['distraction'], 3),
Card("p.e.k.k.a", ['anti_tank'], 7),
Card("rascals", ['tank', 'mini_tank', 'anti_tank'], 5),
Card("inferno dragon", ['anti_air', 'anti_tank'], 4),
Card("electro spirit", ['distraction'], 1),
Card("mother witch", ['anti_air'], 4),
Card("golden knight", ['champion'], 4),
Card("clone", ['none'], 3),
Card("mirror", ['none'], 0),
Card("spirit empress", ['none'], 6),
Card("goblin demolisher", ['none'], 4),
Card("vines", ['none'], 3),
]

name_to_id = {}
for  i, card in enumerate(card_list):
    # card.id = i
    name_to_id[card.name] = card_list.index(card)
category_totals = {"tank": 4,
        "anti_air": 4,
         "distraction": 4,
         "damage_spell": 4,
        "win_condition": 6,
         "second_spell": 2,
        "mini_tank": 3,
         "anti_tank": 3,
        "champion": 3,
         "building": 3}
categorized_cards = {}
for card in card_list:
    for category in card.categories:
        if category == "none":
            continue
        if category not in categorized_cards:
            categorized_cards[category] = []
        categorized_cards[category]+=[card]

# print(categorized_cards)
# print(len(card_list))