

import random


class Card:
     def __init__(self, name, categories, elixir, properties=[]):
        self.name = name
        self.categories = categories
        self.elixir = elixir
        self.properties = properties
        # self.id = 0

     def __str__(self):
        
        # print_string = f"Card({self.name}, {self.categories}, {self.elixir})"
        print_string = f"{self.name}"
        return print_string

     def __repr__(self):
        return self.__str__()

card_list=[
Card("ronin", ['anti_tank', 'mini_tank'], 5, ['dps', 'tank']),
Card("royal delivery", ['damage_spell'], 3, ['small_spell', 'splash', 'distraction']),
Card("hunter", [ 'anti_tank', 'anti_air'], 4, ['dps', 't_air', 'splash']),
Card("prince", ['mini_tank'], 5, ['dps', 'tank', 'aggro', 'retarget']),
Card("goblin hut", ['building'], 5, ['building', 't_air', 'spawner']),
Card("bats", ['anti_air'], 2, ['air', 'swarm', 't_air', 'dps']),
Card("bomber", ['distraction'],2, ['splash']),
Card("wall breakers", ['win_condition'], 2, ['t_building', 'aggro']),
Card("suspicious bush", ['win_condition'], 2, ['t_building', 'aggro']),
Card("ice wizard", ['anti_air'], 3, ['splash', 't_air', 'slow']),
Card("goblins", ['distraction'], 2, ['swarm', 'dps']),
Card("flying machine", ['anti_air'], 4, ['air']),
Card("lumberjack", ['anti_tank'], 4, ['dps', 'aggro', 'support']),
Card("golem", ['tank'], 8, ['tank', 't_building']),
Card("mega knight", ['tank'], 7, ['tank', 'splash']),
Card("three musketeers", ['win_condition'], 9, ['dps', 't_air']),
Card("skeleton barrel", ['win_condition'], 3, ['air', 't_building', 'swarm']),
Card("valkyrie", ['tank', 'mini_tank'], 4, ['tank', 'splash']),
Card("goblinstein", ['champion'], 5, ['tank', 't_air', 'slow']),
Card("goblin giant", ['win_condition', 'tank'], 6, ['tank', 't_building']),
Card("tombstone", ['building'], 3, ['building', 'swarm', 'spawner']),
Card("mortar", ['building'], 4, ['building', 't_building', 'splash', 'aggro', 'retarget']),
Card("lightning", ['damage_spell', 'second_spell'], 6, ['big_spell', 'd_anywhere']),
Card("wizard", ['anti_air'], 5, ['dps', 'splash', 't_air']),
Card("goblin drill", [ 'win_condition','tank'], 4, ['t_building', 'aggro', 'spawner', 'd_anywhere']),
Card("mega minion", ['anti_air'], 3, ['air', 'dps', 't_air']),
Card("hog rider", ['win_condition'], 4, ['t_building', 'aggro']),
Card("berserker", ['distraction', 'mini_tank'], 2, ['distraction', 'aggro']),
Card("giant skeleton", ['tank'], 6, ['tank']),
Card("fisherman", ['mini_tank'], 3, ['distraction', 'aggro', 'support']),
Card("barbarian hut", ['building'], 6, ['building', 'spawner']),
Card("mighty miner", ['champion'], 4, ['dps', 'tank', 'retarget']),
Card("tesla", [ 'building', 'anti_tank'], 4, ['building', 't_air', 'dps']),
Card("executioner", ['anti_air'], 5, ['splash', 't_air']),
Card("bomb tower", [ 'building', 'anti_tank'], 4, ['building', 'splash']),
Card("goblin machine", ['tank', 'mini_tank'], 5, ['tank']),
Card("monk", ['champion'], 5, ['dps', 'tank', 'slow']),
Card("archers", ['anti_air'], 3, ['t_air']),
Card("electro wizard", ['anti_air'], 4, ['t_air', 'slow']),
Card("minions", ['anti_air', 'distraction'], 3, ['t_air', 'air', 'dps', 'swarm']),
Card("phoenix", ['anti_air'], 4, ['t_air', 'tank', 'dps']),
Card("royal giant", ['win_condition', 'tank' ], 6, ['tank', 't_building']),
Card("little prince", ['champion'], 3, ['t_air', 'tank', 'dps']),
Card("archer queen", ['champion'], 5, ['t_air',  'dps']),
Card("miner", ['win_condition','tank', 'mini_tank'], 3, ['t_building', 'aggro', 'distraction', 'd_anywhere']),
Card("sparky", ['anti_tank'], 6, ['dps', 'splash', 'retarget']),
Card("skeleton dragons", ['anti_air'], 4, ['t_air', 'splash', 'air']),
Card("zappies", ['anti_air'], 4, ['t_air', 'dps', 'slow']),
Card("battle ram", ['win_condition'], 4, ['t_building', 'aggro', 'distraction', 'retarget']),
Card("goblin cage", ['building', 'mini_tank', 'anti_tank' ], 4, ['building', 'dps', 'distraction']),
Card("the log", ['damage_spell', 'second_spell'], 2, ['slow', 'small_spell', 'splash']),
Card("ram rider", ['win_condition'], 5, ['t_air', 't_building', 'slow', 'distraction', 'retarget']),
Card("ice spirit", ['distraction'], 1, ['distraction', 'slow']),
Card("inferno tower", ['building', 'anti_tank'], 5, ['building', 'anti_tank', 'retarget']),
Card("elixir golem", ['win_condition', 'tank'], 3, ['t_building', 'tank']),
Card("void", ['damage_spell'], 3, ['big_spell', 'splash', 'd_anywhere']),
Card("skeleton army", ['distraction'], 3, ['dps', 'swarm', 'distraction']),
Card("boss bandit", ['champion'], 6, ['tank', 'dps', 'aggro', 'retarget']),
Card("knight", ['tank', 'mini_tank'], 3, ['tank', 'distraction']),
Card("minion horde", ['anti_air'], 5, ['t_air', 'swarm', 'dps', 'air']),
Card("goblin barrel", ['win_condition'], 3, ['t_building', 'aggro', 'swarm', 'd_anywhere']),
Card("cannon cart", ['mini_tank', 'anti_tank'], 5, ['dps', 'tank']),
Card("firecracker", ['anti_air'], 3, ['t_air', 'splash']),
Card("tornado", ['second_spell'], 3, ['small_spell', 'support', 'd_anywhere']),
Card("freeze", ['second_spell'], 4, ['small_spell', 'support', 'splash', 'slow', 'd_anywhere']),
Card("cannon", ['building', 'anti_tank'], 3, ['building']),
Card("battle healer", ['mini_tank'], 4, ['tank', 'support']),
Card("electro dragon", ['anti_air'], 5, ['anti_air', 'air', 'slow']),
Card("barbarian barrel", ['damage_spell', 'second_spell'], 2, ['small_spell', 'distraction']),
Card("royal recruits", ['tank'], 7, ['swarm', 'tank', 'dps']),
Card("bowler", ['tank'], 5, ['tank', 'splash', 'slow']),
Card("elixir collector", ['building'], 6, ['building']),
Card("balloon", ['win_condition'], 5, ['t_building', 'air']),
Card("goblin curse", ['damage_spell', 'second_spell'], 2, ['small_spell', 'swarm', 'support', 'd_anywhere']),
Card("magic archer", ['anti_air'], 4, ['t_air', 'splash', 'dps', 'support']),
Card("fire spirit", ['distraction'], 1, ['distraction', 'splash']),
Card("mini p.e.k.k.a", ['anti_tank', 'mini_tank'], 4, ['dps', 'aggro']),
Card("x-bow", ['building'], 6, ['building', 't_building', 'aggro', 'retarget']),
Card("giant", [ 'win_condition', 'tank'], 5, ['t_building', 'tank']),
Card("royal ghost", ['mini_tank'], 3, ['splash', 'distraction']),
Card("spear goblins", [ 'distraction', 'anti_air'], 2, ['t_air', 'distraction','swarm', 'aggro']),
Card("fireball", ['damage_spell', 'second_spell'], 4, ['big_spell', 'splash', 'd_anywhere']),
Card("skeletons", ['distraction'], 1, ['distraction', 'swarm']),
Card("ice golem", ['distraction', 'tank'], 2, ['distraction', 'tank']),
Card("poison", ['damage_spell', 'second_spell'], 4, ['big_spell', 'splash', 'd_anywhere']),
Card("rune giant", ['win_condition', 'tank'], 4, ['t_building', 'tank', 'support']),
Card("heal spirit", ['distraction'], 1, ['distraction', 'support']),
Card("princess", ['anti_air'], 3, ['t_air', 'splash', 't_building', 'aggro']),
Card("bandit", ['mini_tank'], 3, ['distraction', 'dps', 'aggro', 'retarget']),
Card("giant snowball", ['damage_spell', 'second_spell'], 2, ['small_spell', 'splash', 'slow', 'd_anywhere']),
Card("elite barbarians", ['anti_tank'], 6, ['tank', 'dps', 'aggro']),
Card("arrows", ['damage_spell', 'second_spell'], 3, ['small_spell', 'splash', 'd_anywhere']),
Card("witch", ['anti_tank','anti_air'], 5, ['t_air', 'splash', 'spawner']),
Card("furnace", ['building'], 4, ['t_air', 'dps', 'splash', 'spawner']),
Card("musketeer", ['anti_air'], 4, ['t_air', 'dps']),
Card("earthquake", ['damage_spell', 'second_spell'], 3, ['small_spell', 't_building', 'd_anywhere']),
Card("dark prince", ['mini_tank'], 4, ['tank', 'splash', 'aggro', 'retarget']),
Card("baby dragon", ['anti_air'], 4, ['t_air', 'splash', 'air']),
Card("electro giant", ['tank'], 7, ['tank', 'splash']),
Card("lava hound", ['tank'], 7, ['tank', 'air', 'swarm', 't_building']),
Card("barbarians", ['anti_tank'], 5, ['dps',  'swarm']),
Card("rocket", ['damage_spell', 'second_spell'], 6, ['big_spell', 'd_anywhere']),
Card("goblin gang", ['distraction'], 3, ['distraction', 'swarm', 'dps']),
Card("night witch", ['anti_air'], 4, ['t_air', 'dps', 'air', 'spawner']),
Card("graveyard", ['win_condition'], 5, ['t_building', 'swarm', 'aggro', 'd_anywhere']),
Card("dart goblin", ['anti_air'], 3, ['t_air', 'dps', 'aggro']),
Card("rage", ['damage_spell'], 2, ['small_spell', 'support', 'd_anywhere']),
Card("skeleton king", ['champion'], 4, ['splash', 'tank', 'swarm', 'spawner']),
Card("zap", ['damage_spell', 'second_spell'], 2, ['small_spell', 'splash', 'slow', 'd_anywhere']),
Card("royal hogs", ['win_condition'], 5, ['t_building', 'swarm', 'aggro']),
Card("guards", ['distraction'], 3, ['distraction', 'swarm']),
Card("p.e.k.k.a", ['anti_tank'], 7, ['tank', 'dps']),
Card("rascals", ['tank', 'mini_tank', 'anti_tank'], 5, ['tank', 't_air', 'dps']),
Card("inferno dragon", ['anti_air', 'anti_tank'], 4, ['t_air', 'dps', 'air', 'retarget']),
Card("electro spirit", ['distraction'], 1, ['distraction', 'swarm', 'slow']),
Card("mother witch", ['anti_air'], 4, ['splash', 't_air', 't_building', 'distraction', 'spawner']),
Card("golden knight", ['champion'], 4, ['dps', 'tank', 'aggro', 'retarget']),
Card("clone", ['second_spell'], 3, ['swarm', 'support', 'd_anywhere']),
Card("mirror", ['second_spell'], 0, []),
Card("spirit empress", ['mini_tank'], 6, ['tank', 'dps', 'air', 't_air']),
Card("goblin demolisher", ['mini_tank'], 4, ['t_building', 'splash', 'aggro']),
Card("vines", ['second_spell'], 3, ['small_spell', 'slow', 'd_anywhere']),
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
properties_to_id = {}
for card in card_list:
    for property in card.properties:
        if property not in properties_to_id:
            properties_to_id[property] = len(properties_to_id)
    for category in card.categories:
        if category == "none":
            continue
        if category not in categorized_cards:
            categorized_cards[category] = []
        categorized_cards[category]+=[card]
def generate_pool():
    pool = set()
    for category, total in category_totals.items():
        for i in range(total):
            test_choice = random.choice(categorized_cards[category]).name
            while test_choice in pool:
                test_choice = random.choice(categorized_cards[category]).name
            pool.add(test_choice)
    return pool
# property_to_id = {}
# for card, category in enumerate(categorized_cards):
#     property_to_id[category] = i
# # print(categorized_cards)
# print(len(card_list))
# for category in categorized_cards:
#     print(category)
# print(category_to_id)