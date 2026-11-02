#!/usr/bin/env python3
"""Draws the tablet's Profile app: the player's ID card.

    idcard.py [--jar <minecraft client jar>]

Like the Messages screens (messages.py), each screen is one glyph in a chest menu's title, in the font vexel:idcard:
U+E200 your own card and U+E201 someone else's, light; U+E202 and U+E203 the same, dark. The screens hold everything
that never changes (the card, labels, the licence row, the buttons); the plugin writes the name and values after them
with messages.py's per-height fonts, and the rank badge with vexel:idcard/badge (badges.py's badges moved down to
BADGE_Y, under the name). The photo is the player's own head, an item in slot 10 drawn 4 times bigger and facing forward by the item
model vexel:id_photo. The layout must match CityLifeCore's idcard feature. Needs Pillow. Run from the pack root.
"""
import json
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import badges  # noqa: E402
import phone  # noqa: E402
from phone import BORDER, rgb, width  # noqa: E402

THEMES = {
    "light": dict(card="#EEEAF3", ink="#1D1F25", muted="#76717F", line="#D6D0DE", photo="#B9C7D8", pill="#C9C3D1"),
    "dark": dict(card="#24252D", ink="#FFFFFF", muted="#A9A7A9", line="#34363F", photo="#3A3C46", pill="#3A3C46"),
}
CARD = (6, 6, 169, 107)  # menu pixels; the screen image is BORDER more on each side
PHOTO = (15, 25, 52, 62)  # around slot 10's head: 32x32, 36x36 with the hat layer, centred on the slot
LABELS_X, FIELDS_Y, FIELD_STEP = 56, 45, 9
BADGE_Y = 34  # under the name; badges are up to 57 wide, too wide for under the photo
# Slot row 5: (first column, last column, label, background, text colour)
OWN_BUTTONS = [(0, 3, "Show nearby", "#664696", "#FFFFFF"), (4, 6, None, "#3A3A3C", "#FFFFFF"), (7, 8, "Close", "#3A3A3C", "#A9A7A9")]
OTHER_BUTTONS = [(0, 2, "Text", "#0A84FF", "#FFFFFF"), (3, 6, "Save contact", "#3A3A3C", "#FFFFFF"), (7, 8, "Close", "#3A3A3C", "#A9A7A9")]


def text(img, glyphs, x, y, string, colour):
    """Minecraft text without a shadow, like menu titles."""
    cx = x
    for ch in string:
        if ch == " ":
            cx += 4
            continue
        glyph, w = glyphs[ch]
        tinted = Image.new("RGBA", glyph.size, rgb(colour) + (255,))
        tinted.putalpha(glyph)
        img.alpha_composite(tinted, (cx, y))
        cx += w + 1


def pill(img, glyphs, x, y, label, bg, fg):
    w = width(glyphs, label)
    ImageDraw.Draw(img).rounded_rectangle((x, y, x + w + 5, y + 10), 3, fill=rgb(bg) + (255,))
    text(img, glyphs, x + 3, y + 2, label, fg)
    return w + 6


