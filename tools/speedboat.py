#!/usr/bin/env python3
"""Builds the speedboat model box by box, in the hand-made style of the sports car (shape after the "220 Bow Raider"
bow rider by sherif shawky).

    speedboat.py

Writes assets/vexel/models/item/vehicle/speedboat.json, its texture and assets/vexel/items/speedboat.json, and prints
the model scale, offset and size and the seat-height for the speedboat type in CityLifeCore's config. Run from the pack root. Needs Pillow.

Sizes are model pixels with the boat centred on x = 0 and its front towards +z; 47 pixels is its full length
(8 blocks). +x is the driver's left. The driver sits at the helm on the right (-x).
"""
import json
import math
import os

from PIL import Image

NAME = "speedboat"
LENGTH_BLOCKS = 8

COLOURS = {
    "white": (238, 241, 244), "shade": (214, 219, 225), "silver": (190, 197, 205), "blue": (28, 92, 196),
    "navy": (14, 38, 100), "cushion": (32, 70, 160), "pale": (226, 230, 236), "floor": (156, 162, 170),
    "teak": (140, 104, 70), "black": (30, 31, 35), "glass": (96, 128, 150), "chrome": (222, 226, 232),
    "red": (200, 40, 40), "green": (40, 170, 70),
}
SWATCH = 2  # texture pixels per colour
FIT = 0.9  # the boat is drawn this much smaller in the model file (the game scales it back up)
WATERLINE = 2.2  # height of the water surface on the hull
HIPS = (-4.2, 5.6, -2.4)  # the driver's hips on the helm seat

elements = []


def box(low, high, colour, faces=None, rotate=None):
    """A box from low to high (x, y, z) in one colour, with some faces in other colours (faces: name -> colour, or
    None to leave a face out). rotate is (axis, degrees, origin)."""
    element = {"from": list(low), "to": list(high), "colours": {}}
    for face in ("north", "south", "east", "west", "up", "down"):
        chosen = (faces or {}).get(face, colour)
        if chosen is not None:
            element["colours"][face] = chosen
    if rotate:
        element["rotate"] = rotate
    elements.append(element)


def pair(low, high, colour, faces=None, rotate=None):
    """A box on the left (+x) and its mirror image on the right."""
    box(low, high, colour, faces, rotate)
    mirrored = {"east": "west", "west": "east"}
    right_faces = {mirrored.get(k, k): v for k, v in (faces or {}).items()}
    right_rotate = None
    if rotate:
        axis, degrees, origin = rotate
        right_rotate = (axis, degrees if axis == "x" else -degrees, (-origin[0], origin[1], origin[2]))
    box((-high[0], low[1], low[2]), (-low[0], high[1], high[2]), colour, right_faces, right_rotate)


def leaning(start, end, size, colour, along, faces=None):
    """A bar of size (x, y) or (x, z) from start to end, leaning in one plane (along = "x" for fore and aft in the y-z
    plane, "y" for in the x-z plane)."""
    sx, sy, sz = start
    ex, ey, ez = end
    if along == "x":  # tilts in the y-z plane, around the x axis
        length = math.hypot(ey - sy, ez - sz)
        degrees = math.degrees(math.atan2(ez - sz, ey - sy))
        box((sx - size / 2, sy, sz - size / 2), (sx + size / 2, sy + length, sz + size / 2), colour, faces,
            ("x", round(degrees, 3), (sx, sy, sz)))
    else:  # turns in the x-z plane, around the y axis
        length = math.hypot(ex - sx, ez - sz)
        degrees = math.degrees(math.atan2(ex - sx, ez - sz))
        box((sx - size, sy, sz), (sx, ey, sz + length), colour, faces, ("y", round(degrees, 3), (sx, sy, sz)))


# --- Hull -------------------------------------------------------------------------------------------------------
# The hull is stacked layers, each a ring of panels following its own outline: lower layers are narrower and end
# further back, so the bottom is a stepped V and the bow leans forward.
BEAM = 8.0  # half width
GUNWALE = 7.6  # top of the hull sides, under the cap
STERN, BOW_START = -22.0, 4.0
# How the bow narrows: (share of the half width, share of the way from BOW_START to the stem).
SHAPE = [(1.0, 0.0), (0.92, 0.33), (0.71, 0.61), (0.39, 0.84), (0.08, 1.0)]
# Layers: bottom, top, half width, stem z, colour, inside colour, wall thickness (None = solid).
LAYERS = [
    (0.0, 1.0, 3.2, 12.0, "blue", None, None),
    (1.0, 2.6, 6.6, 17.0, "blue", None, None),
    (2.6, 4.4, 7.6, 20.0, "blue", "shade", 1.0),
    (4.4, 5.1, BEAM, 21.2, "navy", "white", 1.0),
    (5.1, GUNWALE, BEAM, 22.0, "white", "white", 1.0),
    (GUNWALE, GUNWALE + 0.8, BEAM + 0.2, 22.4, "white", "shade", 2.2),
]


def outline(half, stem):
    return [(half * width, BOW_START + along * (stem - BOW_START)) for width, along in SHAPE]


