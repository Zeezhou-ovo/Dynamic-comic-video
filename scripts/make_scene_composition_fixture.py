"""Build a reusable generic-room Scene/Asset fixture with real layered characters."""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw

from make_character_performance_fixture import build as build_performance_fixture
from pipeline import read, save

W, H = 960, 540
CHAR_W, CHAR_H = 260, 360
CHARACTER_SPECS = {
    "lin": {"skin": "#f1c7a4", "hair": "#382c32", "shirt": "#426f82", "trim": "#e7b967", "accent": "#d98963"},
    "bo": {"skin": "#e6b694", "hair": "#61483c", "shirt": "#7b6c48", "trim": "#b8d7d0", "accent": "#668d86"},
}
ANCHOR = [0.5, 0.94]


def _room(project: Path):
    folder = project / "scene"
    folder.mkdir(parents=True, exist_ok=True)
    bg = Image.new("RGBA", (W, H), "#e7ddcb")
    draw = ImageDraw.Draw(bg)
    draw.rectangle((0, 0, W, 354), fill="#efe5d5")
    draw.rectangle((0, 354, W, H), fill="#c9aa83")
    draw.rectangle((46, 55, 264, 270), fill="#a8c4c0", outline="#806f5e", width=9)
    draw.rectangle((60, 68, 250, 258), fill="#bcd0c7")
    draw.line((155, 68, 155, 258), fill="#eee5d5", width=8)
    draw.line((60, 162, 250, 162), fill="#eee5d5", width=8)
    draw.ellipse((92, 84, 175, 167), fill="#f5dfa8")
    draw.polygon([(60, 255), (100, 197), (135, 255)], fill="#6f988c")
    draw.polygon([(153, 257), (202, 191), (250, 257)], fill="#7e9b7f")
    draw.rectangle((0, 291, 960, 355), fill="#dbcdb8")
    draw.rectangle((666, 64, 916, 300), fill="#755d4d")
    draw.rectangle((678, 77, 904, 287), fill="#9b795b")
    for y in (127, 190, 252):
        draw.rectangle((678, y, 904, y + 8), fill="#dfc89d")
    for x, y, c in ((696, 87, "#bd8c62"), (750, 91, "#71877a"), (813, 84, "#e3c177"),
                     (862, 88, "#69808c"), (702, 141, "#71928a"), (778, 143, "#d3a66e"),
                     (841, 140, "#bd8068"), (694, 205, "#d3a66e"), (760, 207, "#607d80"), (850, 204, "#8b9a74")):
        draw.rounded_rectangle((x, y, x + 35, y + 38), 3, fill=c)
    bg.save(folder / "background.png")

    mid = Image.new("RGBA", (W, H))
    draw = ImageDraw.Draw(mid)
    draw.ellipse((148, 404, 822, 452), fill="#907557")
    draw.polygon([(118, 394), (168, 374), (812, 374), (860, 394), (836, 418), (140, 418)], fill="#b8895e")
    draw.line((140, 397, 838, 397), fill="#dfbd88", width=5)
    draw.polygon([(186, 413), (207, 413), (220, 520), (199, 520)], fill="#80664d")
    draw.polygon([(770, 413), (790, 413), (777, 520), (756, 520)], fill="#80664d")
    mid.save(folder / "midground.png")

    front = Image.new("RGBA", (W, H))
    draw = ImageDraw.Draw(front)
    draw.polygon([(0, 540), (0, 447), (25, 414), (52, 448), (62, 385), (88, 430), (108, 401), (135, 472), (131, 540)], fill="#557765")
    draw.polygon([(960, 540), (960, 431), (936, 402), (910, 447), (895, 394), (871, 439), (844, 407), (829, 477), (838, 540)], fill="#627a60")
    for x, y in ((30, 448), (75, 465), (916, 457), (872, 471)):
        draw.ellipse((x - 11, y - 7, x + 11, y + 7), fill="#d5b876")
    front.save(folder / "foreground.png")

    book = Image.new("RGBA", (260, 150))
    draw = ImageDraw.Draw(book)
    draw.rounded_rectangle((18, 25, 242, 126), 14, fill="#704b39", outline="#ead29a", width=5)
    draw.polygon([(30, 32), (130, 45), (130, 120), (30, 108)], fill="#fff3cf", outline="#cfb47b")
    draw.polygon([(130, 45), (230, 32), (230, 108), (130, 120)], fill="#f4e6c2", outline="#cfb47b")
    draw.line((130, 45, 130, 120), fill="#b79c70", width=4)
    for y in (66, 82, 98):
        draw.line((48, y, 112, y + 4), fill="#baaa8c", width=2)
        draw.line((148, y + 4, 212, y), fill="#baaa8c", width=2)
    draw.ellipse((112, 65, 148, 101), fill="#efc667")
    draw.ellipse((120, 73, 140, 93), fill="#fff1b5")
    book.save(folder / "book.png")


