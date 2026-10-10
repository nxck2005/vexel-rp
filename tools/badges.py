#!/usr/bin/env python3
"""Draws the rank badges shown in chat and the tab list, and adds them to the pack's default font.

    badges.py [--style B|E] [--jar <minecraft client jar>]

B: bold text with a shadow in a darker shade of the badge colour, and a bevel. E: plain text, the bevel and a soft
half-pixel shadow, drawn at twice the resolution. Each badge keeps its font character in both styles, so switching
is only a rerun and a new pack release: LuckPerms prefixes don't change.

Text uses Minecraft's own font, read from the client jar at runtime (default: the 26.2 jar Gradle's Fabric Loom
cache keeps). Writes assets/vexel/textures/font/badge/*.png and assets/minecraft/font/default.json. Font files
from all packs are combined, so this only adds our characters. Needs Pillow. Run from the pack root.
"""
import io
import json
import os
import sys
import zipfile

from PIL import Image, ImageDraw

STAR = ["00100", "01110", "11111", "01110", "01010"]
SHIELD = ["01110", "11111", "11111", "11111", "01110", "00100"]
HAMMER = ["11110", "11110", "00100", "00100", "00100"]

# id, text, character, background, text colour, icon. The character is what LuckPerms prefixes hold: never reuse one.
BADGES = [
    ("citizen", "CITIZEN", "", "#4A4D57", "#E2E2E8", None),
    ("vip", "VIP", "", "#2F8F57", "#F0FFF5", None),
    ("mvp", "MVP", "", "#2A86C9", "#EAF6FF", None),
    ("vexel", "VEXEL", "", "#6A44A6", "#F3ECFF", STAR),
    ("vexelplus", "VEXEL+", "", "#8A2BE2", "#FFF4D6", STAR),
    ("builder", "BUILDER", "", "#C2611F", "#FFF1E6", HAMMER),
    ("helper", "HELPER", "", "#1F9A9A", "#E6FFFF", SHIELD),
    ("mod", "MOD", "", "#D4A017", "#FFF8DC", SHIELD),
    ("admin", "ADMIN", "", "#CC3B2E", "#FFF0EE", SHIELD),
    ("owner", "OWNER", "", "#1A1B20", "#E7C6FF", SHIELD),
]
HEIGHT = 9  # in GUI pixels; chat text is 8 tall
JAR = os.path.expanduser("~/.gradle/caches/fabric-loom/26.2/minecraft-client.jar")


def rgb(colour):
    return tuple(int(colour[i:i + 2], 16) for i in (1, 3, 5))


def mix(colour, target, amount):
    return tuple(round(a + (b - a) * amount) for a, b in zip(colour, target))


def load_font(jar):
    """Glyph image and width for each character of Minecraft's ascii.png."""
    with zipfile.ZipFile(jar) as z:
        providers = json.loads(z.read("assets/minecraft/font/include/default.json"))["providers"]
        ascii_provider = next(p for p in providers if p.get("file") == "minecraft:font/ascii.png")
        sheet = Image.open(io.BytesIO(z.read("assets/minecraft/textures/font/ascii.png"))).convert("RGBA")
    rows = ascii_provider["chars"]
    size = sheet.width // len(rows[0])
    glyphs = {}
    for r, row in enumerate(rows):
        for c, char in enumerate(row):
            glyph = sheet.crop((c * size, r * size, (c + 1) * size, (r + 1) * size)).getchannel("A")
            box = glyph.getbbox()
            glyphs[char] = (glyph, box[2] if box else 0)
    return glyphs


def text_width(glyphs, text, bold):
    return sum(4 if ch == " " else glyphs[ch][1] + 1 for ch in text) + (len(text) if bold else 0) - 1


def badge(glyphs, text, bg, fg, icon, style):
    """One badge at `scale` texture pixels per GUI pixel."""
    bold = style == "B"
    scale = 2 if style == "E" else 1
    back, front = rgb(bg), rgb(fg)
    shadow = mix(back, (0, 0, 0), 0.55 if bold else 0.5)
    icon_width = 6 if icon else 0
    width = text_width(glyphs, text, bold) + icon_width + 5
    img = Image.new("RGBA", (width * scale, HEIGHT * scale))
    d = ImageDraw.Draw(img)
    w, h = img.size
    s = scale

    def dot(x, y, colour):  # one GUI pixel, with its top left at texture pixel (x, y)
        d.rectangle((x, y, x + s - 1, y + s - 1), fill=colour + (255,))

    # Body with clipped corners, then the bevel: light top and left, dark bottom and right.
    d.rectangle((s, 0, w - s - 1, h - 1), fill=back + (255,))
    d.rectangle((0, s, w - 1, h - s - 1), fill=back + (255,))
    d.rectangle((s, 0, w - s - 1, s - 1), fill=mix(back, (255, 255, 255), 0.35) + (255,))
    d.rectangle((0, s, s - 1, h - 2 * s - 1), fill=mix(back, (255, 255, 255), 0.18) + (255,))
    d.rectangle((s, h - s, w - s - 1, h - 1), fill=mix(back, (0, 0, 0), 0.45) + (255,))
    d.rectangle((w - s, 2 * s, w - 1, h - s - 1), fill=mix(back, (0, 0, 0), 0.3) + (255,))

    # The shadow sits one texture pixel down and right: a whole GUI pixel for B, half a pixel for E.
    layers = [(shadow, 1), (front, 0)]
    if icon:
        top = (HEIGHT - len(icon)) // 2
        for colour, off in layers:
            for y, row in enumerate(icon):
                for x, bit in enumerate(row):
                    if bit == "1":
                        dot((2 + x) * s + off, (top + y) * s + off, colour)
    for colour, off in layers:
        cx = 2 + icon_width
        for ch in text:
            if ch == " ":
                cx += 4 + (1 if bold else 0)
                continue
            glyph, glyph_width = glyphs[ch]
            for dx in ((0, 1) if bold else (0,)):
                for y in range(glyph.height):
                    for x in range(glyph.width):
                        if glyph.getpixel((x, y)):
                            dot((cx + x + dx) * s + off, (1 + y) * s + off, colour)
            cx += glyph_width + 1 + (1 if bold else 0)
    return img


def main():
    args = sys.argv[1:]
    style = args[args.index("--style") + 1] if "--style" in args else "B"
    jar = args[args.index("--jar") + 1] if "--jar" in args else JAR
    if style not in ("B", "E"):
        sys.exit("--style must be B or E")
    glyphs = load_font(jar)
    os.makedirs("assets/vexel/textures/font/badge", exist_ok=True)
    os.makedirs("assets/minecraft/font", exist_ok=True)
    providers = []
    for badge_id, text, char, bg, fg, icon in BADGES:
        badge(glyphs, text, bg, fg, icon, style).save(f"assets/vexel/textures/font/badge/{badge_id}.png")
        providers.append({"type": "bitmap", "file": f"vexel:font/badge/{badge_id}.png", "ascent": 8, "height": HEIGHT, "chars": [char]})
    json.dump({"providers": providers}, open("assets/minecraft/font/default.json", "w"), indent=2)
    print(f"{len(BADGES)} badges in style {style}")
    for badge_id, _, char, *_ in BADGES:
        print(f"  {badge_id}: U+{ord(char):04X}")


if __name__ == "__main__":
    main()
