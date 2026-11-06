"""Writes logo_ideo.json (Ideogram v4 structured captions) and logo_z.json (Z-Image fallback) for the title logo."""
import json, os
D = os.path.dirname(os.path.abspath(__file__))
STYLE = {
    "aesthetics": "Luxurious 1930s Art Deco title lettering, geometric high-contrast display letterforms with thin hairlines and thick stems, "
                  "inline engraved detail, perfectly symmetrical composition, cinematic film title card",
    "lighting": "soft warm studio light glinting on polished metal, subtle bevel highlights",
    "medium": "graphic design logo, gold leaf lettering",
    "color_palette": ["#000000", "#D4A84A", "#F6DE96", "#8A6420"],
}
BG = "Pure flat solid black background, completely empty, no texture, no pattern, nothing else."


def cap(desc, elements):
    return {"high_level_description": desc, "style_description": STYLE,
            "compositional_deconstruction": {"background": BG, "elements": elements}}


MASK = {"type": "obj", "bbox": [90, 400, 330, 600],
        "desc": "Gold Art Deco Venetian masquerade eye mask emblem with a small fan of geometric sunburst rays rising behind it, polished gold leaf, symmetrical.",
        "color_palette": ["#D4A84A", "#F6DE96", "#8A6420"]}
RULE = {"type": "obj", "bbox": [760, 300, 790, 700], "desc": "Thin horizontal gold Art Deco divider line with a small central diamond.",
        "color_palette": ["#D4A84A"]}
ideo = [
    {"name": "logo_ideo", "seed": 401, "w": 1536, "h": 768, "prompt": cap(
        "An elegant Art Deco film title logo reading 'Le Bal Masqué' in gold leaf lettering under a gold Venetian mask emblem, on a pure black background.",
        [MASK, {"type": "text", "bbox": [380, 90, 700, 910], "text": "Le Bal Masqué",
                "desc": "Large elegant Art Deco display title in polished gold leaf, one line, capital L, B and M with lowercase letters, "
                        "the final letter is an e with an acute accent (é), clearly drawn.", "color_palette": ["#D4A84A", "#F6DE96"]}, RULE])},
    {"name": "logo_ideo", "seed": 402, "w": 1536, "h": 768, "prompt": cap(
        "An elegant Art Deco film title logo reading 'LE BAL MASQUÉ' in gold leaf capital letters under a gold Venetian mask emblem, on a pure black background.",
        [MASK, {"type": "text", "bbox": [390, 70, 690, 930], "text": "LE BAL MASQUÉ",
                "desc": "Large Art Deco display title in polished gold leaf capital letters with wide letter spacing, one line, "
                        "the last letter is a capital E with an acute accent (É), clearly drawn.", "color_palette": ["#D4A84A", "#F6DE96"]}, RULE])},
    {"name": "logo_ideo", "seed": 403, "w": 1536, "h": 768, "prompt": cap(
        "An elegant Art Deco film title logo reading 'LE BAL MASQUÉ' in gold leaf capital letters under a gold Venetian mask emblem, on a pure black background.",
        [MASK, {"type": "text", "bbox": [390, 70, 690, 930], "text": "LE BAL MASQUÉ",
                "desc": "Large Art Deco display title in polished gold leaf capital letters with wide letter spacing, one line, "
                        "the last letter is a capital E with an acute accent (É), clearly drawn.", "color_palette": ["#D4A84A", "#F6DE96"]}, RULE])},
    {"name": "logo_ideo", "seed": 404, "w": 1536, "h": 768, "prompt": cap(
        "An elegant Art Deco film title logo reading 'Le Bal Masqué' in gold leaf lettering under a gold Venetian mask emblem, on a pure black background.",
        [MASK, {"type": "text", "bbox": [380, 90, 700, 910], "text": "Le Bal Masqué",
                "desc": "Large elegant Art Deco display title in polished gold leaf, one line, capital L, B and M with lowercase letters, "
                        "the final letter is an e with an acute accent (é), clearly drawn.", "color_palette": ["#D4A84A", "#F6DE96"]}, RULE])},
]
json.dump(ideo, open(os.path.join(D, "logo_ideo.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
Z = ("Elegant 1930s Art Deco film title logo: the words \"LE BAL MASQUÉ\" in large polished gold leaf Art Deco capital letters on one line, "
     "with an acute accent on the final É, a small gold Venetian masquerade mask emblem with sunburst rays centered above the words, "
     "a thin gold divider line with a diamond below, pure flat black background, centered, symmetrical, luxurious typography, no other text")
z = [{"name": "logo_z", "seed": s, "w": 1536, "h": 768, "prompt": Z} for s in (411, 412, 413)]
json.dump(z, open(os.path.join(D, "logo_z.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("ok")