def _character_part(project: Path, character_id: str, part: str, state: str = "base"):
    spec = CHARACTER_SPECS[character_id]
    image = Image.new("RGBA", (CHAR_W, CHAR_H))
    draw = ImageDraw.Draw(image)
    skin, hair, shirt = spec["skin"], spec["hair"], spec["shirt"]
    if part == "body":
        draw.rounded_rectangle((59, 181, 201, 351), 45, fill=shirt, outline="#302a2a", width=5)
        draw.polygon([(99, 183), (130, 222), (160, 183)], fill=spec["trim"], outline="#302a2a")
        draw.rounded_rectangle((121, 233, 139, 247), 5, fill=spec["accent"])
        draw.line((81, 280, 179, 280), fill=spec["trim"], width=4)
    elif part == "left_arm":
        draw.line((79, 205, 47, 250, 63, 293), fill=shirt, width=30)
        draw.line((79, 205, 47, 250, 63, 293), fill="#302a2a", width=3)
        draw.ellipse((51, 281, 76, 305), fill=skin, outline="#302a2a", width=2)
    elif part == "right_arm":
        if state == "point":
            draw.line((182, 205, 218, 184, 238, 166), fill=shirt, width=30)
            draw.line((182, 205, 218, 184, 238, 166), fill="#302a2a", width=3)
            draw.line((232, 168, 250, 151), fill=skin, width=12)
        else:
            draw.line((181, 205, 216, 250, 196, 292), fill=shirt, width=30)
            draw.line((181, 205, 216, 250, 196, 292), fill="#302a2a", width=3)
            draw.ellipse((183, 281, 208, 306), fill=skin, outline="#302a2a", width=2)
    elif part == "head":
        draw.rounded_rectangle((106, 176, 154, 219), 17, fill=skin)
        draw.ellipse((48, 57, 212, 228), fill=skin, outline="#302a2a", width=5)
        draw.ellipse((55, 63, 75, 102), fill=skin, outline="#302a2a", width=3)
        draw.ellipse((185, 63, 205, 102), fill=skin, outline="#302a2a", width=3)
        draw.ellipse((62, 139, 93, 153), fill="#e5a79a")
        draw.ellipse((167, 139, 198, 153), fill="#e5a79a")
    elif part == "hair":
        draw.pieslice((43, 38, 217, 198), 180, 360, fill=hair, outline="#29252c", width=5)
        draw.polygon([(44, 106), (60, 66), (105, 51), (156, 58), (207, 91), (195, 135),
                      (173, 111), (157, 140), (139, 106), (118, 143), (98, 107), (75, 139), (62, 110)], fill=hair)
        draw.line((58, 72, 93, 53), fill="#85727a", width=3)
        if character_id == "lin":
            draw.rounded_rectangle((185, 72, 204, 79), 3, fill=spec["trim"])
            draw.rounded_rectangle((190, 84, 208, 91), 3, fill=spec["trim"])
        else:
            draw.polygon([(47, 89), (23, 66), (54, 70)], fill=spec["accent"])
    elif part == "eyes":
        if state == "blink":
            draw.arc((76, 115, 111, 142), 190, 350, fill="#44352e", width=4)
            draw.arc((148, 115, 183, 142), 190, 350, fill="#44352e", width=4)
        else:
            iris = "#856536" if character_id == "lin" else "#56776e"
            draw.ellipse((83, 116, 104, 143), fill=iris, outline="#3a302b", width=2)
            draw.ellipse((156, 116, 177, 143), fill=iris, outline="#3a302b", width=2)
            draw.ellipse((90, 120, 97, 132), fill="#2d292a")
            draw.ellipse((163, 120, 170, 132), fill="#2d292a")
            draw.ellipse((92, 119, 96, 123), fill="white")
            draw.ellipse((165, 119, 169, 123), fill="white")
        draw.arc((75, 105, 112, 125), 190, 350, fill="#44352e", width=3)
        draw.arc((148, 105, 185, 125), 190, 350, fill="#44352e", width=3)
    elif part == "mouth":
        if state == "open":
            draw.ellipse((119, 155, 141, 180), fill="#814750", outline="#5c3235", width=2)
            draw.arc((122, 157, 138, 166), 180, 360, fill="#f4d2bd", width=2)
        elif state == "happy":
            draw.arc((108, 148, 153, 183), 10, 170, fill="#814750", width=4)
        elif state == "confused":
            draw.arc((115, 151, 149, 180), 195, 345, fill="#814750", width=4)
        else:
            draw.arc((111, 147, 149, 176), 15, 165, fill="#814750", width=3)
    elif part == "badge":
        draw.ellipse((129, 243, 157, 271), fill=spec["trim"], outline="#51443a", width=2)
        draw.ellipse((137, 251, 149, 263), fill="#f9ecd0")
    return image


