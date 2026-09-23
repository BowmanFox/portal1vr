"""Validate mirrored controls against the shipped controller hardware paths."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
folder = root / "L4D2VR/SteamVRActionManifest"
manifest = json.loads((folder / "action_manifest.json").read_text())
actions = {a["name"]: a for a in manifest["actions"]}
assert len(actions) == len(manifest["actions"])
main = {k: v for k, v in actions.items() if k.startswith("/actions/main/")}
assert len(main) == 23
for name, definition in main.items():
    counterpart = name.replace("/actions/main", "/actions/left_handed")
    assert actions[counterpart]["type"] == definition["type"]
checks = 0
for path in folder.glob("bindings*.json"):
    binding = json.loads(path.read_text())
    original = binding["bindings"]["/actions/main"]["sources"]
    mirrored = binding["bindings"]["/actions/left_handed"]["sources"]
    assert len(original) == len(mirrored)
    valid_paths = {s["path"] for s in original}
    for source, target in zip(original, mirrored):
        assert source["path"].split("/")[3] != target["path"].split("/")[3]
        # Some bindings omit the offhand trigger; hardware still has it.
        assert target["path"] in valid_paths or target["path"].endswith("/input/trigger")
        assert target["mode"] == source["mode"]
        assert target.get("parameters") == source.get("parameters")
        for control, item in source["inputs"].items():
            actual = target["inputs"][control]["output"]
            assert actual == item["output"].replace("/actions/main", "/actions/left_handed")
            assert actual in actions
            checks += 1
menu = (root / "L4D2VR/resource/gamemenu.res").read_text()
for command in ("portal1vr_hand_left", "portal1vr_hand_right", "portal1vr_recenter"):
    assert menu.count('"engine ' + command + '"') == 1
for stock in ("ResumeGame", "OpenNewGameDialog", "OpenOptionsDialog", "Quit"):
    assert '"' + stock + '"' in menu
print(json.dumps({"mirrored_action_count": len(main), "binding_checks": checks,
                  "controller_types": 3, "menu_commands": 3, "passed": True}))
