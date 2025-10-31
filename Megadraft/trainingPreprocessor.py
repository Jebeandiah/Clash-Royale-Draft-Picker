import random
import copy
import dBManager
import boardGenerator as bg
import sqlite3
import ast
import itertools
import array

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

class draft_state:
    def __init__(self):
        self.decks=[[],[]]
        self.pool=[]
        self.draftstep =0
        self.nextpick=0
        self.score=0
    def player_deck(self, player):
        return self.decks[player]
    def __str__(self):
        print_string = ""
        for card in self.pool:
            print_string += str(card) +", "
        print_string+=" /n"
        for card in self.decks[0]:
            print_string += str(card) +", "
        print_string+=" /n"
        for card in self.decks[1]:
            print_string += str(card) +", "
            

        return print_string
def states_from_battle(battle, bcid, idtocat):
    category_counts = copy.deepcopy(category_totals)
    # print(battle["id"])
    # print(bcid)
    # print(idtocat)
    # print(category_counts)
    # complete_decks = [battle["player_deck"]]+[battle["opp_deck"]]
    cs= draft_state()

    def generate_draft_pool():
        categories_satisfied = True
        current_choices =[]
        multi_choices =[]
        for card in battle["player_deck"]+battle["opp_deck"]:
            # pool.add(card)
            categories = idtocat[card]
            choice = categories[0]
            if len(categories) >1:
                multi_choices+=[categories]
                choice = random.choice(categories)
                # print(categories)
                current_choices+=[choice]     
            # print(f"{bg.card_list[card]} {choice} {categories}")
            if category_counts[choice] ==0: categories_satisfied = False
            category_counts[choice]-=1
            for category in categories:
                bcid[category].remove(card)
    
        if not categories_satisfied:
            for choice in current_choices:
                category_counts[choice]+=1
            

            for combo in itertools.product(*multi_choices):
                categories_satisfied = True
                current_choices =[]
                for choice in combo:
                    
                    # print(category_counts[choice] )
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
                cs.pool.append(card)
                # print("added card to pool "+str(card))
        return
    




    generate_draft_pool()
    states=[]
    def pick_card(p):
        cs.player_deck(p).append(cs.pool.pop())
        return
    def unpick_card(p):
        card= cs.player_deck(p).pop()
        cs.pool.append(card)
        cs.nextpick = card
        cs.draftstep = i
        states.append(copy.deepcopy(cs))
        return
    cs.decks =[battle["player_deck"]]+[battle["opp_deck"]]
    for i, pickcount in enumerate(draftorder):
        # player = i%2
        # ind = len(cs.player_deck(player))
        p = i%2
        cs.score = battle["low_tower_dif"]
        if p!=0:
            cs.score*=-1
        for j in range(pickcount):
            unpick_card(p)
        if pickcount >1:
            pick_card(p)
            pick_card(p)
            cs.player_deck(p)[-1],cs.player_deck(p)[-2]=cs.player_deck(p)[-2],cs.player_deck(p)[-1]
            unpick_card(p)
            unpick_card(p)   
    # print(len(textpool))
    # for state in states:
        # print(state)
    return states


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
def collect_states(dbname=dBManager.dbname, limit=1):
    con = sqlite3.connect(f'{dbname}.db')
    cur = con.cursor()

    base_categorized_ids, id_to_categories = generate_card_refs()

    query = "SELECT * FROM battles"
    if limit:
        query += f" LIMIT {limit}"
    
    cur.execute(query)
    rows = cur.fetchall()

    battles = []
    for row in rows:
        battle = {
            "id": row[0],
            "low_tower_dif": row[1],
            "player_deck": ast.literal_eval(row[2]),
            "opp_deck": ast.literal_eval(row[3])
        }
        battles.append(battle)

    num_cards = len(bg.card_list)

    for battle in battles:
        states = states_from_battle(
            battle,
            copy.deepcopy(base_categorized_ids),
            id_to_categories
        )

        for s in states:
            # --- Encode the state as an input vector using Python lists + array ---
            input_list = s.pool + s.decks[0] + s.decks[1] + [s.draftstep]
            input_arr = array.array('h', input_list)  # 'h' = 16-bit signed integer
            input_blob = input_arr.tobytes()

            # --- Create the target vector (one-hot scaled by score) ---
            target_list = [0.0] * num_cards
            if 0 <= s.nextpick < num_cards:
                target_list[s.nextpick] = float(s.score)
            target_arr = array.array('f', target_list)  # 'f' = 32-bit float
            score_blob = target_arr.tobytes()

            # --- Insert into database ---
            cur.execute(
                "INSERT INTO training (input, score) VALUES (?, ?)",
                (input_blob, score_blob)
            )

    con.commit()
    con.close()
    print("✅ Training data inserted successfully.")

if __name__ == "__main__":
    collect_states()
    # print(generate_card_refs())
    pls = "noerror"