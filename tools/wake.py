#!/usr/bin/env python3
"""Draws the boat wake: pieces of the two lines of a wake's V, as flat item models vexel:wake_v_<angle>_<stage>_<holes>.

    wake.py

CityLifeCore lays one piece per side for each block a boat travels, starting at the bow, and drifts it outward so the
pieces join into the V. Each piece is a square 4 blocks across (16 pixels per block, like the world) laid square to
the world grid, with a stair-stepped pixel line through its middle at <angle> degrees (every 5) and see-through foam
with holes on its left side (towards the boat's path). <stage> 0 to 3 is how faded it is, <holes> one of two hole
patterns. The pieces are drawn for a 19.5 degree V and 1 block per piece, as CityLifeCore lays them.
Run from the pack root. Needs Pillow.
"""
import glob
import json
import math
import os
import random

from PIL import Image

SIZE, SPAN = 64, 4.0  # texture pixels, blocks across
LINE = 0.075  # half thickness of the line, in blocks
FOAM = 1.8  # how far the foam reaches inside the line, in blocks
LENGTH = 1 / math.cos(math.radians(19.5))  # a piece's length along its line: 1 block of travel
# Per stage: line alpha, foam alpha, share of foam left out as holes.
STAGES = [(240, 110, 0.0), (225, 80, 0.3), (180, 40, 0.6), (110, 0, 1.0)]

os.makedirs("assets/vexel/textures/item/wake", exist_ok=True)
os.makedirs("assets/vexel/models/item/wake", exist_ok=True)
os.makedirs("assets/vexel/items", exist_ok=True)
for old in glob.glob("assets/vexel/*/item/wake/*") + glob.glob("assets/vexel/items/wake_*.json"):
    os.remove(old)

rng = random.Random(9)


def holes():
    """Smooth noise from 0 to 1 (random values on a grid blended between points), so holes come in clumps."""
    grid = [[rng.random() for _ in range(17)] for _ in range(17)]

    def at(px, pz):
        gx, gz = px / SIZE * 16, pz / SIZE * 16
        x0, z0 = int(gx), int(gz)
        fx, fz = gx - x0, gz - z0
        top = grid[x0][z0] * (1 - fx) + grid[x0 + 1][z0] * fx
        bottom = grid[x0][z0 + 1] * (1 - fx) + grid[x0 + 1][z0 + 1] * fx
        return top * (1 - fz) + bottom * fz
    values = [[at(px, pz) for pz in range(SIZE)] for px in range(SIZE)]
    low, high = min(map(min, values)), max(map(max, values))
    return [[(v - low) / (high - low) for v in row] for row in values]


patterns = [holes(), holes()]
count = 0
for angle in range(0, 360, 5):
    dx, dz = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    nx, nz = -dz, dx  # the line's left, where the foam goes
    for stage, (line_alpha, foam_alpha, gaps) in enumerate(STAGES):
        for variant, noise in enumerate(patterns):
            image = Image.new("RGBA", (SIZE, SIZE))
            for px in range(SIZE):
                for pz in range(SIZE):
                    x = (px + 0.5) / SIZE * SPAN - SPAN / 2
                    z = (pz + 0.5) / SIZE * SPAN - SPAN / 2
                    along, across = x * dx + z * dz, x * nx + z * nz
                    if abs(across) <= LINE and abs(along) <= LENGTH * 0.75:
                        # The line overlaps its neighbours, so it stays joined through turns.
                        image.putpixel((px, pz), (255, 255, 255, line_alpha))
                    elif foam_alpha and abs(along) <= LENGTH / 2 and LINE < across <= LINE + FOAM:
                        # Foam fades and breaks up further from the line. It must not overlap the next piece's foam,
                        # or the see-through layers would add up into a seam.
                        depth = (across - LINE) / FOAM
                        if noise[px][pz] > gaps + depth ** 2 * 0.7:
                            image.putpixel((px, pz), (220, 232, 244, int(foam_alpha * (1 - 0.6 * depth))))
            name = f"wake_v_{angle:03d}_{stage}_{variant}"
            image.save(f"assets/vexel/textures/item/wake/{name}.png")
            texture = f"vexel:item/wake/{name}"
            model = {"textures": {"0": texture, "particle": texture},
                     "elements": [{"from": [0, 8, 0], "to": [16, 8, 16],
                                   "faces": {"up": {"uv": [0, 0, 16, 16], "texture": "#0"}}}]}
            json.dump(model, open(f"assets/vexel/models/item/wake/{name}.json", "w"))
            json.dump({"model": {"type": "minecraft:model", "model": f"vexel:item/wake/{name}"}},
                      open(f"assets/vexel/items/{name}.json", "w"))
            count += 1
print(f"wake: {count} pieces")
