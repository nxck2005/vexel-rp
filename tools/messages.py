#!/usr/bin/env python3
"""Draws the tablet's Messages screens (an iMessage-style inbox and conversation) and the fonts that place text on them.

    messages.py [--jar <minecraft client jar>]

Like the tablet home screen (phone.py), each screen is one glyph in a chest menu's title: U+E202 the conversation and
U+E203 the inbox, in the font vexel:messages. The plugin writes everything else (names, bubbles, times) after it in
the same title. A title is one line of text, so to place text at a height y (menu pixels, the title itself is at 6)
there is one font per height, vexel:msg/y<y>, for y 5 to 123. Each holds:
- Minecraft's ascii.png letters, moved down to y (characters other than ascii fall back and land on the wrong line),
- bubble pieces (BUBBLE_CHARS) 3 pixels tall, which the plugin stacks into bubbles of any size,
- the unknown-number avatar (U+E340) and the unread dot (U+E341).
The plugin moves along with phone.py's space characters. The layout (slots, rows, bubble colours) must match
CityLifeCore's messages feature. Also writes vexel:blank, an item that shows nothing, for clickable spots.
Needs Pillow. Run from the pack root.
"""
import json
import os
import sys
import zipfile

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import badges  # noqa: E402
import phone  # noqa: E402
from phone import BORDER, rgb, text, width  # noqa: E402

BLUE, GREY, DARK, HEADER, LINE, MUTED = "#0A84FF", "#2C2C2E", "#0B0B0D", "#161618", "#2C2C2E", "#6C6C70"
LOWEST, HIGHEST = 5, 123  # text needs y >= 5: a font's ascent (13 - y) can't be more than its height (8)
BUBBLE_CHARS = 0xE300  # + colour (blue 0, grey 1) * 27 + strip (top 0, middle 1, bottom 2) * 9 + piece
FILLS = [1, 2, 4, 8, 16, 32, 64]  # pieces: 0 left end, 1 right end, 2.. a fill this many pixels wide


def chevron(d, x, y, up):
    pts = [(x, y + 4), (x + 4, y), (x + 8, y + 4)] if up else [(x, y), (x + 4, y + 4), (x + 8, y)]
    d.line(pts, fill=rgb(BLUE) + (255,), width=2)


def base(header):
    """The tablet with a dark screen; header is how tall the lighter top bar is."""
    b = BORDER
    img = phone.bezel()
    scr = Image.new("RGBA", (176, 222))
    d = ImageDraw.Draw(scr)
    d.rectangle((0, 0, 175, 123), fill=rgb(DARK) + (255,))
    if header:
        d.rectangle((0, 0, 175, header), fill=rgb(HEADER) + (255,))
        d.line((0, header + 1, 175, header + 1), fill=rgb(LINE) + (255,))
    mask = Image.new("L", scr.size)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, 175, 221), 6, fill=255)
    img.paste(scr, (b, b), mask)
    return img


def conversation(glyphs):
    """Slot row 0: Back (slots 0-1), the contact's head (4), older and newer (7, 8). Slot row 5: the type bar."""
    b = BORDER
    img = base(36)
    d = ImageDraw.Draw(img)
    d.line([(b + 15, b + 20), (b + 11, b + 26), (b + 15, b + 32)], fill=rgb(BLUE) + (255,), width=2)
    text(img, glyphs, b + 19, b + 22, "Back", BLUE)
    chevron(d, b + 138, b + 24, True)
    chevron(d, b + 156, b + 24, False)
    d.rounded_rectangle((b + 6, b + 109, b + 169, b + 122), 6, outline=rgb("#3A3A3C") + (255,), fill=rgb("#1C1C1E") + (255,))
    text(img, glyphs, b + 13, b + 112, "Type a message...", MUTED)
    d.ellipse((b + 156, b + 110, b + 167, b + 121), fill=rgb(BLUE) + (255,))
    d.line([(b + 161, b + 118), (b + 161, b + 113)], fill=(255, 255, 255, 255))
    d.line([(b + 159, b + 115), (b + 161, b + 113), (b + 163, b + 115)], fill=(255, 255, 255, 255))
    phone.pocket(img)
    return img