def _write_character_assets(project: Path):
    manifests = []
    for character_id in CHARACTER_SPECS:
        root = project / "character_art" / character_id
        root.mkdir(parents=True, exist_ok=True)
        part_names = ("body", "left_arm", "right_arm", "head", "hair", "eyes", "mouth", "badge")
        parts = {}
        for z, part in enumerate(part_names, start=10):
            states = {}
            states_to_draw = {"base": "base"}
            if part == "eyes":
                states_to_draw["blink"] = "blink"
                states_to_draw["expression:happy"] = "base"
                states_to_draw["expression:surprised"] = "base"
                states_to_draw["expression:confused"] = "base"
            if part == "mouth":
                states_to_draw.update({"open": "open", "closed": "base", "expression:happy": "happy",
                                       "expression:surprised": "open", "expression:confused": "confused"})
            if part == "right_arm":
                states_to_draw["pose:point"] = "point"
            for state_name, draw_state in states_to_draw.items():
                path = root / f"{part}_{state_name.replace(':', '_')}.png"
                _character_part(project, character_id, part, draw_state).save(path)
                if state_name == "base":
                    base_path = path
                else:
                    states[state_name] = path.relative_to(project).as_posix()
            pivot = {
                "body": [0.5, 0.78], "left_arm": [0.31, 0.60], "right_arm": [0.70, 0.60],
                "head": [0.5, 0.60], "hair": [0.5, 0.39], "eyes": [0.5, 0.37],
                "mouth": [0.5, 0.46], "badge": [0.55, 0.70],
            }[part]
            parts[part] = {
                "asset": base_path.relative_to(project).as_posix(),
                "pixel_size": {"width": CHAR_W, "height": CHAR_H},
                "anchor": pivot, "pivot": pivot,
                "depth": "character", "z": z,
                "state_assets": states,
            }
        manifests.append({
            "character_id": character_id,
            "reference_size": {"width": CHAR_W, "height": CHAR_H},
            "root_anchor": ANCHOR,
            "anchors": {
                "root": ANCHOR,
                # Medium framing follows the torso center but fits the full upper-body silhouette.
                "body": {"position": [0.5, 0.70], "bounds": {"left": 0.12, "top": 0.14, "right": 0.88, "bottom": 1.0}},
                "face": {"position": [0.5, 0.39], "bounds": {"left": 0.22, "top": 0.18, "right": 0.78, "bottom": 0.56}},
                "head": {"position": [0.5, 0.43], "bounds": {"left": 0.17, "top": 0.15, "right": 0.83, "bottom": 0.62}},
                "mouth": {"position": [0.5, 0.46], "bounds": {"left": 0.42, "top": 0.40, "right": 0.58, "bottom": 0.51}},
                "left_hand": {"position": [0.24, 0.80], "bounds": {"left": 0.18, "top": 0.76, "right": 0.31, "bottom": 0.86}},
                "right_hand": {"position": [0.76, 0.80], "bounds": {"left": 0.69, "top": 0.76, "right": 0.82, "bottom": 0.86}},
                "eyes": {"position": [0.5, 0.37], "bounds": {"left": 0.30, "top": 0.31, "right": 0.70, "bottom": 0.41}},
            },
            "bounds": {"left": 0.12, "top": 0.14, "right": 0.88, "bottom": 1.0},
            "parts": parts,
        })
    return manifests


