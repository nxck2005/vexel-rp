#!/usr/bin/env python3
"""Converts a glTF made of boxes (as Blockbench exports, including Sketchfab re-exports) into a Java item model.

    gltf_to_model.py <model.gltf> <name> <length-in-blocks> [--skip-nodes NAME,...]

Writes assets/vexel/models/item/vehicle/<name>.json, its textures and assets/vexel/items/<name>.json, then prints
the model-scale and model-offset that make the model <length-in-blocks> long, sitting on y=0 and centred on x/z.
Run from the pack root. Uses only the standard library.
"""
import base64
import json
import math
import os
import struct
import sys

# Vertex order of each face, from net.minecraft.client.renderer.FaceInfo (26.2). 0 = min, 1 = max per axis.
FACE_VERTICES = {
    "down": [(0, 0, 1), (0, 0, 0), (1, 0, 0), (1, 0, 1)],
    "up": [(0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)],
    "north": [(1, 1, 0), (1, 0, 0), (0, 0, 0), (0, 1, 0)],
    "south": [(0, 1, 1), (0, 0, 1), (1, 0, 1), (1, 1, 1)],
    "west": [(0, 1, 0), (0, 0, 0), (0, 0, 1), (0, 1, 1)],
    "east": [(1, 1, 1), (1, 0, 1), (1, 0, 0), (1, 1, 0)],
}
DIRECTIONS = {(0, -1, 0): "down", (0, 1, 0): "up", (0, 0, -1): "north", (0, 0, 1): "south", (-1, 0, 0): "west", (1, 0, 0): "east"}
# The model is fitted inside the allowed -16..32 element range with this margin, in model pixels.
FIT = 44.0


def mat_mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(len(b))) for j in range(len(b[0]))] for i in range(len(a))]


def transpose(m):
    return [list(r) for r in zip(*m)]


def apply(m, v):
    return [sum(m[i][k] * v[k] for k in range(3)) for i in range(3)]


