#!/usr/bin/env python3
"""Converts any glTF made of flat faces (not just boxes) into a Java item model, by baking each flat part's texture.

    bake_model.py <model.gltf> <name> <length-in-blocks>

gltf_to_model.py needs a model made of whole boxes. Exports whose faces were merged into many-sided shapes (Sketchfab's
OBJ cleaner does this) or that have round or slanted parts can't be split into boxes, so this tool takes each flat,
connected part of the model, paints the source texture onto it in one new texture, and makes it a flat element with
just that face. Pixels outside the part's shape are transparent, so wheels stay round and cut corners stay angled.

Writes assets/vexel/models/item/vehicle/<name>.json, its texture and assets/vexel/items/<name>.json, and prints the
model-scale and model-offset like gltf_to_model.py. Run from the pack root. Needs Pillow.
"""
import io
import json
import math
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gltf_to_model import FIT, apply, euler_xyz, load, mat_mul, node_matrix  # noqa: E402


def sub(a, b):
    return [x - y for x, y in zip(a, b)]


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def unit(a):
    length = math.sqrt(dot(a, a))
    return [x / length for x in a]


def triangles(gltf, accessor):
    """Every triangle: (corners, uvs, outward normal, texture index), in model space."""
    result = []

    def visit(index, parent):
        node = gltf["nodes"][index]
        world = mat_mul(parent, node_matrix(node))
        rotation = [row[:3] for row in world[:3]]
        for primitive in gltf["meshes"][node["mesh"]]["primitives"] if "mesh" in node else []:
            positions = accessor(primitive["attributes"]["POSITION"])
            normals = accessor(primitive["attributes"]["NORMAL"])
            uvs = accessor(primitive["attributes"]["TEXCOORD_0"])
            material = gltf["materials"][primitive.get("material", 0)]
            texture = material["pbrMetallicRoughness"]["baseColorTexture"]["index"]
            indices = [i[0] for i in accessor(primitive["indices"])] if "indices" in primitive else list(range(len(positions)))
            for t in range(0, len(indices), 3):
                corner = indices[t:t + 3]
                points = [[c + world[k][3] for k, c in enumerate(apply(world, positions[i]))] for i in corner]
                normal = cross(sub(points[1], points[0]), sub(points[2], points[0]))
                if dot(normal, normal) < 1e-14:
                    continue
                normal = unit(normal)
                # The winding decides the face's side; the vertex normals say which side is out.
                if dot(normal, apply(rotation, [sum(normals[i][k] for i in corner) for k in range(3)])) < 0:
                    normal = [-x for x in normal]
                result.append((points, [uvs[i] for i in corner], normal, texture))
        for child in node.get("children", []):
            visit(child, world)

    identity = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    for root in gltf["scenes"][gltf.get("scene", 0)]["nodes"]:
        visit(root, identity)
    return result


def flat_parts(tris):
    """Groups triangles into flat parts: same plane, facing the same way, and touching."""
    planes = []  # (normal, offset, [triangle indices])
    for i, (points, _, normal, _) in enumerate(tris):
        offset = dot(normal, points[0])
        plane = next((p for p in planes if dot(p[0], normal) > 0.9995 and abs(p[1] - offset) < 1e-4), None)
        if plane is None:
            planes.append((normal, offset, [i]))
        else:
            plane[2].append(i)
    parts = []
    for normal, offset, members in planes:
        # Split each plane into pieces that share corners, so far apart pieces don't share one big texture.
        group = {i: i for i in members}

        def find(i):
            while group[i] != i:
                group[i] = group[group[i]]
                i = group[i]
            return i

        owner = {}
        for i in members:
            for point in tris[i][0]:
                key = tuple(round(c, 5) for c in point)
                if key in owner:
                    group[find(i)] = find(owner[key])
                else:
                    owner[key] = i
        pieces = {}
        for i in members:
            pieces.setdefault(find(i), []).append(i)
        parts.extend((normal, offset, piece) for piece in pieces.values())
    return parts


def frame_of(normal, points):
    """Axes (u, n, v) for a flat part: world axes when it faces along one, else u along its longest edge."""
    for axis in ([1, 0, 0], [0, 0, 1], [0, 1, 0]):
        u = sub(axis, [dot(axis, normal) * n for n in normal])
        if dot(u, u) > 0.999:  # the part faces along a world axis other than this one
            u = unit(u)
            return u, normal, cross(u, normal)
    edges = [sub(q, p) for p, q in zip(points, points[1:] + points[:1])]
    u = unit(max(edges, key=lambda e: dot(e, e)))
    u = unit(sub(u, [dot(u, normal) * n for n in normal]))
    return u, normal, cross(u, normal)


