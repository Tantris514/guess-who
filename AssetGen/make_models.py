"""Build the 3D batch (priority order) from selections.json.

  python -I -X utf8 make_models.py OUT.json [--upsample 1024] [--seed 42] [--only a,b] [--skip a,b]
"""
import argparse
import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))

# name: (target faces, texture size). Order = generation priority.
PLAN = [
    # most visible in the rooms first (coordinator, 23:30)
    ("billiard_table", 120000, 2048), ("table_dining", 100000, 2048), ("chair_dining", 50000, 2048),
    ("sofa_chesterfield", 120000, 2048), ("vase_flowers", 100000, 2048), ("palm_potted", 150000, 2048),
    ("chair_wicker", 80000, 2048), ("chair_wingback", 80000, 2048), ("table_console", 60000, 2048),
    ("lamp_floor", 50000, 2048), ("lamp_table", 40000, 1024), ("sconce_wall", 30000, 1024),
    ("table_side", 50000, 2048), ("sideboard", 80000, 2048), ("desk_partners", 100000, 2048),
    ("clock_grandfather", 80000, 2048), ("globe_floor", 80000, 2048), ("bar_cart", 80000, 2048),
    ("bust_marble", 80000, 2048), ("armor_suit", 120000, 2048), ("ottoman", 40000, 2048),
    ("champagne_table", 60000, 2048), ("harp", 100000, 2048), ("stag_head", 80000, 2048),
    # small items
    ("gramophone", 60000, 1024), ("candelabra", 50000, 1024), ("radio_cathedral", 40000, 1024),
    ("telephone", 40000, 1024), ("typewriter", 60000, 1024), ("umbrella_stand", 40000, 1024),
    # 20 new props (2026-11-02, "map too empty")
    ("bench", 60000, 2048), ("safe", 60000, 2048), ("coat_rack", 60000, 2048), ("trunk_steamer", 60000, 2048),
    ("curio_cabinet", 100000, 2048), ("screen_folding", 60000, 2048), ("statue_dancer", 80000, 2048),
    ("fern_stand", 120000, 2048), ("birdcage", 80000, 2048), ("card_table", 60000, 2048), ("chaise_longue", 80000, 2048),
    ("champagne_bucket", 50000, 2048), ("fire_screen", 50000, 2048), ("microphone_stand", 40000, 1024),
    ("vase_floor", 50000, 2048), ("dress_form", 80000, 2048), ("drum_kit", 100000, 2048), ("writing_bureau", 80000, 2048),
    ("film_projector", 60000, 2048), ("double_bass", 60000, 2048),
    # 9 game items (coordinator, 2026-11-02 20:50; kind character_item like the revolver)
    ("sword_knight", 30000, 1024), ("rifle_1930s", 40000, 1024), ("smoke_grenade", 20000, 1024),
    ("gas_canister", 20000, 1024), ("door_trap", 30000, 1024), ("time_bomb", 40000, 1024), ("turret_mg", 60000, 2048),
    ("swap_pistol", 40000, 1024), ("billiard_ball", 10000, 1024),
    # added serving_tray, toilet_hightank, washbasin, cue_rack, bar_stool, liquor_set, cigar_box, chess_table, harp_stool, wine_barrel, candelabra_floor, candelabra_gold, ship_bottle, globe_bar
    ("serving_tray", 20000, 1024), ("toilet_hightank", 60000, 2048), ("washbasin", 40000, 2048), ("cue_rack", 60000, 2048),
    ("bar_stool", 40000, 2048), ("liquor_set", 60000, 1024), ("cigar_box", 40000, 1024), ("chess_table", 80000, 2048),
    ("harp_stool", 30000, 1024), ("wine_barrel", 50000, 2048), ("candelabra_floor", 50000, 2048), ("candelabra_gold", 40000, 1024),
    ("ship_bottle", 50000, 1024), ("globe_bar", 80000, 2048),
    # added tea_trolley, lectern_book, radiator, log_basket, fountain_indoor, orange_tree, garden_bench, suitcase_stack, roulette_table, lion_statue, buffet_table, telescope, heraldic_shield, coal_scuttle, mantel_clock, desk_chair
    ("tea_trolley", 60000, 2048), ("lectern_book", 60000, 2048), ("radiator", 40000, 2048), ("log_basket", 60000, 2048),
    ("fountain_indoor", 80000, 2048), ("orange_tree", 120000, 2048), ("garden_bench", 60000, 2048), ("suitcase_stack", 50000, 2048),
    ("roulette_table", 100000, 2048), ("lion_statue", 80000, 2048), ("buffet_table", 120000, 2048), ("telescope", 40000, 2048),
    ("heraldic_shield", 50000, 2048), ("coal_scuttle", 30000, 1024), ("mantel_clock", 30000, 1024), ("desk_chair", 50000, 2048),
    # added bar_counter, fire_alarm, sticky_note, music_stand_band, chair_ballroom
    ("bar_counter", 100000, 2048), ("fire_alarm", 20000, 1024), ("sticky_note", 5000, 1024), ("music_stand_band", 40000, 2048),
    ("chair_ballroom", 50000, 2048),
    # added 2026-11-05 (game items)
    ("rifle_old", 40000, 1024), ("hidden_blade", 30000, 1024), ("mystery_box", 60000, 2048), ("breaker_box", 40000, 2048),
    # already done (kept for re-runs)
    ("chandelier", 150000, 2048), ("bookcase", 120000, 2048), ("piano_grand", 120000, 2048), ("fireplace", 120000, 2048),
]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("out")
    p.add_argument("--upsample", type=int, default=1024)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--only", default="")
    p.add_argument("--skip", default="")
    a = p.parse_args()
    sel = json.load(open(os.path.join(ROOT, "selections.json"), encoding="utf-8"))
    only = set(filter(None, a.only.split(",")))
    skip = set(filter(None, a.skip.split(",")))
    jobs = []
    for name, faces, tex in PLAN:
        if (only and name not in only) or name in skip:
            continue
        jobs.append({"kind": "model", "name": name, "image": os.path.join(ROOT, sel[name]), "seed": a.seed,
                     "tex": tex, "faces": faces, "upsample": a.upsample})
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=1)
    print(len(jobs), "jobs ->", a.out)


if __name__ == "__main__":
    main()