def build(project: Path):
    if project.exists():
        raise FileExistsError(f"Use a new output directory: {project}")
    build_performance_fixture(project)
    data = {name: read(project / f"{name}.json") for name in
            ("production_brief", "characters", "storyboard", "motion_plan")}
    project_id = "phase4-generic-room"
    for value in data.values():
        value["project_id"] = project_id
    data["production_brief"].update({
        "title": "Phase 4 · generic-room scene composition",
        "original_content": "Lin finds a mysterious book on the reading room table. Bo leans in to look. The book opens and reveals a tiny golden light. They share a quiet smile.",
        "setting": {"place": "A sunlit reading room", "era": "contemporary", "culture": "generic story setting"},
        "visual_language": "Soft, warm, hand-drawn 2D illustration with clear layered silhouettes.",
        "tone": "curious, warm and lightly magical",
        "assumptions": ["Synthetic artwork verifies Scene Graph and composition; it is test art, not final production art."],
    })
    for index, beat in enumerate(data["storyboard"]["beats"]):
        beat["source_excerpt"] = data["production_brief"]["original_content"]
        beat["change"] = ("They spot an old book" if index == 0 else "They inspect the book together" if index < 3
                          else "A warm light appears between the pages" if index == 3 else "They smile at the discovery")
    for name, value in data.items():
        save(project / f"{name}.json", value)

    _room(project)
    character_manifests = _write_character_assets(project)
    scene = {
        "version": "0.1", "project_id": project_id, "scene_id": "generic-room",
        "coordinate_system": "normalized-0-to-1", "reference_size": {"width": W, "height": H},
        "layers": [
            {"id": "scene_root", "parent_id": None, "kind": "group", "depth": "background", "z": 0, "visible": True},
            {"id": "background", "parent_id": "scene_root", "kind": "render_layer", "depth": "background", "asset": "scene/background.png", "fit": "canvas", "z": 1, "visible": True},
            {"id": "midground", "parent_id": "scene_root", "kind": "render_layer", "depth": "midground", "asset": "scene/midground.png", "fit": "canvas", "z": 10, "visible": True},
            {"id": "character_field", "parent_id": "scene_root", "kind": "group", "depth": "character", "z": 20, "visible": True},
            {"id": "foreground", "parent_id": "scene_root", "kind": "render_layer", "depth": "foreground", "asset": "scene/foreground.png", "fit": "canvas", "z": 40, "visible": True},
        ],
        "objects": [{"id": "book", "parent_id": "scene_root", "asset": "scene/book.png", "depth": "foreground",
                      "anchor_id": "book", "position": [0.5, 0.731], "size": [0.20, 0.20],
                      "pivot": [0.5, 0.5], "z": 33, "visible": True}],
        "character_slots": {
            "slot_left": {"parent_id": "character_field", "position": [0.31, 0.83], "scale": 0.76, "facing": 1, "z": 21, "depth": "character"},
            "slot_right": {"parent_id": "character_field", "position": [0.69, 0.83], "scale": 0.76, "facing": -1, "z": 22, "depth": "character"},
        },
        "character_instances": [
            {"character_id": "lin", "slot_id": "slot_left", "visible": True},
            {"character_id": "bo", "slot_id": "slot_right", "visible": True},
        ],
        "composition_anchors": {
            "center": [0.5, 0.5], "book": {"position": [0.5, 0.731], "bounds": {"left": 0.4, "top": 0.631, "right": 0.6, "bottom": 0.831}},
        },
        "camera_safe_bounds": {"left": 0.08, "top": 0.08, "right": 0.92, "bottom": 0.92},
        "background_coverage_bounds": {"left": 0, "top": 0, "right": 1, "bottom": 1},
    }
    assets = {"version": "0.1", "project_id": project_id, "coordinate_system": "normalized-0-to-1",
              "characters": character_manifests}
    save(project / "scene_manifest.json", scene)
    save(project / "character_assets.json", assets)
    return project


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    print(build(parser.parse_args().project.resolve()))