for y0, y1, half, stem, colour, inside, wall in LAYERS:
    thick = wall or 1.0
    faces = {"west": inside} if inside else {}
    pair((half - thick, y0, STERN), (half, y1, BOW_START), colour, faces)
    points = outline(half, stem)
    for (x0, z0), (x1, z1) in zip(points, points[1:]):
        length = math.hypot(x1 - x0, z1 - z0) + 0.3
        degrees = math.degrees(math.atan2(x1 - x0, z1 - z0))
        pair((x0 - thick, y0, z0), (x0, y1, z0 + length), colour, faces, ("y", round(degrees, 3), (x0, y0, z0)))
        if wall is None:
            box((-x1, y0, z0), (x1, y1, z1), colour, {"up": "floor"})
    if wall is None:
        # The top of the solid layers is the cockpit floor.
        box((-half + thick, y0, STERN), (half - thick, y1, BOW_START), colour, {"up": "floor"})
    # This layer's slice of the transom, the flat back.
    box((-half, y0, STERN - 1), (half, y1, STERN), colour, {"south": inside} if inside else None)

# Swim platform and the drive leg under it.
box((-7.4, 2.4, STERN - 4), (7.4, 3.0, STERN - 1), "teak", {"down": "shade"})
box((-1, -1.8, STERN - 3.4), (1, 2.4, STERN - 1.4), "black")
box((-0.6, -2.4, STERN - 3.8), (0.6, -1.8, STERN - 1.0), "black")
# Bow deck: the closed tip in front of the bow seats.
box((-3.0, GUNWALE - 0.6, 18.4), (3.0, GUNWALE + 0.6, 20.2), "white")
box((-1.2, GUNWALE - 0.6, 20.2), (1.2, GUNWALE + 0.6, 21.6), "white")
box((-0.3, GUNWALE + 0.6, 19.0), (0.3, GUNWALE + 1.1, 21.4), "chrome")  # bow rail stub
box((1.6, GUNWALE + 0.6, 19.2), (2.2, GUNWALE + 1.0, 19.8), "red")  # nav lights: red on the left, green on the right
box((-2.2, GUNWALE + 0.6, 19.2), (-1.6, GUNWALE + 1.0, 19.8), "green")

# --- Cockpit ----------------------------------------------------------------------------------------------------
FLOOR = 2.6
# Rear sun deck: a bench across the stern with a backrest against the transom.
box((-BEAM + 1, FLOOR, STERN), (BEAM - 1, 5.0, -16.5), "white")
box((-BEAM + 1, 5.0, -21.0), (BEAM - 1, 6.0, -16.5), "cushion", {"up": "cushion"})
box((-BEAM + 1, 5.0, STERN), (BEAM - 1, GUNWALE, -20.8), "cushion")
# Side seats along both sides, from the bench to the tower.
pair((4.6, FLOOR, -16.5), (BEAM - 1, 4.8, -7.0), "white")
pair((4.6, 4.8, -16.5), (BEAM - 1, 5.7, -7.0), "cushion")
pair((6.0, 5.7, -16.5), (BEAM - 1, 7.2, -7.0), "cushion")
# Helm (driver, right) and passenger consoles, with the windscreen on top.
box((-BEAM + 1, FLOOR, 0.8), (-1.8, 7.0, 4.4), "white", {"up": "black"})
box((1.8, FLOOR, 0.8), (BEAM - 1, 6.6, 4.4), "white")
box((-6.2, 6.4, 1.0), (-2.6, 7.4, 2.0), "black")  # dash
# Steering wheel: a black ring on a tilted column.
leaning((-4.4, 6.8, 0.6), (-4.4, 8.0, 0.0), 0.5, "silver", "x")
box((-5.6, 7.6, -0.3), (-3.2, 9.6, 0.2), "black", None, ("x", -20, (-4.4, 8.6, 0)))
box((-5.0, 8.2, -0.31), (-3.8, 9.0, 0.21), "silver", None, ("x", -20, (-4.4, 8.6, 0)))
# Seats: driver right, passenger left, with backrests.
for x in (-4.2, 4.2):
    box((x - 1.6, FLOOR, -4.4), (x + 1.6, 4.6, -1.0), "white")
    box((x - 1.6, 4.6, -4.4), (x + 1.6, 5.6, -1.0), "cushion")
    box((x - 1.6, 5.6, -4.6), (x + 1.6, 9.4, -3.6), "cushion", {"north": "white"})
# Bow seats: cushions along both sides and across the front, inside the narrowing bow.
pair((3.8, FLOOR, 5.2), (6.4, 5.0, 11.0), "white")
pair((3.8, 5.0, 5.2), (6.4, 5.9, 11.0), "cushion")
pair((2.6, FLOOR, 11.0), (4.8, 5.0, 15.6), "white")
pair((2.6, 5.0, 11.0), (4.8, 5.9, 15.6), "cushion")
box((-2.6, FLOOR, 15.6), (2.6, 5.4, 18.4), "white")
box((-2.6, 5.4, 15.6), (2.6, 6.3, 18.4), "cushion")
# Windscreen: tinted glass on each console, leaning back, with a chrome top edge.
for x0, x1 in ((-BEAM + 0.6, -1.8), (1.8, BEAM - 0.6)):
    box((x0, 6.6, 4.2), (x1, 9.2, 4.5), "glass", None, ("x", -32, (0, 6.6, 4.5)))
    box((x0, 9.2, 4.1), (x1, 9.6, 4.5), "chrome", None, ("x", -32, (0, 6.6, 4.5)))

