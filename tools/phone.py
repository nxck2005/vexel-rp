#!/usr/bin/env python3
"""Draws CityLife's tablet: the screen shown over the 6-row phone menu, and the tablet item.

    phone.py [--jar <minecraft client jar>]

The screen is one glyph in the font vexel:phone: a tablet 8 pixels bigger than the chest menu (176x222) on every
side, so the menu's own background is hidden. Its top holds the app tiles and labels; its bottom is a pocket panel
behind the player's inventory, with a light header because the game always writes "Inventory" there in dark grey.
U+E200 is the normal screen and U+E201 the staff one, which adds the staff tile. The plugin puts the glyph in the
menu title, shifted with the font's space characters, and writes the clock and money over the status bar. App tiles
sit under fixed menu slots, so APPS must match the slots in the plugin's phone.apps config.

Writes assets/vexel/textures/font/phone/screen.png and screen_staff.png, assets/vexel/font/phone.json, and the
tablet item (assets/vexel/items/phone.json, its model and texture). Labels use Minecraft's font from the client jar
(see badges.py). Needs Pillow. Run from the pack root.
"""
import json
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import badges  # noqa: E402

# Label, tile colour and menu slot (row * 9 + column), in labelled rows of four.
APPS = [
    ("Garage", "#3A7BD5", 1),
    ("Cars", "#2F8F57", 3),
    ("Eats", "#E2683C", 5),
    ("Wallet", "#C9971C", 7),
    ("Profile", "#6A44A6", 19),
    ("Chat", "#4A4D57", 21),
    ("Help", "#2A86C9", 23),
    ("Transit", "#1F9E9A", 37),
    ("Jobs", "#8A5A2B", 39),
]
STAFF_APPS = [("Ranks", "#CC3B2E", 25)]
SCREEN, STAFF_SCREEN = "\ue200", "\ue201"
BORDER = 8  # how far the tablet reaches past the menu on each side
# Space characters: U+E210 + n moves left by 2^n pixels, U+E220 + n moves right by 2^n (n = 0..7).
SPACES = {**{chr(0xE210 + n): -(2 ** n) for n in range(8)}, **{chr(0xE220 + n): 2 ** n for n in range(8)}}
BEZEL, EDGE, SILVER = "#0D0E12", "#3A3C46", "#A9A7A9"
WALL_TOP, WALL_BOTTOM = "#4B3373", "#191A21"


def rgb(colour):
    return tuple(int(colour[i:i + 2], 16) for i in (1, 3, 5))


def fade(a, b, f):
    return tuple(round(p + (q - p) * f) for p, q in zip(rgb(a), rgb(b))) + (255,)


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
    """Top left of a chest slot's item area, in screen image pixels."""
    return BORDER + 8 + slot % 9 * 18, BORDER + 18 + slot // 9 * 18


