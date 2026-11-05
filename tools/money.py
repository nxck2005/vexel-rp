#!/usr/bin/env python3
"""Draws the tablet's Money app (a Google Pay style wallet): its screens, payment cards, big digits and face item.

    money.py [--jar <minecraft client jar>]

Like the Messages screens (messages.py), each screen is one glyph in a chest menu's title, in the font vexel:money:
U+E200 home (savings card, people, recent payments), U+E201 the payments with one person, U+E202 a list (history,
players nearby). The plugin writes names and amounts after them with messages.py's per-height fonts, plus:
- vexel:money/big<y> (y in BIG_YS): Minecraft's letters twice as big, for amounts,
- vexel:money/card<y> (y in CARD_YS): payment cards, U+E210 yours (purple), U+E211 theirs (grey), U+E212 a request
  to you (grey, with a Pay button). Cards are CARD_W x CARD_H; the thread shows two, one at each height.
Players are shown with vexel:money_face, their head facing forward and as big as a slot. The layout must match
CityLifeCore's money feature. Needs Pillow. Run from the pack root.
"""
import json
import os
import sys
import zipfile

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import badges  # noqa: E402
import messages  # noqa: E402
import phone  # noqa: E402
from idcard import text as flat_text  # noqa: E402
from phone import BORDER, rgb, width  # noqa: E402

PURPLE, GREY_BUTTON, CARD_GREY, CARD_PURPLE, LIGHT, MUTED, LINK = (
    "#664696", "#3A3A3C", "#2C2C2E", "#5B3E8C", "#D9CCF0", "#8E8E93", "#B49AE0")
BIG_YS = (17, 43, 77)
CARD_YS = (40, 74)
CARD_W, CARD_H = 110, 30
PILL = (80, 5, 104, 17)  # the Pay button on a request card, from the card's top left


def chevron(d, x, y, up):
    pts = [(x, y + 4), (x + 4, y), (x + 8, y + 4)] if up else [(x, y), (x + 4, y + 4), (x + 8, y)]
    d.line(pts, fill=rgb(LINK) + (255,), width=2)


