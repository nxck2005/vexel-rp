#!/usr/bin/env python3
"""Draws a model from inside, as a driver sees it, to check what blocks the first-person view.

    firstperson.py <model.json> <out.png> <eye x,y,z> [--look x,y,z] [--ids]

The eye and look-at points are in model pixels (the same space as the model's from/to). With --ids, each element
is drawn in its own colour and labelled with its index, to find which elements to change. Needs numpy and Pillow.
Run from the pack root.
"""
import json
import math
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from preview import faces  # noqa: E402

WIDTH, HEIGHT, FOV = 960, 540, 70  # Minecraft's default vertical field of view


def main():
    args = sys.argv[1:]
    ids = "--ids" in args
    if ids:
        args.remove("--ids")
    look = None
    if "--look" in args:
        i = args.index("--look")
        look = np.array([float(v) for v in args[i + 1].split(",")])
        del args[i:i + 2]
    path, out = args[0], args[1]
    eye = np.array([float(v) for v in args[2].split(",")])
    model = json.load(open(path))
    textures = {}
    for key, value in model["textures"].items():
        namespace, name = value.split(":")
        textures["#" + key] = np.asarray(Image.open(f"assets/{namespace}/textures/{name}.png").convert("RGBA"), dtype=np.float32)

    if look is None:
        look = eye + np.array([0, 0, -1.0])
    forward = (look - eye) / np.linalg.norm(look - eye)
    right = np.cross(forward, [0, 1, 0])
    right /= np.linalg.norm(right)
    up = np.cross(right, forward)
    half = math.tan(math.radians(FOV / 2))
    xs = (np.arange(WIDTH) + 0.5 - WIDTH / 2) / (HEIGHT / 2) * half
    ys = -(np.arange(HEIGHT) + 0.5 - HEIGHT / 2) / (HEIGHT / 2) * half
    gx, gy = np.meshgrid(xs, ys)
    rays = forward + gx[..., None] * right + gy[..., None] * up

    depth = np.full((HEIGHT, WIDTH), np.inf)
    image = np.zeros((HEIGHT, WIDTH, 3))
    image[:] = (150, 190, 255)
    owner = np.full((HEIGHT, WIDTH), -1)
    element_faces = []
    for index, element in enumerate(model["elements"]):
        for face in faces({"elements": [element]}):
            element_faces.append((index, face))
    rng = np.random.default_rng(1)
    colours = rng.integers(60, 255, size=(len(model["elements"]), 3))
    see_through = []  # (t, pixel mask, colour, alpha) for translucent texels, blended after the solid pass
    for index, (corners, uvs, normal, texture, shade) in element_faces:
        normal = np.array(normal)
        v0, v1, v3 = (np.array(corners[i]) for i in (0, 1, 3))
        denom = rays @ normal
        visible = denom < -1e-9  # item models cull back faces
        t = ((v0 - eye) @ normal) / np.where(visible, denom, -1)
        hit = eye + t[..., None] * rays
        e1, e3 = v1 - v0, v3 - v0
        a = (hit - v0) @ e1 / (e1 @ e1) if e1 @ e1 else np.zeros_like(t)
        b = (hit - v0) @ e3 / (e3 @ e3) if e3 @ e3 else np.zeros_like(t)
        inside = visible & (t > 0.01) & (a >= 0) & (a <= 1) & (b >= 0) & (b <= 1) & (t < depth)
        if not inside.any():
            continue
        # Corners are 0 at v0, 1 at v1, 2 opposite, 3 at v3: interpolate uv across the parallelogram.
        uv = np.array(uvs)
        u = uv[0] + a[..., None] * (uv[1] - uv[0]) + b[..., None] * (uv[3] - uv[0])
        tex = textures[texture]
        h, w = tex.shape[:2]
        px = np.clip((u[..., 0] / 16 * w).astype(int), 0, w - 1)
        py = np.clip((u[..., 1] / 16 * h).astype(int), 0, h - 1)
        sample = tex[py, px]
        translucent = inside & (sample[..., 3] > 25) & (sample[..., 3] < 250)
        if translucent.any():
            see_through.append((t, translucent, sample[..., :3] * shade, sample[..., 3] / 255))
        inside &= sample[..., 3] >= 250
        depth[inside] = t[inside]
        image[inside] = colours[index] if ids else sample[inside][:, :3] * shade
        owner[inside] = index

    for t, mask, colour, alpha in see_through:  # glass in front of what is behind it
        front = mask & (t < depth)
        image[front] = image[front] * (1 - alpha[front, None]) + colour[front] * alpha[front, None]

    result = Image.fromarray(image.astype(np.uint8))
    if ids:
        draw = ImageDraw.Draw(result)
        for index in np.unique(owner[owner >= 0]):
            ys_, xs_ = np.nonzero(owner == index)
            if len(xs_) > 400:
                draw.text((int(xs_.mean()), int(ys_.mean())), str(index), fill=(0, 0, 0))
    result.save(out)


if __name__ == "__main__":
    main()
