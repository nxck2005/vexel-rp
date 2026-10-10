#!/usr/bin/env python3
"""Draws the phone: the screen shown over CityLife's 6-row phone menu, and the phone item.

    phone.py [--jar <minecraft client jar>]

The screen is one glyph (U+E200) in the font vexel:phone, as big as the whole chest menu (176x222): a dark desk, a
phone with app tiles and labels, and dark slots for the player's inventory. The plugin puts it in the menu title,
shifted to the menu's top left with the font's space characters, and writes the clock and money over the status bar.
App tiles sit under fixed menu slots, so APPS must match the slots in the plugin's phone.apps config.

Writes assets/vexel/textures/font/phone/screen.png, assets/vexel/font/phone.json, and the phone item
(assets/vexel/items/phone.json, its model and texture). Labels use Minecraft's font from the client jar (see
badges.py). Needs Pillow. Run from the pack root.
"""
import json
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import badges  # noqa: E402

# Label, tile colour and menu slot (row * 9 + column). Rows 0 and 2 get labels; row 4 is the dock.
APPS = [
    ("Garage", "#3A7BD5", 2),
    ("Cars", "#2F8F57", 4),
    ("Eats", "#E2683C", 6),
    ("Wallet", "#C9971C", 20),
    ("Profile", "#6A44A6", 22),
    ("Chat", "#4A4D57", 24),
    ("Help", "#2A86C9", 40),
]
SCREEN = ""
# Space characters: U+E210 + n moves left by 2^n pixels, U+E220 + n moves right by 2^n (n = 0..7).
SPACES = {**{chr(0xE210 + n): -(2 ** n) for n in range(8)}, **{chr(0xE220 + n): 2 ** n for n in range(8)}}
DESK, BEZEL, EDGE = "#1D1F25", "#0D0E12", "#3A3C46"
WALL_TOP, WALL_BOTTOM = "#4B3373", "#191A21"


def rgb(colour):
    return tuple(int(colour[i:i + 2], 16) for i in (1, 3, 5))


def text(img, glyphs, x, y, string, colour):
    """Minecraft text with its drop shadow."""
    for offset, col in ((1, tuple(v // 4 for v in rgb(colour))), (0, rgb(colour))):
        cx = x
        for ch in string:
            if ch == " ":
                cx += 4
                continue
            glyph, width = glyphs[ch]
            tinted = Image.new("RGBA", glyph.size, col + (255,))
            tinted.putalpha(glyph)
            img.alpha_composite(tinted, (cx + offset, y + offset))
            cx += width + 1


def width(glyphs, string):
    return sum(4 if ch == " " else glyphs[ch][1] + 1 for ch in string) - 1


def slot_xy(slot):
    """Top left of a chest slot's item area."""
    return 8 + slot % 9 * 18, 18 + slot // 9 * 18


def screen(glyphs):
    img = Image.new("RGBA", (176, 222))
    d = ImageDraw.Draw(img)
    # The right edge column must be opaque: the game measures a glyph's width up to its last opaque column.
    d.rounded_rectangle((0, 0, 175, 221), 4, fill=rgb(DESK) + (255,), outline=rgb("#33353F") + (255,))
    d.rectangle((175, 4, 175, 217), fill=rgb("#33353F") + (255,))

    # Phone body, then a wallpaper fading from brand purple into dark.
    d.rounded_rectangle((28, 1, 148, 121), 9, fill=rgb(BEZEL) + (255,), outline=rgb(EDGE) + (255,))
    wall = Image.new("RGBA", (113, 113))
    wd = ImageDraw.Draw(wall)
    for y in range(wall.height):
        f = y / (wall.height - 1)
        wd.line((0, y, wall.width - 1, y), fill=tuple(round(a + (b - a) * f) for a, b in zip(rgb(WALL_TOP), rgb(WALL_BOTTOM))) + (255,))
    mask = Image.new("L", wall.size)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, wall.width - 1, wall.height - 1), 6, fill=255)
    img.paste(wall, (32, 4), mask)

    # Dock behind the last row of apps.
    dock = Image.new("RGBA", img.size)
    ImageDraw.Draw(dock).rounded_rectangle((36, 86, 140, 109), 6, fill=(255, 255, 255, 22), outline=rgb("#5A4A7A") + (255,))
    img.alpha_composite(dock)

    for label, colour, slot in APPS:
        x, y = slot_xy(slot)
        tile = rgb(colour)
        d.rounded_rectangle((x - 2, y - 2, x + 17, y + 17), 4, fill=tile + (255,))
        d.line((x, y - 2, x + 15, y - 2), fill=tuple(min(255, v + 50) for v in tile) + (255,))
        if slot < 36:
            text(img, glyphs, x + 8 - width(glyphs, label) // 2, y + 20, label, "#E6E6E6")

    # Dark slots for the player's inventory (three rows, then the hotbar).
    for row in range(4):
        for column in range(9):
            x, y = 8 + column * 18, 139 + row * 18 + (4 if row == 3 else 0)
            d.rectangle((x - 1, y - 1, x + 16, y + 16), fill=rgb("#141519") + (255,))
            d.rectangle((x, y, x + 15, y + 15), fill=rgb("#282931") + (255,))
    return img


def phone_item():
    img = Image.new("RGBA", (16, 16))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((4, 1, 11, 14), 2, fill=rgb("#16171C") + (255,), outline=rgb(EDGE) + (255,))
    d.rectangle((5, 3, 10, 11), fill=rgb("#664696") + (255,))
    d.rectangle((5, 3, 10, 5), fill=rgb("#8B6BC4") + (255,))
    d.line((7, 13, 8, 13), fill=rgb("#A9A7A9") + (255,))
    return img


def main():
    args = sys.argv[1:]
    glyphs = badges.load_font(args[args.index("--jar") + 1] if "--jar" in args else badges.JAR)
    for folder in ("assets/vexel/textures/font/phone", "assets/vexel/font", "assets/vexel/textures/item",
                   "assets/vexel/models/item", "assets/vexel/items"):
        os.makedirs(folder, exist_ok=True)
    screen(glyphs).save("assets/vexel/textures/font/phone/screen.png")
    # Ascent 13 puts the glyph's top at the menu's top edge (the title is drawn 6 pixels down, baseline 7 below that).
    font = {"providers": [
        {"type": "bitmap", "file": "vexel:font/phone/screen.png", "ascent": 13, "height": 222, "chars": [SCREEN]},
        {"type": "space", "advances": SPACES},
    ]}
    json.dump(font, open("assets/vexel/font/phone.json", "w"), indent=2)
    phone_item().save("assets/vexel/textures/item/phone.png")
    json.dump({"parent": "minecraft:item/generated", "textures": {"layer0": "vexel:item/phone"}},
              open("assets/vexel/models/item/phone.json", "w"), indent=2)
    json.dump({"model": {"type": "minecraft:model", "model": "vexel:item/phone"}},
              open("assets/vexel/items/phone.json", "w"), indent=2)
    print("phone screen and item written")


if __name__ == "__main__":
    main()
