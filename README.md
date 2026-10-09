# vexel-rp

The Vexel Network server resource pack (Minecraft 26.2, pack format 88). Model credits are in [CREDITS.md](CREDITS.md).

## Adding a vehicle model

Models made of boxes (Blockbench, or a Sketchfab glTF download of a Blockbench model) are converted with:

    python3 tools/gltf_to_model.py <model.gltf> <name> <length-in-blocks> [--skip-nodes NAME,...]

It writes the model, its textures and `assets/vexel/items/<name>.json`, and prints the `scale`, `offset` and
`size` for the vehicle type's `model` section in CityLifeCore's config. `tools/preview.py` draws a converted model
to a PNG to check it before testing in game.

Re-running the converter overwrites the model's textures. `truck_0.png` has the original company logos painted
over by hand, so keep that file if the truck is converted again.

## Releasing

    zip -r -X vexel-rp.zip pack.mcmeta assets
    sha1sum vexel-rp.zip
    gh release create <tag> vexel-rp.zip

Then set the server's `resource-pack` to the release asset URL and `resource-pack-sha1` to the hash.
