"""Writes ui_art_1.json: Z-Image Turbo jobs for the UI art (backgrounds, cards, ornaments, icons, how-to art, textures)."""
import json, os
STYLE = ("1930s Art Deco gouache illustration, painterly, elegant, black lacquer, gold leaf, ivory, deep emerald green and burgundy accents, "
         "no text, no lettering, no words, no letters, no watermark, no signature")
ICON = ("a single flat gold Art Deco emblem icon of {x}, bold simple geometric shapes, engraved polished gold leaf with fine bevels, "
        "perfectly centered, symmetrical where possible, isolated on a pure flat black background, large margin around it, "
        "vector-like clean edges, no text, no lettering, no frame, no shadow")
J = [
 {"name": "bg_ballroom", "seed": 201, "w": 1920, "h": 1088, "prompt":
  "Wide cinematic view of a grand Art Deco ballroom in an English manor at night during a masquerade ball, elegant masked couples dancing in the middle distance "
  "as soft silhouettes, three glittering crystal chandeliers, tall black marble columns with gold capitals, gold geometric sunburst motifs on the walls, "
  "a polished parquet floor reflecting warm candle light, the whole left third of the picture is a calm dark shadowy area of black marble wall, "
  "deep rich shadows, mysterious, moody, warm gold light against black. " + STYLE},
 {"name": "bg_ballroom_wide", "seed": 202, "w": 2304, "h": 1024, "prompt":
  "Ultra wide cinematic panorama of an Art Deco ballroom in an English manor at night during a masquerade ball, masked dancers in evening dress as soft "
  "silhouettes far away in the center right, crystal chandeliers, black marble and gold columns, tall arched windows with rain and moonlight, "
  "the left side of the picture is dark and empty, deep shadows, moody warm gold light. " + STYLE},
 {"name": "fg_drapes", "seed": 203, "w": 1920, "h": 1088, "prompt":
  "Heavy deep burgundy red velvet theatre curtains drawn open, hanging only along the far left edge and the far right edge of the frame, "
  "with thick gold rope tie-backs, gold tassels and a gold fringe, rich folds, front view, the entire middle of the image is an empty solid flat "
  "bright chroma key green background (#00FF00), studio lighting, no stage, no floor, no people, no text"},
 {"name": "art_arrival", "seed": 204, "w": 1920, "h": 1088, "prompt":
  "A black 1930s Rolls-Royce limousine arriving at the illuminated stone entrance of a grand English country manor at night in the rain, "
  "a chauffeur holding a black umbrella, masked guests in evening dress climbing the steps, warm golden light pouring from the open doors and windows, "
  "wet gravel reflecting the light, cold blue moonlight, mysterious. " + STYLE},
 {"name": "card_invite", "seed": 205, "w": 832, "h": 1248, "prompt":
  "An ornate Art Deco tarot card, full card visible, front view, flat: a symmetrical gold leaf border with geometric sunburst corners and stepped lines on black lacquer, "
  "in the center an elegant 1930s lady in a black evening gown holding a gold Venetian masquerade mask on a stick in front of her face, "
  "a gold sunburst halo behind her, emerald green accents, an empty plain black plaque at the bottom of the card with nothing written on it. " + STYLE},
 {"name": "card_detective", "seed": 206, "w": 832, "h": 1248, "prompt":
  "An ornate Art Deco tarot card, full card visible, front view, flat: a symmetrical gold leaf border with geometric sunburst corners and stepped lines on black lacquer, "
  "in the center a mysterious 1930s detective in a tan trench coat and a dark fedora hat, face in shadow, holding a revolver pointed up and a brass magnifying glass, "
  "a gold sunburst halo behind him, burgundy accents, an empty plain black plaque at the bottom of the card with nothing written on it. " + STYLE},
 {"name": "orn_corner", "seed": 207, "w": 1024, "h": 1024, "prompt":
  "A single Art Deco gold corner ornament for the top left corner of a picture frame: two thin parallel gold lines running along the top edge and the left edge, "
  "meeting in a stepped geometric corner with a small gold sunburst fan and a diamond, polished gold leaf, flat front view, isolated on a pure flat black background, "
  "no text, no other objects"},
 {"name": "orn_divider", "seed": 208, "w": 1536, "h": 512, "prompt":
  "A horizontal symmetrical Art Deco gold divider ornament: thin double gold lines extending left and right from a central gold diamond with a small sunburst fan "
  "and stepped chevrons, polished gold leaf, flat front view, isolated on a pure flat black background, no text"},
 {"name": "orn_sunburst", "seed": 209, "w": 1536, "h": 768, "prompt":
  "A large Art Deco gold sunburst: a half circle fan of straight radiating gold rays of alternating lengths rising from the bottom center, with concentric stepped arcs, "
  "polished gold leaf, flat front view, isolated on a pure flat black background, no text"},
 {"name": "ico_mask", "seed": 210, "w": 1024, "h": 1024, "prompt": ICON.format(x="a Venetian masquerade eye mask")},
 {"name": "ico_magnifier", "seed": 211, "w": 1024, "h": 1024, "prompt": ICON.format(x="a detective magnifying glass, tilted")},
 {"name": "ico_revolver", "seed": 212, "w": 1024, "h": 1024, "prompt": ICON.format(x="a 1930s revolver seen from the side, pointing left")},
 {"name": "ico_ghost", "seed": 213, "w": 1024, "h": 1024, "prompt": ICON.format(x="a friendly ghost wearing a masquerade eye mask")},
 {"name": "ico_clock", "seed": 214, "w": 1024, "h": 1024, "prompt": ICON.format(x="a round pocket watch clock face with hands and twelve tick marks, no numbers")},
 {"name": "ico_heart", "seed": 215, "w": 1024, "h": 1024, "prompt": ICON.format(x="a heart")},
 {"name": "ico_players", "seed": 216, "w": 1024, "h": 1024, "prompt": ICON.format(x="three masked guests heads in a row, simple silhouettes")},
 {"name": "ico_gear", "seed": 217, "w": 1024, "h": 1024, "prompt": ICON.format(x="a gear cog")},
 {"name": "ico_book", "seed": 218, "w": 1024, "h": 1024, "prompt": ICON.format(x="an open book")},
 {"name": "ico_door", "seed": 219, "w": 1024, "h": 1024, "prompt": ICON.format(x="an open door with an arch")},
 {"name": "howto_blend", "seed": 220, "w": 1216, "h": 832, "prompt":
  "A crowd of elegant masked guests in black tie and evening gowns at a 1930s masquerade ball, all wearing identical gold masks, one gentleman in the middle "
  "subtly glancing sideways with suspicious eyes, Art Deco ballroom background. " + STYLE},
 {"name": "howto_hunt", "seed": 221, "w": 1216, "h": 832, "prompt":
  "A 1930s detective in a tan trench coat and fedora, seen from behind over his shoulder, holding a revolver low, scanning a crowd of masked guests "
  "in an Art Deco ballroom, a beam of light on him, tense atmosphere. " + STYLE},
 {"name": "howto_penalty", "seed": 222, "w": 1216, "h": 832, "prompt":
  "Still life: a cracked gold Venetian masquerade mask lying on a black and white marble floor next to a toppled champagne glass and spilled champagne, "
  "a single red rose, dramatic light from above, dark background. " + STYLE},
 {"name": "howto_ghost", "seed": 223, "w": 1216, "h": 832, "prompt":
  "A translucent pale blue ghost of a masked gentleman in a tuxedo floating above the dance floor of an Art Deco ballroom, glowing softly, "
  "the dancers below unaware of him, eerie but elegant. " + STYLE},
 {"name": "tex_paper", "seed": 224, "w": 1024, "h": 1024, "prompt":
  "Flat scan of a blank sheet of thick ivory cotton paper, subtle fibers and very faint warm mottling, evenly lit, completely blank, no text, no marks, no border"},
 {"name": "tex_newsprint", "seed": 225, "w": 1024, "h": 1024, "prompt":
  "Flat scan of a blank sheet of old yellowed newsprint paper from the 1930s, subtle stains and fibers, evenly lit, completely blank, no text, no print, no border"},
 {"name": "tex_lacquer", "seed": 226, "w": 1024, "h": 1024, "prompt":
  "Flat close-up texture of a black lacquer panel with a very subtle deep emerald sheen and tiny scattered gold leaf flecks, evenly lit, no objects, no text"},
 {"name": "photo_detectives", "seed": 227, "w": 1216, "h": 832, "prompt":
  "1930s black and white press photograph, flash photography, three detectives in trench coats and fedoras standing proudly in the grand hall of an English manor "
  "after a masquerade ball, one holding a revolver, masked guests staring in the background, grainy film, high contrast, no text"},
 {"name": "photo_guests", "seed": 228, "w": 1216, "h": 832, "prompt":
  "1930s black and white press photograph, flash photography, elegant masked guests in evening dress laughing and raising champagne glasses in a grand Art Deco "
  "ballroom, a confused detective in a fedora in the corner, grainy film, high contrast, no text"},
]
json.dump(J, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui_art_1.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(len(J))