def angles(r):
    """Minecraft's x/y/z element rotation for r, also when y is +-90 degrees, where euler_xyz can't tell x from z."""
    if abs(r[2][0]) < 0.99999:
        return euler_xyz(r)
    # With y at +-90 only x - z (or x + z) matters, so z is 0 and x carries the turn.
    return [round(math.degrees(math.atan2(-r[1][2], r[1][1])), 4), -90.0 if r[2][0] > 0 else 90.0, 0.0]


def main():
    path, name, length = sys.argv[1], sys.argv[2], float(sys.argv[3])
    gltf, accessor, image = load(path)
    images = {}
    tris = triangles(gltf, accessor)
    for _, _, _, texture in tris:
        if texture not in images:
            images[texture] = Image.open(io.BytesIO(image(gltf["textures"][texture]["source"]))).convert("RGBA")

    # Texture pixels per model unit, from how the source texture is spread over the model, so baked parts keep its
    # pixel size.
    densities = []
    for points, uvs, _, texture in tris:
        area = math.sqrt(dot(c := cross(sub(points[1], points[0]), sub(points[2], points[0])), c)) / 2
        w, h = images[texture].size
        uv_area = abs((uvs[1][0] - uvs[0][0]) * (uvs[2][1] - uvs[0][1]) - (uvs[2][0] - uvs[0][0]) * (uvs[1][1] - uvs[0][1])) / 2 * w * h
        if area > 1e-9 and uv_area > 0:
            densities.append(math.sqrt(uv_area / area))
    density = sorted(densities)[len(densities) // 2]

    patches = []  # (frame, plane offset, low u, low v, size u, size v, image)
    for normal, offset, members in flat_parts(tris):
        u, n, v = frame_of(normal, tris[members[0]][0])
        flat = [[(dot(p, u), dot(p, v)) for p in tris[i][0]] for i in members]
        low_u, low_v = min(a for f in flat for a, _ in f), min(b for f in flat for _, b in f)
        size_u = max(a for f in flat for a, _ in f) - low_u
        size_v = max(b for f in flat for _, b in f) - low_v
        # The pixel grid is stretched a little to fit the part exactly, so rectangles fill their pixels with no fringe.
        width, height = max(1, round(size_u * density)), max(1, round(size_v * density))
        if width * height <= 16:
            # Tiny parts (facets of round shapes) would miss every pixel centre, so they get a finer grid.
            fine = min(8, math.ceil(8 / min(width, height)))
            width, height = width * fine, height * fine
        patch = Image.new("RGBA", (width, height))
        pixels = patch.load()
        for i, f in zip(members, flat):
            uvs, source = tris[i][1], images[tris[i][3]]
            sw, sh = source.size
            src = source.load()
            (a0, b0), (a1, b1), (a2, b2) = [((a - low_u) / size_u * width, (b - low_v) / size_v * height) for a, b in f]
            det = (b1 - b2) * (a0 - a2) + (a2 - a1) * (b0 - b2)
            if abs(det) < 1e-12:
                continue
            for py in range(max(0, int(min(b0, b1, b2)) - 1), min(height, int(max(b0, b1, b2)) + 2)):
                for px in range(max(0, int(min(a0, a1, a2)) - 1), min(width, int(max(a0, a1, a2)) + 2)):
                    x, y = px + 0.5, py + 0.5
                    w0 = ((b1 - b2) * (x - a2) + (a2 - a1) * (y - b2)) / det
                    w1 = ((b2 - b0) * (x - a2) + (a0 - a2) * (y - b2)) / det
                    w2 = 1 - w0 - w1
                    # A pixel belongs to the triangle its centre is in (a little leeway keeps one pixel wide parts).
                    if pixels[px, py][3] or min(w0, w1, w2) < -0.02:
                        continue
                    w0, w1, w2 = (max(0.0, w) for w in (w0, w1, w2))
                    total = w0 + w1 + w2
                    tu = (w0 * uvs[0][0] + w1 * uvs[1][0] + w2 * uvs[2][0]) / total
                    tv = (w0 * uvs[0][1] + w1 * uvs[1][1] + w2 * uvs[2][1]) / total
                    colour = src[min(sw - 1, max(0, int(tu * sw))), min(sh - 1, max(0, int(tv * sh)))]
                    if colour[3]:
                        pixels[px, py] = colour
        patches.append(((u, n, v), offset, low_u, low_v, size_u, size_v, patch))

    # Pack the patches into one square texture, tallest first in rows, with a pixel between them.
    patches.sort(key=lambda p: -p[-1].height)
    size = 64
    while True:
        places, x, y, row = [], 1, 1, 0
        for *_, patch in patches:
            if x + patch.width + 1 > size:
                x, y, row = 1, y + row + 1, 0
            places.append((x, y))
            x, row = x + patch.width + 1, max(row, patch.height)
        if y + row + 1 <= size and all(patch.width + 2 <= size for *_, patch in patches):
            break
        size *= 2
    atlas = Image.new("RGBA", (size, size))
    for (*_, patch), place in zip(patches, places):
        atlas.paste(patch, place)

    all_points = [p for t in tris for p in t[0]]
    lo = [min(p[k] for p in all_points) for k in range(3)]
    hi = [max(p[k] for p in all_points) for k in range(3)]
    scale = FIT / max(hi[k] - lo[k] for k in range(3))  # model pixels per source unit
    middle = [(lo[k] + hi[k]) / 2 for k in range(3)]

    def to_model(point):
        return [8 + (point[k] - middle[k]) * scale for k in range(3)]

    texture_key = f"vexel:item/vehicle/{name}_0"
    elements = []
    for ((u, n, v), offset, low_u, low_v, size_u, size_v, patch), (x, y) in zip(patches, places):
        half_u, half_v = size_u / 2, size_v / 2
        # The element is flat, with only its top face, in the part's own axes: x along u, y along the normal, z along v.
        centre = [(low_u + half_u) * u[k] + offset * n[k] + (low_v + half_v) * v[k] for k in range(3)]
        origin = to_model(centre)
        element = {
            "from": [round(origin[0] - half_u * scale, 4), round(origin[1], 4), round(origin[2] - half_v * scale, 4)],
            "to": [round(origin[0] + half_u * scale, 4), round(origin[1], 4), round(origin[2] + half_v * scale, 4)],
            "faces": {"up": {"uv": [round(c, 4) for c in (x / size * 16, y / size * 16, (x + patch.width) / size * 16,
                                                           (y + patch.height) / size * 16)], "texture": "#0"}},
        }
        turn = angles([[u[r], n[r], v[r]] for r in range(3)])
        if any(abs(a) > 1e-3 for a in turn):
            element["rotation"] = {"origin": [round(c, 4) for c in origin], "x": turn[0], "y": turn[1], "z": turn[2]}
        elements.append(element)

    model_path = f"assets/vexel/models/item/vehicle/{name}.json"
    texture_dir = "assets/vexel/textures/item/vehicle"
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    os.makedirs(texture_dir, exist_ok=True)
    os.makedirs("assets/vexel/items", exist_ok=True)
    atlas.save(f"{texture_dir}/{name}_0.png")
    model = {"textures": {"0": texture_key, "particle": texture_key}, "elements": elements,
             "display": {"gui": {"rotation": [30, 225, 0], "scale": [round(15 / FIT, 4)] * 3}}}
    json.dump(model, open(model_path, "w"), indent=1)
    json.dump({"model": {"type": "minecraft:model", "model": f"vexel:item/vehicle/{name}"}}, open(f"assets/vexel/items/{name}.json", "w"), indent=2)

    # Same scale and offset as gltf_to_model.py: the longest horizontal side is <length> blocks, sitting on y=0.
    horizontal = max(hi[0] - lo[0], hi[2] - lo[2])
    blocks_per_unit = length / horizontal
    model_scale = blocks_per_unit * 16 / scale
    bottom = to_model(lo)[1] / 16 - 0.5
    print(f"{name}: {len(elements)} flat parts, {size}x{size} texture, {density:.0f} pixels per unit")
    print(f"  size in blocks: x {(hi[0] - lo[0]) * blocks_per_unit:.2f}, y {(hi[1] - lo[1]) * blocks_per_unit:.2f}, z {(hi[2] - lo[2]) * blocks_per_unit:.2f}")
    print(f"  model-scale: {model_scale:.4f}")
    print(f"  model-offset: [0.0000, {-bottom * model_scale:.4f}, 0.0000]")


if __name__ == "__main__":
    main()
