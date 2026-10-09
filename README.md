# vexel-rp

The Vexel Network server resource pack (Minecraft 1.21.11 to 26.2, pack formats 75 to 88). Model credits are in [CREDITS.md](CREDITS.md).

## Adding a vehicle model

Models made of boxes (Blockbench, or a Sketchfab glTF download of a Blockbench model) are converted with:

    python3 tools/gltf_to_model.py <model.gltf> <name> <length-in-blocks> [--skip-nodes NAME,...] [--only-nodes NAME,...]

It writes the model, its textures and `assets/vexel/items/<name>.json`, and prints the `scale`, `offset` and
`size` for the vehicle type's `model` section in CityLifeCore's config. `--skip-nodes` drops parts (like a
built-in driver or round parts that get blocky replacements) and `--only-nodes` keeps just some parts (the
helicopter's rotor is its own model, `helicopter_rotor`, so it can spin).

Source downloads live in `~/projects/vexel-dev/models-incoming/` (not committed). Vehicle lengths used so far:
sedan_a 6.5, sports_car 7.52, mini 6.67, golf_cart 5.09, truck 15, helicopter 9.44.

## Interiors

`tools/edits/<name>.json` holds hand changes the converter applies after converting: faces to retexture,
elements to remove, `cuts` (pieces of an element, used to hollow out solid cabins) and elements to add.
These files are made by `python3 tools/interior.py <name>`, which builds each vehicle's seats, wheel, dash and
glass, and draws `interior.png`. Run it, then run the converter again.

Seats are fitted so a player's eye is 0.87 blocks above their hips and about 1.2 blocks fit between cushion and
roof. The type's `seat-height` in CityLifeCore's config is the hips height minus 0.13.

To check a model, `tools/preview.py <model.json> <out.png>` draws the outside and
`tools/firstperson.py <model.json> <out.png> <eye x,y,z> --look x,y,z [--ids]` draws the driver's view
(in model pixels; `--ids` labels each element with its index).

Re-running the converter overwrites the model's textures. `truck_0.png` has the original company logos painted
over by hand, so after converting the truck again, restore it with `git checkout -- assets/vexel/textures/item/vehicle/truck_0.png`.

## Releasing

    zip -r -X vexel-rp.zip pack.mcmeta assets
    sha1sum vexel-rp.zip
    gh release create <tag> vexel-rp.zip

Then set the server's `resource-pack` to the release asset URL and `resource-pack-sha1` to the hash.
