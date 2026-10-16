#!/usr/bin/env python3
"""Moves a vehicle model's see-through faces into their own model, vexel:<name>_glass.

    glass.py <name> [<name> ...]

If any face of an item model is see-through (a pixel it uses has alpha between 0 and 255), the game draws the whole
model after the solid ones. Shader packs (Iris) light the world before that, so the solid faces never show and only
the glass and the shadow are left. With the see-through faces in a model of their own, the body stays solid and the
glass is drawn on its own display. CityLifeCore shows it from the model's `glass` setting.
gltf_to_model.py runs this after converting. Run from the pack root. Needs Pillow.
"""
import json
import math
import sys

from PIL import Image

MODELS = "assets/vexel/models/item/vehicle"


def texture_path(key):
    namespace, path = key.split(":") if ":" in key else ("minecraft", key)
    return f"assets/{namespace}/textures/{path}.png"


def see_through(image, uv):
    """True if the part of the texture a face uses has a partly transparent pixel, worked out as the game does."""
    u0, v0, u1, v1 = min(uv[0], uv[2]) / 16, min(uv[1], uv[3]) / 16, max(uv[0], uv[2]) / 16, max(uv[1], uv[3]) / 16
    width, height = image.size
    if (u0, v0, u1, v1) == (0, 0, 1, 1):
        box = (0, 0, width, height)
    else:
        box = (math.floor(u0 * width), math.floor(v0 * height), math.ceil(u1 * width), math.ceil(v1 * height))
    if box[2] <= box[0] or box[3] <= box[1]:
        return False
    return any(image.crop(box).getchannel("A").histogram()[1:255])


def split(name):
    model_path = f"{MODELS}/{name}.json"
    model = json.load(open(model_path))
    images = {key: Image.open(texture_path(value)).convert("RGBA")
              for key, value in model["textures"].items() if key != "particle"}
    body, glass = [], []
    for element in model["elements"]:
        solid = {d: f for d, f in element["faces"].items() if not see_through(images[f["texture"][1:]], f["uv"])}
        clear = {d: f for d, f in element["faces"].items() if d not in solid}
        if solid:
            body.append({**element, "faces": solid})
        if clear:
            glass.append({**element, "faces": clear})
    if not glass:
        print(f"{name}: no see-through faces")
        return
    used = {f["texture"][1:] for e in glass for f in e["faces"].values()}
    textures = {key: model["textures"][key] for key in sorted(used)}
    textures["particle"] = model["textures"]["particle"]
    model["elements"] = body
    json.dump(model, open(model_path, "w"), indent=1)
    json.dump({"textures": textures, "elements": glass, "display": model.get("display", {})},
              open(f"{MODELS}/{name}_glass.json", "w"), indent=1)
    json.dump({"model": {"type": "minecraft:model", "model": f"vexel:item/vehicle/{name}_glass"}},
              open(f"assets/vexel/items/{name}_glass.json", "w"), indent=2)
    print(f"{name}: moved {sum(len(e['faces']) for e in glass)} see-through faces to vexel:{name}_glass")


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        split(arg)