def inbox(glyphs):
    """Five conversation rows on slot rows 0-4. Slot row 5: Share (45-47), New message (48-51), page up and down."""
    b = BORDER
    img = base(0)
    d = ImageDraw.Draw(img)
    text(img, glyphs, b + 8, b + 5, "Messages", "#FFFFFF")
    for row in range(4):
        d.line((b + 28, b + 35 + row * 18, b + 175, b + 35 + row * 18), fill=rgb("#1F1F22") + (255,))
    d.rounded_rectangle((b + 6, b + 109, b + 58, b + 122), 6, fill=rgb("#1C1C1E") + (255,))
    text(img, glyphs, b + 32 - width(glyphs, "Share") // 2, b + 112, "Share", BLUE)
    d.rounded_rectangle((b + 62, b + 109, b + 131, b + 122), 6, fill=rgb(BLUE) + (255,))
    text(img, glyphs, b + 97 - width(glyphs, "New message") // 2, b + 112, "New message", "#FFFFFF")
    chevron(d, b + 138, b + 113, True)
    chevron(d, b + 156, b + 113, False)
    phone.pocket(img)
    return img


def bubble_pieces():
    """6 rows (blue top/middle/bottom, grey top/middle/bottom) of 9 cells 64x3. Ends are 3 wide with a 3-pixel round
    corner; the bottom strip's outer end is 5 wide with a tail (grey on the left, blue on the right)."""
    img = Image.new("RGBA", (64 * 9, 18))
    d = ImageDraw.Draw(img)
    for colour_index, colour in enumerate((BLUE, GREY)):
        fill = rgb(colour) + (255,)
        for strip in range(3):
            y = (colour_index * 3 + strip) * 3
            for row in range(3):
                # Pixels cut from the corner on this row: top strip 2, 1, 0 and bottom strip 0, 1, 2.
                cut = (2 - row) if strip == 0 else row if strip == 2 else 0
                tail = strip == 2
                if tail and colour == GREY:  # left end with the tail: 2 extra pixels, the bottom row reaching out
                    d.line((2 - row, y + row, 4, y + row), fill=fill)
                else:
                    d.line((cut, y + row, 2, y + row), fill=fill)
                if tail and colour == BLUE:
                    d.line((64, y + row, 64 + 2 + row, y + row), fill=fill)
                else:
                    d.line((64, y + row, 64 + 2 - cut, y + row), fill=fill)
                for i, w in enumerate(FILLS):
                    d.line((64 * (2 + i), y + row, 64 * (2 + i) + w - 1, y + row), fill=fill)
    return img


def icons(glyphs):
    """16x16 cells: the avatar for numbers that aren't a contact, and the unread dot."""
    img = Image.new("RGBA", (32, 16))
    d = ImageDraw.Draw(img)
    d.ellipse((1, 1, 14, 14), fill=rgb("#636366") + (255,))
    text(img, glyphs, 6, 4, "?", "#FFFFFF")
    d.ellipse((16, 6, 19, 9), fill=rgb(BLUE) + (255,))
    return img


def line_font(y, ascii_chars):
    ascent = 13 - y  # the title is drawn at y 6 with its baseline 7 lower
    providers = [{"type": "space", "advances": {" ": 4}},
                 {"type": "bitmap", "file": "minecraft:font/ascii.png", "ascent": ascent, "height": 8, "chars": ascii_chars},
                 {"type": "bitmap", "file": "vexel:font/messages/icons.png", "ascent": ascent, "height": 16,
                  "chars": [""]}]
    if ascent <= 3:
        providers.append({"type": "bitmap", "file": "vexel:font/messages/bubble.png", "ascent": ascent, "height": 3,
                          "chars": ["".join(chr(BUBBLE_CHARS + row * 9 + piece) for piece in range(9)) for row in range(6)]})
    return {"providers": providers}


if __name__ == "__main__":
    args = sys.argv[1:]
    jar = args[args.index("--jar") + 1] if "--jar" in args else badges.JAR
    glyphs = badges.load_font(jar)
    with zipfile.ZipFile(jar) as z:
        default = json.loads(z.read("assets/minecraft/font/include/default.json"))["providers"]
    ascii_chars = next(p for p in default if p.get("file") == "minecraft:font/ascii.png")["chars"]
    for folder in ("assets/vexel/textures/font/messages", "assets/vexel/font/msg", "assets/vexel/items"):
        os.makedirs(folder, exist_ok=True)
    conversation(glyphs).save("assets/vexel/textures/font/messages/conversation.png")
    inbox(glyphs).save("assets/vexel/textures/font/messages/inbox.png")
    bubble_pieces().save("assets/vexel/textures/font/messages/bubble.png")
    icons(glyphs).save("assets/vexel/textures/font/messages/icons.png")
    json.dump({"providers": [
        {"type": "bitmap", "file": "vexel:font/messages/conversation.png", "ascent": 21, "height": 238, "chars": [""]},
        {"type": "bitmap", "file": "vexel:font/messages/inbox.png", "ascent": 21, "height": 238, "chars": [""]},
    ]}, open("assets/vexel/font/messages.json", "w"), indent=2)
    for y in range(LOWEST, HIGHEST + 1):
        json.dump(line_font(y, ascii_chars), open(f"assets/vexel/font/msg/y{y}.json", "w"))
    json.dump({"model": {"type": "minecraft:empty"}}, open("assets/vexel/items/blank.json", "w"), indent=2)
    print(f"messages screens and {HIGHEST - LOWEST + 1} line fonts written")
