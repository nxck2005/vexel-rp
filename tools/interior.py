#!/usr/bin/env python3
"""Builds detailed car interiors as converter edits, and draws the interior texture they use.

    interior.py <name>

Writes tools/edits/<name>.json (picked up by gltf_to_model.py) and assets/vexel/textures/item/vehicle/interior.png.
Each car's layout is a function below (front is -z, the driver sits on the -x side); details follow the car's style.
Needs Pillow. Run from the pack root.
"""
import json
import math
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
from gltf_to_model import FIT, euler_xyz, faces_of, load, mat_mul, node_matrix  # noqa: E402

TEXTURE = "vexel:item/vehicle/interior"
WIDTH, HEIGHT = 64, 96  # interior.png; uv runs 0-16 across each side
SPORTS_CAR_PX = 5.8542  # the sports car's model pixels per block, which the detail sizes were made for
INCOMING = os.path.expanduser("~/projects/vexel-dev/models-incoming")

# Plain colours: a 4x4-texel swatch each along the top row, then the second row.
COLOURS = {
    "rim": (34, 34, 38), "leather": (46, 42, 40), "silver": (178, 178, 186), "black": (10, 10, 10),
    "headliner": (74, 74, 80), "carpet": (26, 26, 28), "red": (150, 28, 34), "cream": (226, 218, 196),
    "white": (232, 232, 232), "plastic": (24, 24, 27), "chrome": (216, 216, 224), "glass": (120, 150, 170),
    "amber": (240, 170, 40), "darkgrey": (44, 44, 48), "leather2": (64, 57, 53), "grey": (108, 108, 116),
    "tint": (40, 52, 60, 110),  # see-through window glass
}
# Detail tiles: 16x16 texels each, four to a row, starting at texel row 16.
TILES = ["gauge", "tacho", "screen", "vent", "stitch", "carbon", "speaker", "hub", "mirror", "buttons", "digital",
         "doorpad", "classic_gauge", "classic_small", "chrome_hub"]