def screen(glyphs, theme, own):
    t = THEMES[theme]
    b = BORDER
    img = phone.bezel()
    wall = Image.new("RGBA", (176, 222))
    wd = ImageDraw.Draw(wall)
    for y in range(222):  # all of it: see-through pixels would show the chest menu's own background
        wd.line((0, y, 175, y), fill=phone.fade("#2A2140", "#121318", min(1, y / 123)))
    mask = Image.new("L", wall.size)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, 175, 221), 6, fill=255)
    img.paste(wall, (b, b), mask)

    x0, y0, x1, y1 = (v + b for v in CARD)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((x0 - 1, y0 - 1, x1 + 1, y1 + 1), 6, fill=(0, 0, 0, 120))
    card = Image.new("RGBA", img.size)
    cd = ImageDraw.Draw(card)
    cd.rectangle((x0, y0, x1, y1), fill=rgb(t["card"]) + (255,))
    stripes = Image.new("RGBA", img.size)
    sd = ImageDraw.Draw(stripes)
    for k in range(-120, 200, 9):
        sd.line((x0 + k, y1, x0 + k + 100, y0), fill=rgb("#664696") + ((22 if theme == "light" else 30),))
    card.alpha_composite(stripes)
    for y in range(y0, y0 + 15):
        cd.line((x0, y, x1, y), fill=phone.fade("#7A56B0", "#553A80", (y - y0) / 14))
    mask = Image.new("L", img.size)
    ImageDraw.Draw(mask).rounded_rectangle((x0, y0, x1, y1), 5, fill=255)
    img.paste(card, (0, 0), mask)
    d = ImageDraw.Draw(img)
    text(img, glyphs, x0 + 5, y0 + 4, "CITYLIFE ID", "#FFFFFF")

    px0, py0, px1, py1 = (v + b for v in PHOTO)
    d.rectangle((px0, py0, px1, py1), fill=rgb(t["line"]) + (255,))
    d.rectangle((px0 + 1, py0 + 1, px1 - 1, py1 - 1), fill=rgb(t["photo"]) + (255,))

    for i, label in enumerate(("Job", "School", "Phone", "Since", "Played")):
        text(img, glyphs, LABELS_X + b, FIELDS_Y + i * FIELD_STEP + b, label, t["muted"])

    d.line((x0 + 5, 90 + b, x1 - 5, 90 + b), fill=rgb(t["line"]) + (255,))
    x = x0 + 5
    for name in ("Car", "Boat", "Plane"):
        x += pill(img, glyphs, x, 93 + b, name, t["pill"], t["muted"]) + 2
    text(img, glyphs, x + 2, 95 + b, "Coming soon!", t["muted"])

    other_theme = "Light" if theme == "dark" else "Dark"
    for first, last, label, bg, fg in OWN_BUTTONS if own else OTHER_BUTTONS:
        left, right = b + 7 + first * 18 + (0 if first == 0 else 1), b + 7 + last * 18 + (15 if last < 8 else 16)
        label = label or other_theme + " card"
        d.rounded_rectangle((left, b + 109, right, b + 122), 6, fill=rgb(bg) + (255,))
        phone.text(img, glyphs, (left + right) // 2 - width(glyphs, label) // 2, b + 112, label, fg)

    phone.pocket(img)
    return img


if __name__ == "__main__":
    args = sys.argv[1:]
    jar = args[args.index("--jar") + 1] if "--jar" in args else badges.JAR
    glyphs = badges.load_font(jar)
    for folder in ("assets/vexel/textures/font/idcard", "assets/vexel/font/idcard", "assets/vexel/items", "assets/vexel/models/item"):
        os.makedirs(folder, exist_ok=True)
    providers = []
    for n, (theme, own) in enumerate((("light", True), ("light", False), ("dark", True), ("dark", False))):
        name = f"{theme}_{'own' if own else 'other'}"
        screen(glyphs, theme, own).save(f"assets/vexel/textures/font/idcard/{name}.png")
        providers.append({"type": "bitmap", "file": f"vexel:font/idcard/{name}.png", "ascent": 21, "height": 238,
                          "chars": [chr(0xE200 + n)]})
    json.dump({"providers": providers}, open("assets/vexel/font/idcard.json", "w"), indent=2)
    json.dump({"providers": [{"type": "bitmap", "file": f"vexel:font/badge/{badge_id}.png", "ascent": 13 - BADGE_Y,
                              "height": badges.HEIGHT, "chars": [char]} for badge_id, _, char, *_ in badges.BADGES]},
              open("assets/vexel/font/idcard/badge.json", "w"), indent=2)
    # The head faces forward (gui rotation 0 shows its face), 4 times bigger: 32x32 pixels. It's 8 tall from
    # the bottom of the block, so it moves up by its half height times the scale to stay centred on the slot.
    json.dump({"parent": "minecraft:item/template_skull", "gui_light": "front",
               "display": {"gui": {"rotation": [0, 0, 0], "translation": [0, 16, 0], "scale": [4, 4, 1]}}},
              open("assets/vexel/models/item/id_photo.json", "w"), indent=2)
    # oversized_in_gui: since 1.21.6 the game cuts item drawings to their slot unless this is set.
    json.dump({"oversized_in_gui": True, "model": {"type": "minecraft:special", "base": "vexel:item/id_photo", "model": {"type": "minecraft:player_head"},
                         "transformation": {"left_rotation": [1.0, 0.0, 0.0, 0.0], "right_rotation": [0.0, 0.0, 0.0, 1.0],
                                            "scale": [1.0, 1.0, 1.0], "translation": [0.5, 0.0, 0.5]}}},
              open("assets/vexel/items/id_photo.json", "w"), indent=2)
    print("id card screens, badge font and photo item written")