def node_matrix(node):
    if "matrix" in node:
        m = node["matrix"]  # column-major
        return [[m[c * 4 + r] for c in range(4)] for r in range(4)]
    x, y, z, w = node.get("rotation", [0, 0, 0, 1])
    r = [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
         [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
         [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]
    s = node.get("scale", [1, 1, 1])
    t = node.get("translation", [0, 0, 0])
    return [[r[i][0] * s[0], r[i][1] * s[1], r[i][2] * s[2], t[i]] for i in range(3)] + [[0, 0, 0, 1]]


def load(path):
    gltf = json.load(open(path))
    base = os.path.dirname(path)
    buffers = []
    for buffer in gltf["buffers"]:
        uri = buffer["uri"]
        buffers.append(base64.b64decode(uri.split(",", 1)[1]) if uri.startswith("data:") else open(os.path.join(base, uri), "rb").read())

    def accessor(index):
        a = gltf["accessors"][index]
        view = gltf["bufferViews"][a["bufferView"]]
        data = buffers[view["buffer"]]
        offset = view.get("byteOffset", 0) + a.get("byteOffset", 0)
        n = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[a["type"]]
        fmt = {5126: "f", 5123: "H", 5125: "I", 5121: "B"}[a["componentType"]]
        stride = view.get("byteStride", struct.calcsize(fmt) * n)
        return [struct.unpack_from("<" + fmt * n, data, offset + k * stride) for k in range(a["count"])]

    def image(index):
        img = gltf["images"][index]
        if "uri" in img:
            uri = img["uri"]
            return base64.b64decode(uri.split(",", 1)[1]) if uri.startswith("data:") else open(os.path.join(base, uri), "rb").read()
        view = gltf["bufferViews"][img["bufferView"]]
        start = view.get("byteOffset", 0)
        return buffers[view["buffer"]][start:start + view["byteLength"]]

    return gltf, accessor, image


def faces_of(gltf, accessor, mesh, world):
    """Quads (corners, uvs, normal, material) in model order, from consecutive triangle pairs."""
    rotation = [row[:3] for row in world[:3]]
    faces = []
    for primitive in mesh["primitives"]:
        positions = accessor(primitive["attributes"]["POSITION"])
        normals = accessor(primitive["attributes"]["NORMAL"])
        uvs = accessor(primitive["attributes"]["TEXCOORD_0"])
        indices = [i[0] for i in accessor(primitive["indices"])] if "indices" in primitive else list(range(len(positions)))
        for t in range(0, len(indices), 6):
            # Some exporters repeat shared corners as separate vertices, so match corners by position and uv.
            corners = list({(tuple(round(c, 5) for c in positions[i]), tuple(round(c, 5) for c in uvs[i])): i
                            for i in indices[t:t + 6]}.values())
            if len(corners) != 4:
                sys.exit(f"Triangles {t // 3} and {t // 3 + 1} don't make a quad")
            points = [[c + world[k][3] for k, c in enumerate(apply(world, positions[i]))] for i in corners]
            normal = apply(rotation, [sum(normals[i][k] for i in corners) for k in range(3)])
            length = math.sqrt(sum(c * c for c in normal))
            faces.append(([p[:3] for p in points], [uvs[i] for i in corners], [c / length for c in normal], primitive.get("material", 0)))
    return faces


def proper_rotations():
    """The 24 rotations that map axes onto axes."""
    result = []
    for perm in [(0, 1, 2), (0, 2, 1), (1, 0, 2), (1, 2, 0), (2, 0, 1), (2, 1, 0)]:
        for signs in [(a, b, c) for a in (1, -1) for b in (1, -1) for c in (1, -1)]:
            m = [[0] * 3 for _ in range(3)]
            for col, row in enumerate(perm):
                m[row][col] = signs[col]
            det = (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
                   + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))
            if det == 1:
                result.append(m)
    return result


ROTATIONS = proper_rotations()


def box_rotation(faces):
    """The rotation closest to none whose axes line up with the box's face normals."""
    a = faces[0][2]
    b = next(f[2] for f in faces if abs(sum(x * y for x, y in zip(a, f[2]))) < 0.01)
    c = [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]
    frame = transpose([a, b, c])
    return max((mat_mul(frame, p) for p in ROTATIONS), key=lambda r: r[0][0] + r[1][1] + r[2][2])


def euler_xyz(r):
    """Angles for Minecraft's x/y/z element rotation, which applies rotationZYX: R = Rz * Ry * Rx."""
    y = math.asin(max(-1, min(1, -r[2][0])))
    x = math.atan2(r[2][1], r[2][2])
    z = math.atan2(r[1][0], r[0][0])
    return [round(math.degrees(v), 4) for v in (x, y, z)]


def face_uv(direction, corners, uvs, low, high, size):
    """Minecraft uv [u1, v1, u2, v2] and rotation that put the source texture corners on this face."""
    targets = [[(high if pick else low)[k] for k, pick in enumerate(v)] for v in FACE_VERTICES[direction]]
    span = max(h - l for l, h in zip(low, high)) or 1
    vertex_uv = []
    for target in targets:
        nearest = min(range(4), key=lambda i: sum((corners[i][k] - target[k]) ** 2 for k in range(3)))
        vertex_uv.append((uvs[nearest][0] * 16, uvs[nearest][1] * 16))
    for shift in range(4):
        by_index = {(v + shift) % 4: vertex_uv[v] for v in range(4)}
        u1, v1 = by_index[0]
        u2, v2 = by_index[2]
        if all(abs(a - b) < 1e-3 for a, b in [(by_index[1][0], u1), (by_index[1][1], v2), (by_index[3][0], u2), (by_index[3][1], v1)]):
            return [round(u1, 4), round(v1, 4), round(u2, 4), round(v2, 4)], shift * 90
    sys.exit(f"No uv mapping fits a {direction} face of size {span}")


def main():
    args = sys.argv[1:]
    skip = set()
    if "--skip-nodes" in args:
        i = args.index("--skip-nodes")
        skip = set(args[i + 1].split(","))
        del args[i:i + 2]
    path, name, length = args[0], args[1], float(args[2])
    gltf, accessor, image = load(path)

    cubes = []

    def visit(index, parent):
        node = gltf["nodes"][index]
        if node.get("name") in skip:
            return
        world = mat_mul(parent, node_matrix(node))
        if "mesh" in node:
            faces = faces_of(gltf, accessor, gltf["meshes"][node["mesh"]], world)
            if len(faces) % 6:
                sys.exit(f"Node {node.get('name')} has {len(faces)} faces, not whole boxes")
            cubes.extend(faces[i:i + 6] for i in range(0, len(faces), 6))
        for child in node.get("children", []):
            visit(child, world)

    identity = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    for root in gltf["scenes"][gltf.get("scene", 0)]["nodes"]:
        visit(root, identity)

    # Each box: centre, rotation, half extents and faces in its own frame.
    boxes = []
    for faces in cubes:
        points = [p for f in faces for p in f[0]]
        centre = [sum(p[k] for p in points) / len(points) for k in range(3)]
        r = box_rotation(faces)
        rt = transpose(r)
        local = [[apply(rt, [p[k] - centre[k] for k in range(3)]) for p in f[0]] for f in faces]
        low = [min(p[k] for c in local for p in c) for k in range(3)]
        high = [max(p[k] for c in local for p in c) for k in range(3)]
        boxes.append((centre, r, low, high, faces, local))

    all_points = [p for b in boxes for f in b[4] for p in f[0]]
    lo = [min(p[k] for p in all_points) for k in range(3)]
    hi = [max(p[k] for p in all_points) for k in range(3)]
    extent = max(hi[k] - lo[k] for k in range(3))
    scale = FIT / extent  # model pixels per source unit
    middle = [(lo[k] + hi[k]) / 2 for k in range(3)]

    def to_model(v):
        return [8 + (v[k] - middle[k]) * scale for k in range(3)]

    textures = {}
    elements = []
    for centre, r, low, high, faces, local in boxes:
        origin = to_model(centre)
        element = {
            "from": [round(origin[k] + low[k] * scale, 4) for k in range(3)],
            "to": [round(origin[k] + high[k] * scale, 4) for k in range(3)],
            "faces": {},
        }
        angles = euler_xyz(r)
        if any(abs(a) > 1e-3 for a in angles):
            element["rotation"] = {"origin": [round(c, 4) for c in origin], "x": angles[0], "y": angles[1], "z": angles[2]}
        for (corners, uvs, normal, material), corners_local in zip(faces, local):
            d = apply(transpose(r), normal)
            axis = max(range(3), key=lambda k: abs(d[k]))
            key = tuple((1 if d[axis] > 0 else -1) if k == axis else 0 for k in range(3))
            direction = DIRECTIONS[key]
            uv, rotation = face_uv(direction, corners_local, uvs, low, high, scale)
            texture = gltf["materials"][material]["pbrMetallicRoughness"]["baseColorTexture"]["index"]
            textures.setdefault(texture, f"vexel:item/vehicle/{name}_{len(textures)}")
            face = {"uv": uv, "texture": f"#{list(textures).index(texture)}"}
            if rotation:
                face["rotation"] = rotation
            element["faces"][direction] = face
        for k in range(3):
            if not -16 <= element["from"][k] <= 32 or not -16 <= element["to"][k] <= 32:
                sys.exit(f"Element outside -16..32: {element}")
        elements.append(element)

    model_path = f"assets/vexel/models/item/vehicle/{name}.json"
    texture_dir = "assets/vexel/textures/item/vehicle"
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    os.makedirs(texture_dir, exist_ok=True)
    os.makedirs("assets/vexel/items", exist_ok=True)
    for i, (texture, key) in enumerate(textures.items()):
        source = gltf["textures"][texture]["source"]
        open(f"{texture_dir}/{name}_{i}.png", "wb").write(image(source))
    # The model fills about FIT pixels, so shrink it to fit an inventory slot (16 pixels) when shown as an icon.
    icon_scale = round(15 / FIT, 4)
    model = {"textures": {str(i): key for i, key in enumerate(textures.values())}, "elements": elements,
             "display": {"gui": {"rotation": [30, 225, 0], "scale": [icon_scale] * 3}}}
    model["textures"]["particle"] = list(textures.values())[0]
    json.dump(model, open(model_path, "w"), indent=1)
    json.dump({"model": {"type": "minecraft:model", "model": f"vexel:item/vehicle/{name}"}}, open(f"assets/vexel/items/{name}.json", "w"), indent=2)

    # An item display draws model pixel p at (p / 16 - 0.5) blocks. Scale so the longest horizontal side is
    # <length> blocks, then shift so the model sits on y=0, centred on x and z.
    horizontal = max(hi[0] - lo[0], hi[2] - lo[2])
    blocks_per_unit = length / horizontal
    model_scale = blocks_per_unit * 16 / scale
    bottom = to_model(lo)[1] / 16 - 0.5
    offset = [0.0, -bottom * model_scale, 0.0]
    print(f"{name}: {len(elements)} boxes, {len(textures)} texture(s)")
    print(f"  size in blocks: x {(hi[0] - lo[0]) * blocks_per_unit:.2f}, y {(hi[1] - lo[1]) * blocks_per_unit:.2f}, z {(hi[2] - lo[2]) * blocks_per_unit:.2f}")
    print(f"  model-scale: {model_scale:.4f}")
    print(f"  model-offset: [{offset[0]:.4f}, {offset[1]:.4f}, {offset[2]:.4f}]")


if __name__ == "__main__":
    main()