# --- Wakeboard tower ----------------------------------------------------------------------------------------------
TOP = 17.0
for side in (1, -1):
    x = side * 6.9
    leaning((x, GUNWALE + 0.8, -1.2), (x, TOP, -5.0), 1.0, "silver", "x")
    leaning((x, GUNWALE + 0.8, -12.0), (x, TOP, -7.0), 1.0, "silver", "x")
box((-7.4, TOP - 0.2, -7.4), (7.4, TOP + 0.8, -4.4), "silver", {"up": "white"})
box((-4.0, TOP - 1.6, -6.8), (-1.6, TOP - 0.2, -5.0), "black")  # speakers under the top
box((1.6, TOP - 1.6, -6.8), (4.0, TOP - 0.2, -5.0), "black")


def main():
    names = list(COLOURS)
    columns = 8
    size = 16
    texture = Image.new("RGBA", (size, size))
    for index, name in enumerate(names):
        x, y = index % columns * SWATCH, index // columns * SWATCH
        for dx in range(SWATCH):
            for dy in range(SWATCH):
                texture.putpixel((x + dx, y + dy), COLOURS[name] + (255,))

    def uv(name):
        index = names.index(name)
        x, y = index % columns * SWATCH, index // columns * SWATCH
        return [x + 0.5, y + 0.5, x + SWATCH - 0.5, y + SWATCH - 0.5]

    # Shrink the boat to fit and centre it in the -16..32 range the game allows (checked before rotation).
    for e in elements:
        e["from"] = [c * FIT for c in e["from"]]
        e["to"] = [c * FIT for c in e["to"]]
        if "rotate" in e:
            axis, degrees, origin = e["rotate"]
            e["rotate"] = (axis, degrees, [c * FIT for c in origin])
    lows = [min(e["from"][k] for e in elements) for k in range(3)]
    highs = [max(e["to"][k] for e in elements) for k in range(3)]
    shift = [8 - (lows[k] + highs[k]) / 2 for k in range(3)]
    out = []
    for e in elements:
        element = {"from": [round(e["from"][k] + shift[k], 4) for k in range(3)],
                   "to": [round(e["to"][k] + shift[k], 4) for k in range(3)],
                   "faces": {face: {"uv": uv(colour), "texture": "#0"} for face, colour in e["colours"].items()}}
        if "rotate" in e:
            axis, degrees, origin = e["rotate"]
            element["rotation"] = {"origin": [round(origin[k] + shift[k], 4) for k in range(3)],
                                   "x": degrees if axis == "x" else 0, "y": degrees if axis == "y" else 0,
                                   "z": degrees if axis == "z" else 0}
        assert all(-16 <= c <= 32 for c in element["from"] + element["to"]), element
        out.append(element)

    key = f"vexel:item/vehicle/{NAME}_0"
    os.makedirs("assets/vexel/textures/item/vehicle", exist_ok=True)
    os.makedirs("assets/vexel/models/item/vehicle", exist_ok=True)
    os.makedirs("assets/vexel/items", exist_ok=True)
    texture.save(f"assets/vexel/textures/item/vehicle/{NAME}_0.png")
    model = {"textures": {"0": key, "particle": key}, "elements": out,
             "display": {"gui": {"rotation": [30, 225, 0], "scale": [0.34, 0.34, 0.34]}}}
    json.dump(model, open(f"assets/vexel/models/item/vehicle/{NAME}.json", "w"), indent=1)
    json.dump({"model": {"type": "minecraft:model", "model": f"vexel:item/vehicle/{NAME}"}},
              open(f"assets/vexel/items/{NAME}.json", "w"), indent=2)

    # CityLifeCore's numbers: the model's centre from the water surface below the driver, and the seat above it.
    scale = LENGTH_BLOCKS * 16 / (highs[2] - lows[2])
    block = scale / 16  # blocks per model pixel
    centre = [(lows[k] + highs[k]) / 2 for k in range(3)]
    offset = [(centre[0] - HIPS[0] * FIT) * block, (centre[1] - WATERLINE * FIT) * block, (centre[2] - HIPS[2] * FIT) * block]
    print(f"{NAME}: {len(out)} boxes")
    print(f"  scale: {scale:.4f}")
    print(f"  offset: [{offset[0]:.4f}, {offset[1]:.4f}, {offset[2]:.4f}]")
    print(f"  size: [{(highs[0] - lows[0]) * block:.2f}, {(highs[1] - lows[1]) * block:.2f}, {(highs[2] - lows[2]) * block:.2f}]")
    print(f"  seat-height: {(HIPS[1] - WATERLINE) * FIT * block - 0.13:.3f}")


if __name__ == "__main__":
    main()
