#!/usr/bin/env python3
"""Draws an item model the way Minecraft builds it (face corners, uv mapping, x/y/z rotation), to check a conversion.

    preview.py <assets/vexel/models/...json> <out.png>

Renders two views (front-left and back-right, looking down a little) with simple face shading. Needs Pillow.
Run from the pack root.
"""
import json
import math
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from gltf_to_model import FACE_VERTICES  # noqa: E402

SHADE = {"up": 1.0, "down": 0.5, "north": 0.8, "south": 0.8, "west": 0.6, "east": 0.6}
NORMALS = {"down": (0, -1, 0), "up": (0, 1, 0), "north": (0, 0, -1), "south": (0, 0, 1), "west": (-1, 0, 0), "east": (1, 0, 0)}


def rot(axis, degrees):
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    return {"x": [[1, 0, 0], [0, c, -s], [0, s, c]], "y": [[c, 0, s], [0, 1, 0], [-s, 0, c]], "z": [[c, -s, 0], [s, c, 0], [0, 0, 1]]}[axis]


def mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def apply(m, v):
    return [sum(m[i][k] * v[k] for k in range(3)) for i in range(3)]


def faces(model):
    for element in model["elements"]:
        low, high = element["from"], element["to"]
        m, origin = [[1, 0, 0], [0, 1, 0], [0, 0, 1]], [0, 0, 0]
        if "rotation" in element:
            r = element["rotation"]
            origin = r["origin"]
            if "axis" in r:
                m = rot(r["axis"], r["angle"])
            else:  # rotationZYX: R = Rz * Ry * Rx
                m = mul(rot("z", r["z"]), mul(rot("y", r["y"]), rot("x", r["x"])))
        for direction, face in element["faces"].items():
            corners = []
            for pick in FACE_VERTICES[direction]:
                p = [(high if pick[k] else low)[k] - origin[k] for k in range(3)]
                corners.append([c + o for c, o in zip(apply(m, p), origin)])
            u1, v1, u2, v2 = face["uv"]
            shift = face.get("rotation", 0) // 90
            uvs = []
            for v in range(4):
                index = (v + shift) % 4
                uvs.append((u1 if index in (0, 1) else u2, v1 if index in (0, 3) else v2))
            yield corners, uvs, apply(m, NORMALS[direction]), face["texture"], SHADE[direction]


def render(model, textures, yaw, pitch, size=600):
    view = mul(rot("x", pitch), rot("y", yaw))
    drawn = []
    for corners, uvs, normal, texture, shade in faces(model):
        n = apply(view, normal)
        if n[2] <= 0:  # facing away; Minecraft culls back faces of item models
            continue
        points = [apply(view, [c - 8 for c in corner]) for corner in corners]
        drawn.append((sum(p[2] for p in points) / 4, points, uvs, texture, shade))
    image = Image.new("RGBA", (size, size), (40, 40, 48, 255))
    scale = size / 60
    for _, points, uvs, texture, shade in sorted(drawn, key=lambda d: d[0]):
        screen = [(size / 2 + p[0] * scale, size / 2 - p[1] * scale) for p in points]
        tex = textures[texture]
        w, h = tex.size
        src = [(u / 16 * w, v / 16 * h) for u, v in uvs]
        # Affine map from screen to texture through three corners.
        (x0, y0), (x1, y1), (x2, y2) = screen[0], screen[1], screen[2]
        det = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
        if abs(det) < 1e-9:
            continue
        coeffs = []
        for k in range(2):
            s0, s1, s2 = src[0][k], src[1][k], src[2][k]
            a = ((s1 - s0) * (y2 - y0) - (s2 - s0) * (y1 - y0)) / det
            b = ((s2 - s0) * (x1 - x0) - (s1 - s0) * (x2 - x0)) / det
            coeffs += [a, b, s0 - a * x0 - b * y0]
        layer = tex.transform((size, size), Image.Transform.AFFINE, coeffs, Image.Resampling.NEAREST)
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).polygon(screen, fill=255)
        mask = Image.composite(layer.getchannel("A"), Image.new("L", (size, size), 0), mask).point(lambda a: 255 if a > 25 else 0)
        rgb = layer.convert("RGB").point(lambda c: int(c * shade))
        image.paste(rgb, (0, 0), mask)
    return image


def main():
    path, out = sys.argv[1], sys.argv[2]
    model = json.load(open(path))
    textures = {}
    for key, value in model["textures"].items():
        namespace, name = value.split(":")
        textures["#" + key] = Image.open(f"assets/{namespace}/textures/{name}.png").convert("RGBA")
    sheet = Image.new("RGBA", (1200, 600))
    sheet.paste(render(model, textures, 35, 25), (0, 0))
    sheet.paste(render(model, textures, 215, 25), (600, 0))
    sheet.save(out)


if __name__ == "__main__":
    main()