def draw_texture(path):
    image = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
    d = ImageDraw.Draw(image)
    for i, colour in enumerate(COLOURS.values()):
        x, y = (i % 16) * 4, (i // 16) * 4
        d.rectangle([x, y, x + 3, y + 3], fill=colour if len(colour) == 4 else colour + (255,))

    def tile(name):
        i = TILES.index(name)
        return (i % 4) * 16, 16 + (i // 4) * 16

    def dial(name, face, ring, tick, needle, redline, ticks=11):
        x, y = tile(name)
        d.rectangle([x, y, x + 15, y + 15], fill=(0, 0, 0, 0))  # see-through corners leave a round dial
        d.ellipse([x, y, x + 15, y + 15], fill=face + (255,), outline=ring + (255,))
        for k in range(ticks):  # ticks round 270 degrees
            a = math.radians(135 + k * 270 / (ticks - 1))
            colour = (200, 40, 40) if redline and k >= ticks - 3 else tick
            d.point((x + 7.5 + 5.6 * math.cos(a), y + 7.5 + 5.6 * math.sin(a)), fill=colour + (255,))
        a = math.radians(205)
        d.line([(x + 7.5, y + 7.5), (x + 7.5 + 4.5 * math.cos(a), y + 7.5 + 4.5 * math.sin(a))], fill=needle + (255,))

    dial("gauge", (10, 10, 12), (60, 60, 66), (200, 200, 205), (210, 40, 40), False)
    dial("tacho", (10, 10, 12), (60, 60, 66), (200, 200, 205), (210, 40, 40), True)
    dial("classic_gauge", (226, 218, 196), (200, 200, 206), (30, 30, 30), (20, 20, 20), False)
    dial("classic_small", (226, 218, 196), (200, 200, 206), (30, 30, 30), (20, 20, 20), False, 7)
    x, y = tile("screen")
    d.rectangle([x, y, x + 15, y + 15], fill=(16, 18, 22, 255))
    d.rectangle([x, y, x + 15, y + 1], fill=(36, 38, 44, 255))
    for k in range(3, 14, 3):
        d.line([(x + 2, y + k + 1), (x + 9 + (k % 4), y + k + 1)], fill=(52, 60, 74, 255))
    d.rectangle([x + 11, y + 4, x + 13, y + 6], fill=(150, 150, 156, 255))
    x, y = tile("vent")
    d.rectangle([x, y, x + 15, y + 15], fill=(14, 14, 16, 255))
    for row in range(1, 16, 3):
        d.line([(x, y + row), (x + 15, y + row)], fill=(50, 50, 55, 255))
    x, y = tile("stitch")
    d.rectangle([x, y, x + 15, y + 15], fill=COLOURS["leather"] + (255,))
    for k in range(0, 16, 2):
        for px, py in ((x + k, y + 1), (x + k, y + 14), (x + 1, y + k), (x + 14, y + k)):
            d.point((px, py), fill=(62, 57, 54, 255))
    x, y = tile("carbon")
    for i in range(16):
        for j in range(16):
            d.point((x + i, y + j), fill=(36, 36, 40, 255) if (i // 2 + j // 2) % 2 else (22, 22, 24, 255))
    x, y = tile("speaker")
    d.rectangle([x, y, x + 15, y + 15], fill=(28, 28, 30, 255))
    for i in range(1, 16, 2):
        for j in range(1, 16, 2):
            if (i - 7.5) ** 2 + (j - 7.5) ** 2 < 49:
                d.point((x + i, y + j), fill=(12, 12, 12, 255))
    x, y = tile("hub")
    d.rectangle([x, y, x + 15, y + 15], fill=(22, 22, 25, 255))
    d.rectangle([x + 5, y + 7, x + 10, y + 8], fill=COLOURS["silver"] + (255,))
    x, y = tile("chrome_hub")
    d.rectangle([x, y, x + 15, y + 15], fill=COLOURS["chrome"] + (255,))
    d.ellipse([x + 4, y + 4, x + 11, y + 11], fill=(30, 30, 32, 255))
    x, y = tile("mirror")
    for j in range(16):
        d.line([(x, y + j), (x + 15, y + j)], fill=(150 - j * 3, 172 - j * 3, 190 - j * 2, 255))
    x, y = tile("buttons")
    d.rectangle([x, y, x + 15, y + 15], fill=(22, 22, 25, 255))
    for k in range(4):
        d.rectangle([x + 1 + k * 4, y + 6, x + 2 + k * 4, y + 9], fill=(86, 86, 92, 255))
    x, y = tile("digital")
    d.rectangle([x, y, x + 15, y + 15], fill=(10, 10, 12, 255))
    for k in range(3):
        d.rectangle([x + 3 + k * 4, y + 6, x + 5 + k * 4, y + 10], fill=(170, 170, 176, 255))
    x, y = tile("doorpad")
    d.rectangle([x, y, x + 15, y + 15], fill=COLOURS["leather2"] + (255,))
    for k in range(2, 16, 4):
        d.line([(x, y + k), (x + 15, y + k)], fill=COLOURS["leather"] + (255,))
    image.save(path)


def uv_of(texture):
    """uv box for a colour name or tile name."""
    if texture in COLOURS:
        i = list(COLOURS).index(texture)
        x, y, w, h = (i % 16) * 4 + 1, (i // 16) * 4 + 1, 2, 2
    else:
        i = TILES.index(texture)
        x, y, w, h = (i % 4) * 16, 16 + (i // 4) * 16, 16, 16
    return [round(x * 16 / WIDTH, 4), round(y * 16 / HEIGHT, 4), round((x + w) * 16 / WIDTH, 4), round((y + h) * 16 / HEIGHT, 4)]


def retexture(index, face, texture):
    """Repaints one face of a converted element (by its index before edits) with the interior texture."""
    return {"index": index, "face": face, "uv": uv_of(texture), "texture": "#interior"}


def rx(degrees):
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    return [[1, 0, 0], [0, c, -s], [0, s, c]]


def ry(degrees):
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    return [[c, 0, s], [0, 1, 0], [-s, 0, c]]


IDENTITY = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]


def rz(degrees):
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    return [[c, -s, 0], [s, c, 0], [0, 0, 1]]


def box(lo, hi, texture, faces=None, rotation=None, origin=None):
    """An element from lo to hi. texture covers every face; faces overrides some, e.g. {"south": "gauge"}.
    rotation is a 3x3 matrix applied about origin."""
    element = {"from": [round(v, 4) for v in lo], "to": [round(v, 4) for v in hi], "faces": {}}
    for direction in ("north", "south", "east", "west", "up", "down"):
        name = (faces or {}).get(direction, texture)
        element["faces"][direction] = {"uv": uv_of(name), "texture": "#interior"}
    if rotation is not None:
        x, y, z = euler_xyz(rotation)
        element["rotation"] = {"origin": [round(v, 4) for v in origin], "x": x, "y": y, "z": z}
    return element


def local(centre, rotation, lo, hi, texture, faces=None):
    """A box given relative to centre in a rotated frame."""
    return box([c + v for c, v in zip(centre, lo)], [c + v for c, v in zip(centre, hi)], texture, faces, rotation, centre)


def steering_wheel(centre, tilt, radius=1.25, unit=1.0, hub="hub", sporty=True, facing=IDENTITY):
    """Octagonal leather rim (blocky, like the car's tyres), three spokes, a hub with the logo, paddles and a column shroud.
    The wheel faces +z (the driver); tilt leans its top forward. unit scales the detail sizes (1 = sports car pixels).
    hub is the tile on the hub's face; sporty adds button pads and paddle shifters. facing turns the whole wheel
    (ry(180) for models whose driver looks toward -z)."""
    u = unit
    parts = []
    tilt_m = mat_mul(facing, rx(tilt))
    segments = 8
    length = 2 * radius * math.tan(math.pi / segments) + 0.18 * u
    for k in range(segments):
        r = mat_mul(tilt_m, rz(k * 360 / segments))
        parts.append(local(centre, r, [-length / 2, radius - 0.2 * u, -0.2 * u], [length / 2, radius + 0.2 * u, 0.2 * u], "leather",
                           {"south": "leather2"}))
    for angle, colour in [(90, "silver"), (-90, "silver"), (180, "rim")]:
        r = mat_mul(tilt_m, rz(angle))
        parts.append(local(centre, r, [-0.13 * u, 0.3 * u, -0.07 * u], [0.13 * u, radius - 0.12 * u, 0.07 * u], colour))
    for angle in (90, -90) if sporty else ():  # button pads on the side spokes
        r = mat_mul(tilt_m, rz(angle))
        parts.append(local(centre, r, [-0.22 * u, 0.45 * u, 0.06 * u], [0.22 * u, 0.85 * u, 0.1 * u], "plastic", {"south": "buttons"}))
    parts.append(local(centre, tilt_m, [-0.42 * u, -0.42 * u, -0.22 * u], [0.42 * u, 0.42 * u, 0.12 * u], "rim", {"south": hub}))
    parts.append(local(centre, tilt_m, [-0.28 * u, -0.28 * u, -1.6 * u], [0.28 * u, 0.28 * u, -0.22 * u], "plastic"))
    for side in (-1, 1) if sporty else ():  # paddle shifters behind the rim
        x = side * (radius - 0.2 * u)
        parts.append(local(centre, tilt_m, [x - 0.25 * u, 0.05 * u, -0.36 * u], [x + 0.25 * u, 0.65 * u, -0.3 * u], "silver"))
    return parts


def octagon(centre, flats, depth, texture, axis, faces=None):
    """A solid octagon, flats across, as four strips at 0, 45, 90 and 135 degrees about axis ("x" or "z")."""
    side = flats * math.tan(math.pi / 8)
    turn = rx if axis == "x" else rz
    if axis == "x":
        lo, hi = [-depth / 2, -side / 2, -flats / 2], [depth / 2, side / 2, flats / 2]
    else:
        lo, hi = [-flats / 2, -side / 2, -depth / 2], [flats / 2, side / 2, depth / 2]
    return [local(centre, turn(angle), lo, hi, texture, faces) for angle in (0, 45, 90, 135)]


def tyre(centre, radius, width):
    """A blocky octagonal wheel turning about x: rubber, a silver hub and a dark cap."""
    return (octagon(centre, radius * 1.85, width, "plastic", "x")
            + octagon(centre, radius * 0.95, width + 0.12 * radius, "silver", "x")
            + octagon(centre, radius * 0.35, width + 0.2 * radius, "black", "x"))


class Frame:
    """Converts a source model's coordinates (blocks, as in the glTF) to its converted model pixels."""

    def __init__(self, path, skip=()):
        gltf, accessor, _ = load(path)
        points = []
        self.groups = {}  # group name -> converted element indices inside it, counted like the converter does

        def visit(index, parent, names):
            node = gltf["nodes"][index]
            if node.get("name") in skip:
                return
            world = mat_mul(parent, node_matrix(node))
            names = names + [node.get("name")]
            if "mesh" in node:
                faces = faces_of(gltf, accessor, gltf["meshes"][node["mesh"]], world)
                points.extend(p for f in faces for p in f[0])
                count = 1 if len(faces) <= 6 else len(faces) // 6
                start = self.count
                self.count += count
                for name in names:
                    self.groups.setdefault(name, []).extend(range(start, start + count))
            for child in node.get("children", []):
                visit(child, world, names)

        self.count = 0
        for root in gltf["scenes"][gltf.get("scene", 0)]["nodes"]:
            visit(root, [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], [])
        lo = [min(p[k] for p in points) for k in range(3)]
        hi = [max(p[k] for p in points) for k in range(3)]
        self.px = FIT / max(hi[k] - lo[k] for k in range(3))
        self.mid = [(lo[k] + hi[k]) / 2 for k in range(3)]
        self.unit = self.px / SPORTS_CAR_PX

    def p(self, x, y, z):
        return [8 + (v - m) * self.px for v, m in zip((x, y, z), self.mid)]

    def d(self, length):
        return length * self.px


def gauges(centre, tilt, spacing, unit=1.0, facing=IDENTITY):
    """Two dials and a small digital readout, facing the driver, in a tilted frame."""
    r, u = mat_mul(facing, rx(tilt)), unit
    return [
        local(centre, r, [-spacing - 0.7 * u, -0.7 * u, 0], [-spacing + 0.7 * u, 0.7 * u, 0.05 * u], "black", {"south": "gauge"}),
        local(centre, r, [spacing - 0.7 * u, -0.7 * u, 0], [spacing + 0.7 * u, 0.7 * u, 0.05 * u], "black", {"south": "tacho"}),
        local(centre, r, [-0.35 * u, -0.45 * u, 0], [0.35 * u, 0.25 * u, 0.04 * u], "black", {"south": "digital"}),
    ]


def door_panel(x, inward, z0, z1, y_floor, y_top):
    """Trim on a door's inner face at x, facing inward (+1 faces +x)."""
    def xs(a, b):  # a..b measured inward from the door face
        lo, hi = x + inward * a, x + inward * b
        return min(lo, hi), max(lo, hi)
    face = "east" if inward > 0 else "west"
    parts = []
    a, b = xs(0, 0.06)
    parts.append(box([a, y_floor + 2.6, z0 + 1], [b, y_top - 1.0, z1 - 1], "leather2", {face: "doorpad"}))
    a, b = xs(0, 0.6)
    parts.append(box([a, y_floor + 3.9, z0 + 2.2], [b, y_floor + 4.25, z1 - 2.2], "leather", {"up": "stitch"}))
    a, b = xs(0.1, 0.5)
    parts.append(box([a, y_floor + 4.25, z0 + 2.4], [b, y_floor + 4.3, z0 + 3.6], "plastic", {"up": "buttons"}))
    a, b = xs(0, 0.22)
    parts.append(box([a, y_top - 1.9, z0 + 1.6], [b, y_top - 1.65, z0 + 2.6], "chrome"))
    a, b = xs(0, 0.04)
    parts.append(box([a, y_floor + 1.2, z0 + 1.5], [b, y_floor + 2.4, z0 + 3.5], "plastic", {face: "speaker"}))
    parts.append(box([a, y_top - 0.25, z0 + 0.5], [b, y_top - 0.1, z1 - 0.5], "chrome"))
    return parts


def sports_car():
    edits = {"remove": [92, 98, 125, 126], "add": [],
             "retexture": [retexture(52, "down", "headliner"), retexture(59, "down", "headliner")]
             + [retexture(97, "south", "plastic")]}
    add = edits["add"].extend
    # Steering wheel in front of the driver, leaning like the original column.
    add(steering_wheel([3.61, 9.45, 9.0], -22.5, 1.0))
    # Dials on the original cluster plate (element 98, z 7.47..8.02 in its own frame).
    add([local([3.61, 10.03, 8.02], rx(-22.5), [-1.65, -0.8, -0.2], [1.65, 0.8, 0], "plastic")])
    add(gauges([3.61, 10.03, 8.02], -22.5, 0.82))
    # Dashboard face (z = 5.87 faces the driver): screen, vents, trim, buttons.
    z = 5.87
    add([
        box([6.4, 8.45, z], [9.6, 10.35, z + 0.06], "black"),
        box([6.55, 8.6, z + 0.06], [9.45, 10.2, z + 0.08], "black", {"south": "screen"}),
        box([5.5, 9.1, z], [6.3, 10.1, z + 0.08], "silver", {"south": "vent"}),
        box([9.7, 9.1, z], [10.5, 10.1, z + 0.08], "silver", {"south": "vent"}),
        box([1.25, 9.0, z], [2.05, 10.0, z + 0.08], "silver", {"south": "vent"}),
        box([13.95, 9.0, z], [14.75, 10.0, z + 0.08], "silver", {"south": "vent"}),
        box([10.6, 8.85, z], [14.75, 8.97, z + 0.05], "silver"),
        box([10.6, 8.15, z], [13.8, 8.8, z + 0.04], "carbon", {"south": "carbon"}),
        box([5.0, 8.35, z], [5.35, 8.7, z + 0.12], "red"),
        box([7.85, 10.38, z], [8.15, 10.5, z + 0.08], "red"),
        box([1.14, 10.45, 2.1], [14.86, 10.6, 5.87], "leather"),
    ])
    # Climate panel and knobs on the console front, then the console top.
    add([
        box([6.4, 6.95, z], [9.6, 7.9, z + 0.05], "plastic", {"south": "buttons"}),
        box([6.6, 7.2, z + 0.05], [7.05, 7.65, z + 0.3], "silver"),
        box([8.95, 7.2, z + 0.05], [9.4, 7.65, z + 0.3], "silver"),
        box([7.55, 6.91, 6.5], [8.45, 7.15, 7.4], "leather", {"up": "stitch"}),
        box([7.93, 7.15, 6.87], [8.07, 8.1, 7.03], "chrome"),
        box([7.75, 8.1, 6.7], [8.25, 8.5, 7.2], "leather", {"up": "black"}),
        box([7.8, 6.91, 7.9], [8.2, 7.25, 8.9], "plastic"),
        box([7.85, 7.25, 7.95], [8.15, 7.32, 8.15], "silver"),
        box([6.5, 6.91, 9.05], [7.35, 6.95, 9.85], "silver", {"up": "black"}),
        box([8.65, 6.91, 9.05], [9.5, 6.95, 9.85], "silver", {"up": "black"}),
        box([6.2, 6.91, 10.0], [9.8, 7.5, 10.81], "leather", {"up": "stitch"}),
        box([6.08, 6.91, 5.87], [6.2, 6.98, 10.0], "silver"),
        box([9.8, 6.91, 5.87], [9.92, 6.98, 10.0], "silver"),
    ])
    # Pedals under the dash.
    add([box([2.5, 5.1, 2.03], [3.1, 5.9, 2.15], "silver"), box([3.6, 5.1, 2.03], [4.0, 6.1, 2.15], "silver")])
    # Door panels.
    add(door_panel(1.14, 1, 6.0, 15.0, 3.4, 10.53))
    add(door_panel(14.86, -1, 6.0, 15.0, 3.4, 10.53))
    # Seats: side bolsters and a red stripe, on the base and (in its leaning frame) the back.
    back_tilt = rx(22.5)
    for dx in (0, 8.78):
        add([
            box([1.69 + dx, 6.73, 9.0], [2.2 + dx, 7.15, 13.5], "leather2"),
            box([5.02 + dx, 6.73, 9.0], [5.53 + dx, 7.15, 13.5], "leather2"),
            box([3.4 + dx, 6.73, 9.0], [3.82 + dx, 6.76, 13.5], "red"),
        ])
        centre = [3.6094 + dx, 8.7142, 13.6682]
        add([
            local(centre, back_tilt, [-1.92, -2.6, -1.15], [-1.4, 2.4, -0.83], "leather2"),
            local(centre, back_tilt, [1.4, -2.6, -1.15], [1.92, 2.4, -0.83], "leather2"),
            local(centre, back_tilt, [-0.21, -2.6, -0.87], [0.21, 2.6, -0.83], "red"),
        ])
    # Rear-view mirror, headliner, dome light and sun visors.
    add([
        box([7.9, 13.0, 8.4], [8.1, 13.55, 8.6], "plastic"),
        box([6.7, 12.45, 8.4], [9.3, 13.05, 8.65], "black"),
        box([6.8, 12.52, 8.65], [9.2, 12.98, 8.67], "black", {"south": "mirror"}),
        box([7.4, 13.45, 10.0], [8.6, 13.55, 10.8], "headliner", {"down": "white"}),
        box([1.6, 13.1, 8.7], [5.3, 13.45, 9.7], "headliner"),
        box([10.7, 13.1, 8.7], [14.4, 13.45, 9.7], "headliner", {"down": "mirror"}),
    ])
    return edits


def mini():
    f = Frame(f"{INCOMING}/leyland-mini/source/model.gltf", {"tube", "cylinder"})
    # The original wheel's rim was a round mesh and its spokes are large; replace it with a smaller blocky one.
    edits = {"remove": f.groups["SteeringHeel"], "add": []}
    for x, z in [(1.08, -2.285), (1.08, 2.06), (-1.23, -2.28), (-1.23, 2.055)]:
        edits["add"].extend(tyre(f.p(x, 0.065, z), f.d(0.575), f.d(0.44)))
    edits["add"].extend(steering_wheel(f.p(-0.6, 0.98, -0.88), -20, f.d(0.3), f.unit, "chrome_hub", sporty=False))

    def b(lo, hi, texture, faces=None, rotation=None, origin=None):
        return box(f.p(*lo), f.p(*hi), texture, faces, rotation, origin and f.p(*origin))
    # Thicker seat cushions so the driver sits high enough to see out.
    edits["add"].extend([b((-1.11, 0.23, -0.82), (-0.17, 0.5, 0.18), "leather2"),
                         b((0.02, 0.23, -0.82), (1.02, 0.5, 0.18), "leather2")])
    z = -1.12  # the dashboard's face toward the driver
    edits["add"].extend([
        # The classic central speedo in an octagonal chrome bezel, with a small gauge either side.
        *octagon(f.p(-0.06, 0.95, z + 0.008), f.d(0.4), f.d(0.016), "chrome", "z"),
        b((-0.22, 0.79, z + 0.015), (0.10, 1.11, z + 0.025), "black", {"south": "classic_gauge"}),
        b((-0.45, 0.86, z), (-0.29, 1.02, z + 0.02), "chrome", {"south": "classic_small"}),
        b((0.17, 0.86, z), (0.33, 1.02, z + 0.02), "chrome", {"south": "classic_small"}),
        # Toggle switches, the ignition key and a chrome strip along the dash.
        *[b((x, 0.66, z), (x + 0.035, 0.7, z + 0.07), "chrome") for x in (-0.24, -0.14, -0.04, 0.06, 0.16)],
        b((-0.42, 0.68, z), (-0.36, 0.74, z + 0.05), "silver"),
        b((-1.16, 1.19, z), (1.03, 1.21, z + 0.02), "chrome"),
        # Rear-view mirror under the roof.
        b((-0.08, 1.9, -0.95), (-0.04, 2.0, -0.91), "plastic"),
        b((-0.26, 1.8, -0.93), (0.14, 1.9, -0.89), "black"),
        b((-0.24, 1.81, -0.89), (0.12, 1.89, -0.885), "black", {"south": "mirror"}),
        # Gear stick and handbrake between the seats.
        b((-0.1, -0.17, -1.05), (-0.02, 0.0, -0.97), "leather"),
        b((-0.075, 0.0, -1.025), (-0.045, 0.5, -0.995), "chrome"),
        b((-0.11, 0.5, -1.06), (-0.01, 0.6, -0.96), "black"),
        b((-0.09, -0.17, -0.3), (-0.03, 0.08, 0.05), "plastic"),
        b((-0.085, 0.08, -0.3), (-0.035, 0.1, -0.2), "silver"),
    ])
    for x, inward in ((-1.16, 1), (1.03, -1)):  # door pulls and window winders
        x0, x1 = sorted((x, x + inward * 0.06))
        edits["add"].extend([
            b((x0, 0.7, -0.75), (x1, 0.74, -0.35), "leather"),
            b((x0, 0.45, -0.25), (x1, 0.55, -0.15), "chrome"),
        ])
    return edits


def paint(texture):
    """A face painted with the interior texture, for cuts."""
    return {"uv": uv_of(texture), "texture": "#interior"}


def sedan_a():
    """Sprint's car is solid blocks, so the body and cabin are rebuilt hollow from pieces of the originals,
    with tinted glass, then fitted out. In model pixels (about 6.8 per block)."""
    u = 6.77 / SPORTS_CAR_PX
    X0, X1, Y0, Y1, Z0, Z1 = -0.6147, 16.6147, 0.9757, 9.7229, -1.1442, 21.5191  # body (element 0)
    floor, wall, dash_end = Y0 + 1.2, 0.6, 2.4
    cuts = [
        {"index": 0, "from": [X0, Y0, Z0], "to": [X1, floor, Z1], "faces": {"up": paint("carpet")}},
        {"index": 0, "from": [X0, floor, Z0], "to": [X0 + wall, Y1, Z1], "faces": {"east": paint("doorpad")}},
        {"index": 0, "from": [X1 - wall, floor, Z0], "to": [X1, Y1, Z1], "faces": {"west": paint("doorpad")}},
        {"index": 0, "from": [X0 + wall, floor, Z0], "to": [X1 - wall, Y1, dash_end], "faces": {"south": paint("plastic")}},
        {"index": 0, "from": [X0 + wall, floor, 15.5], "to": [X1 - wall, Y1, Z1], "faces": {"north": paint("leather2")}},
    ]
    # Cabin (element 1): the roof, and pillars between the side windows.
    cx0, cx1, cy0, cy1, cz0, cz1 = 0.048, 15.952, 9.5904, 15.687, 3.7596, 14.8924
    roof = cy1 - 0.7
    cuts.append({"index": 1, "from": [cx0, roof, cz0], "to": [cx1, cy1, cz1], "faces": {"down": paint("headliner")}})
    for x0, x1, inner in ((cx0, cx0 + 0.5, "east"), (cx1 - 0.5, cx1, "west")):
        cuts.append({"index": 1, "from": [x0, cy0, 8.6], "to": [x1, roof, 9.6], "faces": {inner: paint("plastic")}})
    # Windscreen (element 2) and rear window (element 3): keep their edges as pillars, glass in between.
    for index, (y0, z0), (y1, z1) in ((2, (7.3137, 1.1195), (15.2657, 5.0955)), (3, (8.5138, 11.9212), (13.02, 21.3311))):
        cuts.append({"index": index, "from": [0.1805, y0, z0], "to": [1.2, y1, z1]})
        cuts.append({"index": index, "from": [14.8, y0, z0], "to": [15.8195, y1, z1]})
    glass = []
    for origin, angle, (y0, z0), (y1, z1) in (((8.0, 11.2897, 3.1075), 35, (7.3137, 2.9), (15.2657, 3.3)),
                                               ((8.0, 10.7669, 16.6261), 45, (8.5138, 16.4), (13.02, 16.8))):
        glass.append(box([1.2, y0, z0], [14.8, y1, z1], "tint", rotation=rx(angle), origin=list(origin)))
    for x0, x1 in ((cx0, cx0 + 0.2), (cx1 - 0.2, cx1)):
        glass.append(box([x0, cy0, cz0], [x1, roof, 8.6], "tint"))
        glass.append(box([x0, cy0, 9.6], [x1, roof, cz1], "tint"))

    add = []
    seat_y = floor + 3.0  # cushion top, about 0.65 blocks up
    for x0, x1 in ((1.4, 7.0), (9.0, 14.6)):  # front seats: cushion, leaning back, headrest
        add.append(box([x0, floor, 8.2], [x1, seat_y, 12.0], "leather2"))
        add.append(box([x0, seat_y - 0.5, 12.0], [x1, seat_y + 7.4, 13.2], "leather2", rotation=rx(12),
                       origin=[(x0 + x1) / 2, seat_y, 12.6]))
        add.append(box([(x0 + x1) / 2 - 1.2, seat_y + 7.0, 12.9], [(x0 + x1) / 2 + 1.2, seat_y + 8.8, 14.0], "leather2",
                       rotation=rx(12), origin=[(x0 + x1) / 2, seat_y, 12.6]))
    add.append(box([X0 + wall, floor, 13.6], [X1 - wall, seat_y - 0.4, 15.5], "leather2"))  # rear bench
    # Dashboard face (z = dash_end, facing the driver): gauges, screen, vents, trim.
    z = dash_end
    add.extend(gauges([4.2, 8.6, z], 0, 0.95 * u, u))
    add.extend([
        box([3.0, 7.6, z], [5.4, 9.6, z + 0.03], "plastic"),
        box([6.9, 5.9, z], [9.1, 7.9, z + 0.06], "black", {"south": "screen"}),
        box([6.1, 6.6, z], [6.7, 7.5, z + 0.06], "silver", {"south": "vent"}),
        box([9.3, 6.6, z], [9.9, 7.5, z + 0.06], "silver", {"south": "vent"}),
        box([1.1, 7.2, z], [1.8, 8.1, z + 0.06], "silver", {"south": "vent"}),
        box([14.2, 7.2, z], [14.9, 8.1, z + 0.06], "silver", {"south": "vent"}),
        box([10.4, 6.9, z], [14.6, 7.0, z + 0.04], "silver"),
        box([0.0, Y1 - 0.05, Z0], [16.0, Y1 + 0.1, dash_end + 0.2], "darkgrey"),
    ])
    # Centre console with the gear stick between the seats.
    add.extend([
        box([7.3, floor, dash_end], [8.7, floor + 2.4, 11.0], "plastic"),
        box([7.3, floor + 2.4, 5.5], [8.7, floor + 2.5, 11.0], "silver"),
        box([7.85, floor + 2.5, 6.4], [8.15, floor + 3.6, 6.7], "chrome"),
        box([7.7, floor + 3.6, 6.25], [8.3, floor + 4.1, 6.85], "leather"),
    ])
    add.extend(steering_wheel([4.2, 7.6, 5.2], -22.5, 1.25, u))
    add.append(box([3.95, 6.6, dash_end], [4.45, 7.1, 3.8], "plastic"))  # column into the dash
    # Rear-view mirror, door handles and sun visors.
    add.extend([
        box([7.85, roof - 0.6, 5.0], [8.15, roof, 5.2], "plastic"),
        box([6.8, roof - 1.2, 5.0], [9.2, roof - 0.6, 5.25], "black"),
        box([6.9, roof - 1.15, 5.25], [9.1, roof - 0.65, 5.27], "black", {"south": "mirror"}),
        box([1.2, roof - 0.35, 4.2], [6.8, roof, 5.6], "headliner"),
        box([9.2, roof - 0.35, 4.2], [14.8, roof, 5.6], "headliner"),
    ])
    for x, inward in ((X0 + wall, 1), (X1 - wall, -1)):
        x0, x1 = sorted((x, x + inward * 0.5))
        add.extend([
            box([x0, floor + 3.6, 6.0], [x1, floor + 3.95, 11.5], "leather", {"up": "stitch"}),
            box([min(x, x + inward * 0.2), floor + 5.6, 5.0], [max(x, x + inward * 0.2), floor + 5.9, 6.2], "chrome"),
        ])
    return {"remove": [0, 1, 2, 3], "cuts": cuts, "add": glass + add}


def truck():
    """The Kenworth's cab is solid blocks; hollow it, glaze it and fit it out. The model faces +z, so the driver
    (on the left) sits on the +x side. In model pixels (about 2.9 per block at 15 blocks long)."""
    u = (FIT / 15) / SPORTS_CAR_PX
    turn = ry(180)
    x0, x1, z_back, z_dash = 4.23, 11.76, 19.56, 22.4
    floor, wall = 8.35, 0.22
    cuts = [
        {"index": 25, "from": [x0, 8.0, z_back], "to": [x1, floor, 23.33], "faces": {"up": paint("carpet")}},
        {"index": 25, "from": [x0 + wall, floor, z_dash], "to": [x1 - wall, 10.51, 23.33],
         "faces": {"north": paint("plastic"), "up": paint("plastic")}},
    ]
    for index, (y0, y1), z1 in ((25, (floor, 10.51), 23.33), (26, (10.51, 11.45), 22.07)):
        cuts.append({"index": index, "from": [x0, y0, z_back], "to": [x0 + wall, y1, z1], "faces": {"east": paint("doorpad")}})
        cuts.append({"index": index, "from": [x1 - wall, y0, z_back], "to": [x1, y1, z1], "faces": {"west": paint("doorpad")}})
    for index, (y0, y1) in ((25, (floor, 10.51)), (26, (10.51, 11.45)), (31, (11.45, 12.39)), (32, (12.39, 13.33))):
        cuts.append({"index": index, "from": [x0 + wall, y0, z_back], "to": [x1 - wall, y1, z_back + 0.24],
                     "faces": {"south": paint("plastic")}})
    # Faces the original never showed (inside the pillars, dash lip and cowl) get plain trim.
    retextures = [retexture(117, "down", "headliner"), retexture(118, "down", "headliner"), retexture(27, "north", "plastic"),
                  retexture(35, "east", "plastic"), retexture(35, "north", "plastic"), retexture(71, "west", "plastic"),
                  retexture(71, "north", "plastic"), retexture(24, "up", "plastic"), retexture(24, "north", "plastic"),
                  retexture(33, "north", "plastic"), retexture(27, "up", "plastic"), retexture(33, "up", "plastic")]
    glass = [
        box([4.55, 10.25, 22.79], [11.45, 13.08, 23.11], "tint", rotation=rx(-10), origin=[8.0, 11.665, 22.95]),
        box([x0, 11.45, z_back + 0.24], [x0 + 0.1, 13.33, 22.07], "tint"),
        box([x1 - 0.1, 11.45, z_back + 0.24], [x1, 13.33, 22.07], "tint"),
    ]
    add = []
    cushion = floor + 1.3
    for sx0, sx1 in ((9.0, 10.9), (5.1, 7.0)):  # driver (left, +x) and passenger seats
        add.append(box([sx0, floor, z_back + 0.3], [sx1, cushion, 21.3], "leather2"))
        add.append(box([sx0, cushion - 0.2, z_back + 0.24], [sx1, cushion + 2.6, z_back + 0.6], "leather2",
                       rotation=rx(-8), origin=[(sx0 + sx1) / 2, cushion, z_back + 0.4]))
    add.extend(steering_wheel([9.95, 10.3, 21.45], -50, 0.65, u, sporty=False, facing=turn))
    add.extend(gauges([9.95, 10.98, 22.07], 0, 0.95 * 0.6 * u, 0.6 * u, facing=turn))  # on the cowl above the dash
    add.extend([
        *[box([x, 9.0, z_dash - 0.12], [x + 0.12, 9.12, z_dash], "chrome") for x in (6.2, 6.6, 7.0, 7.4)],
        box([5.2, 9.6, z_dash - 0.03], [7.6, 10.3, z_dash], "silver", {"north": "vent"}),
        box([7.8, floor, 20.9], [8.3, floor + 0.3, 21.4], "leather"),
        box([7.98, floor + 0.3, 21.08], [8.12, 10.6, 21.22], "chrome"),
        box([7.88, 10.6, 20.98], [8.22, 10.95, 21.32], "black"),
        box([x0 + wall, floor + 1.9, 20.3], [x0 + wall + 0.25, floor + 2.05, 21.9], "leather"),
        box([x1 - wall - 0.25, floor + 1.9, 20.3], [x1 - wall, floor + 2.05, 21.9], "leather"),
    ])
    return {"remove": [25, 26, 28, 29, 30, 31, 32, 34], "cuts": cuts, "retexture": retextures, "add": glass + add}


def helicopter():
    """The cockpit is already hollow and fitted; add the pilot's controls. In the source's pixels (16 per block)."""
    f = Frame(f"{INCOMING}/helicopter/source/model.gltf", {"propeller"})

    def b(lo, hi, texture):
        return box(f.p(*lo), f.p(*hi), texture)
    return {"remove": [], "add": [
        b((-10.2, 11, -11.2), (-7.8, 12, -8.8), "leather"),  # cyclic boot, stick and grip
        b((-9.3, 12, -10.3), (-8.7, 19, -9.7), "black"),
        b((-9.7, 19, -10.7), (-8.3, 21.2, -9.3), "rim"),
        b((-14.4, 12.6, -8.0), (-13.4, 13.4, 0.0), "black"),  # collective lever and grip
        b((-14.6, 12.4, -9.6), (-13.2, 13.6, -8.0), "rim"),
        b((-12.4, 10.5, -16.4), (-10.6, 12.6, -15.9), "silver"),  # pedals
        b((-7.4, 10.5, -16.4), (-5.6, 12.6, -15.9), "silver"),
    ]}


LAYOUTS = {"sports_car": sports_car, "mini": mini, "sedan_a": sedan_a, "truck": truck, "helicopter": helicopter}


def main():
    name = sys.argv[1]
    edits = LAYOUTS[name]()
    edits["textures"] = {"interior": TEXTURE}
    os.makedirs(os.path.join(os.path.dirname(__file__), "edits"), exist_ok=True)
    json.dump(edits, open(os.path.join(os.path.dirname(__file__), "edits", f"{name}.json"), "w"), indent=1)
    draw_texture("assets/vexel/textures/item/vehicle/interior.png")
    print(f"{name}: removed {len(edits['remove'])}, added {len(edits['add'])}")


if __name__ == "__main__":
    main()
