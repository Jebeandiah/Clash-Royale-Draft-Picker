import random
import copy
import dBManager
import boardGenerator as bg
import sqlite3
import ast
import itertools

draftorder = [1, 2, 2, 2, 2, 2, 2, 2, 1]
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


def states_from_battle(battle, bcid, idtocat):
    category_counts = copy.deepcopy(category_totals)
   
    def generate_draft_pool():
        pool = []
        categories_satisfied = True
        current_choices =[]
        multi_choices =[]
        for card in battle["player_deck"]+battle["opp_deck"]:
            pool +=[card]
            categories = idtocat[card]
            choice = categories[0]
            if len(categories) >1:
                multi_choices+=[categories]
                choice = random.choice(categories)
                # print(categories)
                current_choices+=[choice]     
            if category_counts[choice] ==0: categories_satisfied = False
            category_counts[choice]-=1
            for category in categories:
                bcid[category].remove(card)
        textpool = []
        for card in generate_draft_pool():
            textpool+=[bg.card_list[card]]
        print(textpool)
        print(category_counts)
        print(current_choices)
        if not categories_satisfied:
            for choice in current_choices:
                category_counts[choice]+=1
            

            for combo in itertools.product(*multi_choices):
                categories_satisfied = True
                current_choices =[]
                for choice in combo:
                    print(category_counts[choice] )
                    if category_counts[choice] ==0:
                        categories_satisfied = False
                        break
                    category_counts[choice]-=1
                    current_choices += [choice]
                if categories_satisfied == True: break
                for choice in current_choices:
                    category_counts[choice]+=1
            
        for category in category_counts:
            for i in range(category_counts[category]):
                card = random.choice(bcid[category])
                for cat in idtocat[card]:
                    bcid[cat].remove(card)
                pool+=[card]
        return pool
    
    def pick_card(card_id):
        for category in idtocat[card_id]:
            bcid[category].remove(card_id)
        return
    states = [30]
    for i, pickcount in enumerate(draftorder):
        if pickcount ==1:
            break
    textpool = []
    for card in generate_draft_pool():
        textpool+=[bg.card_list[card]]
    # print(len(textpool))
    return


def generate_card_refs():
    categorized_ids = {}
    id_to_categories = {}
    for category in bg.cards:
        categorized_ids[category] = []
        for card in bg.cards[category]:
            card_id=bg.card_str_to_id(card)
            categorized_ids[category]+=[card_id]
            if card_id not in id_to_categories:
                id_to_categories[card_id] =[]
            id_to_categories[card_id] +=[category]
    return categorized_ids, id_to_categories
def collect_states( dbname=dBManager.dbname, limit=None):
    con = sqlite3.connect(f'{dbname}.db')
    cur = con.cursor()
    id_to_categories = {}
    base_categorized_ids = {}
    base_categorized_ids, id_to_categories = generate_card_refs()
    query = "SELECT * FROM battles"
    if limit:
        query += f" LIMIT {limit}"
    
    cur.execute(query)
    rows = cur.fetchall()
    battles = []
    for row in rows:
        # row: (id, player_crowns, opp_crowns, winner_low_tower, player_deck, opp_deck)
        battle = {
            "id": row[0],
            "player_crowns": row[1],
            "opp_crowns": row[2],
            "winner_low_tower": row[3],
            "player_deck": ast.literal_eval(row[4]),  # convert string back to list
            "opp_deck": ast.literal_eval(row[5])
        }
        battles.append(battle)
    for battle in battles:
        states_from_battle(battle, copy.deepcopy(base_categorized_ids), id_to_categories)
    con.close()

    # print(base_categorized_ids)

    return

if __name__ == "__main__":
    collect_states()
    # print(generate_card_refs())
    pls = "noerror"