def screen(glyphs, apps):
    b = BORDER
    img = Image.new("RGBA", (176 + 2 * b, 222 + 2 * b))
    d = ImageDraw.Draw(img)
    # Bezel. Its right edge must be opaque: the game measures a glyph's width up to its last opaque column.
    d.rounded_rectangle((0, 0, img.width - 1, img.height - 1), 13, fill=rgb(BEZEL) + (255,), outline=rgb(EDGE) + (255,))
    d.ellipse((b + 86, 2, b + 89, 5), fill=rgb("#23252E") + (255,))  # camera

    # Screen: exactly the menu's area, a wallpaper fading from brand purple into dark.
    wall = Image.new("RGBA", (176, 222))
    wd = ImageDraw.Draw(wall)
    for y in range(wall.height):
        wd.line((0, y, wall.width - 1, y), fill=fade(WALL_TOP, WALL_BOTTOM, min(1, y / 170)))
    mask = Image.new("L", wall.size)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, wall.width - 1, wall.height - 1), 6, fill=255)
    img.paste(wall, (b, b), mask)

    for label, colour, slot in apps:
        x, y = slot_xy(slot)
        tile = rgb(colour)
        d.rounded_rectangle((x - 2, y - 2, x + 17, y + 17), 4, fill=tile + (255,))
        d.line((x, y - 2, x + 15, y - 2), fill=tuple(min(255, v + 50) for v in tile) + (255,))
        text(img, glyphs, x + 8 - width(glyphs, label) // 2, y + 20, label, "#E6E6E6")

    # Pocket panel behind the player's inventory; the game writes "Inventory" at (8, 128) in dark grey, on the header.
    panel = Image.new("RGBA", img.size)
    pd = ImageDraw.Draw(panel)
    pd.rounded_rectangle((b + 2, b + 124, b + 173, b + 219), 5, fill=(14, 15, 19, 235))
    pd.rounded_rectangle((b + 2, b + 124, b + 173, b + 137), 5, fill=rgb(SILVER) + (255,))
    pd.rectangle((b + 2, b + 131, b + 173, b + 137), fill=rgb(SILVER) + (255,))
    img.alpha_composite(panel)
    for row in range(4):
        for column in range(9):
            x, y = b + 8 + column * 18, b + 139 + row * 18 + (4 if row == 3 else 0)
            d.rectangle((x - 1, y - 1, x + 16, y + 16), fill=rgb("#0B0C0F") + (255,))
            d.rectangle((x, y, x + 15, y + 15), fill=rgb("#23242B") + (255,))
    return img


def tablet_item():
    img = Image.new("RGBA", (16, 16))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((1, 2, 14, 14), 2, fill=rgb("#16171C") + (255,), outline=rgb(EDGE) + (255,))
    for y in range(3, 12):  # screen: purple fading darker
        d.line((3, y, 12, y), fill=fade("#7B5BAA", "#3A2A5A", (y - 3) / 8))
    for i, colour in enumerate(("#3A7BD5", "#2F8F57", "#E2683C", "#C9971C")):  # app tiles
        x, y = 4 + i % 2 * 4, 4 + i // 2 * 4
        d.rectangle((x, y, x + 1, y + 1), fill=rgb(colour) + (255,))
    d.point((8, 13), fill=rgb(SILVER) + (255,))  # home button
    return img


def main():
    args = sys.argv[1:]
    glyphs = badges.load_font(args[args.index("--jar") + 1] if "--jar" in args else badges.JAR)
    for folder in ("assets/vexel/textures/font/phone", "assets/vexel/font", "assets/vexel/textures/item",
                   "assets/vexel/models/item", "assets/vexel/items"):
        os.makedirs(folder, exist_ok=True)
    screen(glyphs, APPS).save("assets/vexel/textures/font/phone/screen.png")
    screen(glyphs, APPS + STAFF_APPS).save("assets/vexel/textures/font/phone/screen_staff.png")
    # The title's baseline is 13 pixels below the menu's top, so ascent 13 + BORDER puts the glyph's top BORDER above it.
    height = 222 + 2 * BORDER
    font = {"providers": [
        {"type": "bitmap", "file": "vexel:font/phone/screen.png", "ascent": 13 + BORDER, "height": height, "chars": [SCREEN]},
        {"type": "bitmap", "file": "vexel:font/phone/screen_staff.png", "ascent": 13 + BORDER, "height": height,
         "chars": [STAFF_SCREEN]},
        {"type": "space", "advances": SPACES},
    ]}
    json.dump(font, open("assets/vexel/font/phone.json", "w"), indent=2)
    tablet_item().save("assets/vexel/textures/item/phone.png")
    json.dump({"parent": "minecraft:item/generated", "textures": {"layer0": "vexel:item/phone"}},
              open("assets/vexel/models/item/phone.json", "w"), indent=2)
    json.dump({"model": {"type": "minecraft:model", "model": "vexel:item/phone"}},
              open("assets/vexel/items/phone.json", "w"), indent=2)
    print("tablet screens and item written")


if __name__ == "__main__":
    main()