def bar_button(img, glyphs, first, last, label, bg):
    """A button on slot row 5 from column first to last."""
    b = BORDER
    left = b + 7 + first * 18 + (0 if first == 0 else 1)
    right = b + 7 + last * 18 + (15 if last < 8 else 16)
    ImageDraw.Draw(img).rounded_rectangle((left, b + 109, right, b + 122), 6, fill=rgb(bg) + (255,))
    phone.text(img, glyphs, (left + right) // 2 - width(glyphs, label) // 2, b + 112, label, "#FFFFFF")


def home(glyphs):
    """Rows 0-1: the savings card (click: history). Row 2: four people (slots 19, 21, 23, 25). Row 4: recent payments
    (click: history). Row 5: Pay number (45-48), Nearby (49-50), Request (51-53)."""
    b = BORDER
    img = messages.base(0)
    x0, y0, x1, y1 = b + 6, b + 4, b + 169, b + 44
    card = Image.new("RGBA", img.size)
    cd = ImageDraw.Draw(card)
    for i in range(x1 - x0 + 1):
        cd.line((x0 + i, y0, x0 + i, y1), fill=phone.fade("#7A56B0", "#3E2A60", i / (x1 - x0)))
    mask = Image.new("L", img.size)
    ImageDraw.Draw(mask).rounded_rectangle((x0, y0, x1, y1), 6, fill=255)
    img.paste(card, (0, 0), mask)
    flat_text(img, glyphs, b + 12, b + 7, "Savings", LIGHT)
    # On slot row 1 (y 36-51), so it is over slots that open History; the card's top line has no slots under it.
    flat_text(img, glyphs, b + 164 - width(glyphs, "History >"), b + 35, "History >", LIGHT)
    flat_text(img, glyphs, b + 8, b + 46, "People", MUTED)
    flat_text(img, glyphs, b + 8, b + 83, "Recent", MUTED)
    flat_text(img, glyphs, b + 168 - width(glyphs, "See all >"), b + 83, "See all >", LINK)
    bar_button(img, glyphs, 0, 3, "Pay number", PURPLE)
    bar_button(img, glyphs, 4, 5, "Nearby", GREY_BUTTON)
    bar_button(img, glyphs, 6, 8, "Request", GREY_BUTTON)
    phone.pocket(img)
    return img


def thread(glyphs):
    """Slot row 0: Back (0-1), the person's head (4), older and newer (7, 8). Row 5: Pay (45-48), Request (49-53)."""
    b = BORDER
    img = messages.base(36)
    d = ImageDraw.Draw(img)
    d.line([(b + 15, b + 20), (b + 11, b + 26), (b + 15, b + 32)], fill=rgb(LINK) + (255,), width=2)
    phone.text(img, glyphs, b + 19, b + 22, "Back", LINK)
    chevron(d, b + 138, b + 24, True)
    chevron(d, b + 156, b + 24, False)
    bar_button(img, glyphs, 0, 3, "Pay", PURPLE)
    bar_button(img, glyphs, 4, 8, "Request", GREY_BUTTON)
    phone.pocket(img)
    return img


def list_screen(glyphs):
    """Five rows on slot rows 0-4 (icon in column 0). Row 5: Back (45-48), page up and down (52, 53)."""
    b = BORDER
    img = messages.base(0)
    d = ImageDraw.Draw(img)
    for row in range(4):
        y = b + 35 + row * 18
        d.line((b + 28, y, b + 175, y), fill=rgb("#1F1F22") + (255,))
    bar_button(img, glyphs, 0, 3, "Back", GREY_BUTTON)
    chevron(d, b + 138, b + 113, True)
    chevron(d, b + 156, b + 113, False)
    phone.pocket(img)
    return img


def card(glyphs, colour, pill):
    img = Image.new("RGBA", (CARD_W, CARD_H))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, CARD_W - 1, CARD_H - 1), 5, fill=rgb(colour) + (255,))
    if pill:
        x0, y0, x1, y1 = PILL
        d.rounded_rectangle(PILL, 4, fill=rgb("#2F8F57") + (255,))
        flat_text(img, glyphs, (x0 + x1) // 2 - width(glyphs, "Pay") // 2 + 1, y0 + 2, "Pay", "#FFFFFF")
    return img


if __name__ == "__main__":
    args = sys.argv[1:]
    jar = args[args.index("--jar") + 1] if "--jar" in args else badges.JAR
    glyphs = badges.load_font(jar)
    with zipfile.ZipFile(jar) as z:
        default = json.loads(z.read("assets/minecraft/font/include/default.json"))["providers"]
    ascii_chars = next(p for p in default if p.get("file") == "minecraft:font/ascii.png")["chars"]
    for folder in ("assets/vexel/textures/font/money", "assets/vexel/font/money", "assets/vexel/items", "assets/vexel/models/item"):
        os.makedirs(folder, exist_ok=True)
    screens = []
    for n, (name, draw) in enumerate((("home", home), ("thread", thread), ("list", list_screen))):
        draw(glyphs).save(f"assets/vexel/textures/font/money/{name}.png")
        screens.append({"type": "bitmap", "file": f"vexel:font/money/{name}.png", "ascent": 21, "height": 238,
                        "chars": [chr(0xE200 + n)]})
    json.dump({"providers": screens}, open("assets/vexel/font/money.json", "w"), indent=2)
    cards = [("card_yours", CARD_PURPLE, False), ("card_theirs", CARD_GREY, False), ("card_request", CARD_GREY, True)]
    for name, colour, pill in cards:
        card(glyphs, colour, pill).save(f"assets/vexel/textures/font/money/{name}.png")
    for y in CARD_YS:
        json.dump({"providers": [{"type": "bitmap", "file": f"vexel:font/money/{name}.png", "ascent": 13 - y,
                                  "height": CARD_H, "chars": [chr(0xE210 + i)]} for i, (name, _, _) in enumerate(cards)]},
                  open(f"assets/vexel/font/money/card{y}.json", "w"), indent=2)
    # The title is drawn at y 6 with its baseline 7 lower, so text with its top at y needs ascent 13 - y.
    for y in BIG_YS:
        json.dump({"providers": [{"type": "space", "advances": {" ": 8}},
                                 {"type": "bitmap", "file": "minecraft:font/ascii.png", "ascent": 13 - y, "height": 16,
                                  "chars": ascii_chars}]}, open(f"assets/vexel/font/money/big{y}.json", "w"))
    # Like idcard.py's photo, at twice the size: 16x16, 18x18 with the hat layer, so it may draw past its slot.
    json.dump({"parent": "minecraft:item/template_skull", "gui_light": "front",
               "display": {"gui": {"rotation": [0, 0, 0], "translation": [0, 8, 0], "scale": [2, 2, 1]}}},
              open("assets/vexel/models/item/money_face.json", "w"), indent=2)
    json.dump({"oversized_in_gui": True, "model": {"type": "minecraft:special", "base": "vexel:item/money_face",
                                                   "model": {"type": "minecraft:player_head"},
                                                   "transformation": {"left_rotation": [1.0, 0.0, 0.0, 0.0],
                                                                      "right_rotation": [0.0, 0.0, 0.0, 1.0],
                                                                      "scale": [1.0, 1.0, 1.0], "translation": [0.5, 0.0, 0.5]}}},
              open("assets/vexel/items/money_face.json", "w"), indent=2)
    print("money screens, cards, big fonts and face item written")
