"""Create a two-character fixture for deterministic performance and camera rendering."""
from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path

from PIL import Image, ImageDraw

from pipeline import ROOT, read, save

WIDTH, HEIGHT, FPS = 960, 540, 24
CHARACTERS = {
    "lin": {"cx": 300, "color": "#568883", "skin": "#f2b074", "accent": "#edac58"},
    "bo": {"cx": 670, "color": "#6388ab", "skin": "#efbb91", "accent": "#dc8f68"},
}
PARTS = ("body", "head", "eyes", "mouth", "left_arm", "right_arm")
DURATIONS = (48, 24, 24, 24, 24)
BEATS = (
    "Lin speaks while Bo listens and blinks.",
    "Lin points while the camera gently pushes closer.",
    "Bo nods in response.",
    "Bo speaks while Lin listens.",
    "Lin makes a small reaction bounce.",
)


def _part_image(folder: Path, shot_index: int, character_id: str, part: str, state: str = "base") -> Path:
    spec = CHARACTERS[character_id]
    cx = spec["cx"] + shot_index
    cy = 0
    image = Image.new("RGBA", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(image)
    skin, accent = spec["skin"], spec["accent"]
    if part == "body":
        draw.rounded_rectangle((cx - 48, 244, cx + 48, 414), 26, fill=spec["color"], outline="#172332", width=5)
        draw.ellipse((cx - 16, 286, cx + 16, 318), fill=accent)
    elif part == "head":
        draw.ellipse((cx - 56, 128, cx + 56, 240), fill=skin, outline="#172332", width=5)
        draw.arc((cx - 55, 122, cx + 55, 218), 185, 355, fill=spec["color"], width=12)
    elif part == "eyes":
        if state == "blink":
            draw.line((cx - 31, 184, cx - 15, 184), fill="#172332", width=5)
            draw.line((cx + 15, 184, cx + 31, 184), fill="#172332", width=5)
        elif state == "surprised":
            draw.ellipse((cx - 32, 168, cx - 14, 198), fill="#172332")
            draw.ellipse((cx + 14, 168, cx + 32, 198), fill="#172332")
        else:
            draw.ellipse((cx - 29, 170, cx - 16, 190), fill="#172332")
            draw.ellipse((cx + 16, 170, cx + 29, 190), fill="#172332")
    elif part == "mouth":
        if state == "open":
            draw.ellipse((cx - 9, 211, cx + 9, 228), fill="#6f3039")
        elif state == "happy":
            draw.arc((cx - 20, 202, cx + 20, 237), 10, 170, fill="#6f3039", width=5)
        else:
            draw.line((cx - 11, 219, cx + 11, 219), fill="#6f3039", width=4)
    elif part == "left_arm":
        draw.line((cx - 35, 270, cx - 106, 314), fill=skin, width=22)
        draw.ellipse((cx - 120, 302, cx - 99, 324), fill=skin)
    elif part == "right_arm":
        if state == "point":
            draw.line((cx + 35, 270, cx + 104, 270), fill=skin, width=22)
            draw.line((cx + 100, 270, cx + 122, 253), fill=skin, width=11)
        else:
            draw.line((cx + 35, 270, cx + 106, 314), fill=skin, width=22)
            draw.ellipse((cx + 98, 303, cx + 121, 326), fill=skin)
    name = f"{character_id}_{part}_{state}.png"
    path = folder / name
    image.save(path)
    return path


def _manifest(character_id: str) -> dict:
    spec = CHARACTERS[character_id]
    return {
        "id": character_id,
        "name": "林岚" if character_id == "lin" else "小博",
        "story_role": "Character Performance runtime fixture",
        "identity": {
            "face": "simple oval synthetic face", "hair": "short graphic fringe",
            "clothing": "flat-color shirt", "proportions": "small geometric character",
            "distinctive_features": f"{spec['color']} body and {spec['accent']} accent",
        },
        "capabilities": {
            "parts": list(PARTS), "poses": ["point"], "expressions": ["happy", "surprised"],
        },
        "reference": {
            "image": f"characters/{character_id}/reference.png", "status": "planned",
            "locks": "identity_only", "prompt": "Synthetic test character; not production art.",
        },
    }


def build(project: Path) -> Path:
    if project.exists():
        raise FileExistsError(f"Use a new output directory: {project}")
    project.mkdir(parents=True)
    data = {name: read(ROOT / "examples/library" / f"{name}.json") for name in (
        "production_brief", "characters", "storyboard", "motion_plan",
    )}
    project_id = "character-performance-fixture"
    for value in data.values():
        value["project_id"] = project_id
    brief = data["production_brief"]
    brief.update({
        "title": "Character Performance Runtime fixture",
        "original_content": " ".join(BEATS),
        "content_preservation": ["Show two characters speaking, reacting, and moving through simple local actions."],
        "setting": {"place": "Synthetic test stage", "era": "timeless", "culture": "technical fixture"},
        "visual_language": "Simple flat geometric illustration for runtime verification.",
        "tone": "neutral technical test",
        "format": {"width": WIDTH, "height": HEIGHT, "fps": FPS, "duration_frames": sum(DURATIONS)},
        "assumptions": ["Synthetic characters and artwork are test assets, not production art."],
    })
    data["characters"]["characters"] = [_manifest("lin"), _manifest("bo")]
    board = data["storyboard"]
    board["scenes"] = [{
        "id": "stage", "space": "Two characters on a flat stage with a simple horizon.",
        "time": "day", "lighting": "Soft even test lighting.",
        "anchors": ["Lin left", "Bo right", "shared ground line"],
    }]
    board["beats"] = [
        {"id": f"b{i+1}", "source_excerpt": text, "change": text, "emotion": "friendly"}
        for i, text in enumerate(BEATS)
    ]

    stage_specs = [
        ("speaker", "idle", "Lin speaks; Bo listens and blinks.", "speaker"),
        ("idle", "listener", "Lin points as the camera pushes in; Bo watches.", "point"),
        ("listener", "listener", "Bo nods once in response.", "nod"),
        ("listener", "speaker", "Bo speaks; Lin listens.", "talk"),
        ("idle", "idle", "Lin makes a small reaction bounce.", "bounce"),
    ]
    board_shots = []
    motion_shots = []
    for index, (duration, beat, stage) in enumerate(zip(DURATIONS, BEATS, stage_specs)):
        shot_id = f"shot_{index+1:03d}"
        role_a, role_b, purpose, action = stage
        next_id = f"shot_{index+2:03d}" if index < 4 else None
        dialogue = []
        if index in (0, 3):
            speaker = "lin" if index == 0 else "bo"
            dialogue = [{
                "speaker": speaker,
                "text": "Hey, take a look!" if speaker == "lin" else "That's a great idea!",
                "start_frame": 2, "end_frame": duration - 2,
            }]
        characters = [
            {"character_id": "lin", "action": "speaks" if index == 0 else purpose,
             "pose_tag": "standing", "expression": "happy" if index == 4 else "neutral", "gaze": "Bo"},
            {"character_id": "bo", "action": "listens" if index < 3 else purpose,
             "pose_tag": "standing", "expression": "neutral", "gaze": "Lin"},
        ]
        board_layers = [{"id": "bg", "role": "background", "elements": "Simple test stage", "method": "reconstruct", "reason": "Background plane."}]
        for cid in CHARACTERS:
            for part in PARTS:
                board_layers.append({
                    "id": f"{cid}_{part}", "role": "character", "character_id": cid,
                    "elements": f"{cid} {part}", "method": "reconstruct", "reason": "Aligned local character part.",
                })
        board_shots.append({
            "id": shot_id, "source_panel": f"performance-test-{index+1}", "beat_id": f"b{index+1}",
            "duration_frames": duration, "purpose": purpose, "transition": "cut",
            "setting": "Synthetic test stage", "shot_size": ["wide", "medium", "medium", "medium", "close_up"][index],
            "angle": "eye_level", "composition": purpose, "composition_tag": ["center", "right_third", "left_third", "diagonal", "symmetrical"][index],
            "characters": characters, "continuity": "Both characters remain on their assigned sides of the stage.",
            "master": f"shots/{shot_id}/master.png", "layers": board_layers,
            "repetition_exception": "Repeated synthetic stage is intentional for runtime isolation.",
            "dialogue": dialogue,
            "direction": {
                "scene_id": "stage", "camera_position": "push_in" if index == 1 else "static",
                "background_view": f"stage-view-{index+1}", "view_id": f"stage-view-{index+1}",
                "incoming_state": "Both characters hold their established positions.",
                "outgoing_state": "The current interaction beat completes.",
                "micro_actions": purpose, "cut_reason": "Advance to the next performance beat.",
                "next_shot_id": next_id, "handoff": "Continue with the speaker/listener relationship and stable screen direction.",
                "reaction_hold_frames": (duration - dialogue[-1]["end_frame"]) if dialogue else 0,
                "listening_reactions": ([{"character_id": "bo" if index == 0 else "lin", "response": "listen and hold eye contact"}] if dialogue else []),
            },
        })

        folder = project / "shots" / shot_id / "layers"
        folder.mkdir(parents=True, exist_ok=True)
        bg = Image.new("RGBA", (WIDTH, HEIGHT), "#efe9d8")
        draw = ImageDraw.Draw(bg)
        draw.rectangle((0, 426, WIDTH, HEIGHT), fill="#d7cfb6")
        draw.line((0, 426, WIDTH, 426), fill="#a89b7c", width=5)
        draw.ellipse((CHARACTERS["lin"]["cx"]-95, 408, CHARACTERS["lin"]["cx"]+95, 435), fill="#c2b79d")
        draw.ellipse((CHARACTERS["bo"]["cx"]-95, 408, CHARACTERS["bo"]["cx"]+95, 435), fill="#c2b79d")
        bg_path = folder / "bg.png"
        bg.save(bg_path)
        motion_layers = [{"layer_id": "bg", "asset": f"shots/{shot_id}/layers/bg.png", "depth": "background", "z": 0,
                          "from": {"x": 0, "y": 0, "scale": 1}, "to": {"x": 0, "y": 0, "scale": 1}}]
        master = bg.copy()
        z = 10
        for cid, cx_base in (("lin", CHARACTERS["lin"]["cx"]), ("bo", CHARACTERS["bo"]["cx"])):
            for part in PARTS:
                asset_path = _part_image(folder, index, cid, part)
                rel = f"shots/{shot_id}/layers/{asset_path.name}"
                state_assets = {}
                if part == "eyes":
                    blink = _part_image(folder, index, cid, part, "blink")
                    surprised = _part_image(folder, index, cid, part, "surprised")
                    state_assets = {"blink": f"shots/{shot_id}/layers/{blink.name}", "expression:surprised": f"shots/{shot_id}/layers/{surprised.name}"}
                if part == "mouth":
                    closed = asset_path
                    opened = _part_image(folder, index, cid, part, "open")
                    happy = _part_image(folder, index, cid, part, "happy")
                    state_assets = {"closed": rel, "open": f"shots/{shot_id}/layers/{opened.name}", "expression:happy": f"shots/{shot_id}/layers/{happy.name}"}
                if part == "right_arm":
                    pointing = _part_image(folder, index, cid, part, "point")
                    state_assets["pose:point"] = f"shots/{shot_id}/layers/{pointing.name}"
                with Image.open(asset_path) as image:
                    master.alpha_composite(image)
                pivot_x = cx_base + index
                pivot_y = {"body": 330, "head": 232, "eyes": 182, "mouth": 219, "left_arm": 270, "right_arm": 270}[part]
                plan_layer = {
                    "layer_id": f"{cid}_{part}", "asset": rel, "depth": "character", "z": z,
                    "from": {"x": 0, "y": 0, "scale": 1}, "to": {"x": 0, "y": 0, "scale": 1},
                    "state_assets": state_assets,
                    "acting": {
                        "part": part, "pivot": [pivot_x / WIDTH, pivot_y / HEIGHT], "easing": "easeInOut",
                        "keys": [
                            {"frame": 0, "x": 0, "y": 0, "rotation": 0, "opacity": 1, "scale": 1},
                            {"frame": duration-1, "x": 0, "y": 0, "rotation": 0, "opacity": 1, "scale": 1},
                        ],
                    },
                }
                motion_layers.append(plan_layer)
                z += 1
        master.save(folder.parent / "master.png")

        def performer(cid, role, events=(), pose=None, expression=None):
            cx = CHARACTERS[cid]["cx"] + index
            return {
                "character_id": cid, "role": role, "root_pivot": [cx / WIDTH, 0.5],
                "root_easing": "easeInOut", **({"pose": pose} if pose else {}), **({"expression": expression} if expression else {}),
                "root_keys": [
                    {"frame": 0, "x": 0, "y": 0, "scale": 1, "rotation": 0, "opacity": 1},
                    {"frame": duration-1, "x": 0, "y": 0, "scale": 1, "rotation": 0, "opacity": 1},
                ],
                "events": list(events),
            }

        def event(event_id, preset, start=2, peak=6, settle=None, end=None, part=None, amplitude=None):
            settle = duration - 5 if settle is None else settle
            end = duration - 2 if end is None else end
            value = {"event_id": event_id, "preset": preset, "start_frame": start,
                     "peak_frame": peak, "settle_frame": settle, "end_frame": end, "easing": "easeInOut"}
            if part: value["part"] = part
            if amplitude is not None: value["amplitude"] = amplitude
            return value

        perf_a, perf_b = [], []
        if index == 0:
            perf_a.append(performer("lin", role_a, [event("lin-talk", "talk", 0, 2, duration-3, duration-1)]))
            perf_b.append(performer("bo", role_b, [event("bo-idle", "idle", 0, 0, duration-1, duration-1), event("bo-blink", "blink", 18, 20, 22, 24)]))
        elif index == 1:
            root_keys = [
                {"frame": 0, "x": 0, "y": 0, "scale": 1, "rotation": 0, "opacity": 1},
                {"frame": duration-1, "x": 3, "y": -2, "scale": 1.015, "rotation": 0, "opacity": 1},
            ]
            perf_a.append({**performer("lin", role_a, [event("lin-point", "point", 2, 6, 17, 22, "right_arm")], pose="point"), "root_keys": root_keys})
            perf_b.append(performer("bo", role_b, [event("bo-listen-blink", "blink", 14, 16, 18, 20)]))
        elif index == 2:
            perf_a.append(performer("lin", role_a))
            perf_b.append(performer("bo", role_b, [event("bo-nod", "nod", 2, 7, 14, 21)]))
        elif index == 3:
            perf_a.append(performer("lin", role_a))
            perf_b.append(performer("bo", role_b, [event("bo-talk", "talk", 0, 2, duration-3, duration-1)]))
        else:
            perf_a.append(performer("lin", role_a, [event("lin-bounce", "small_bounce", 2, 7, 12, 18, amplitude=11)], expression="happy"))
            perf_b.append(performer("bo", role_b))

        camera = {"type": "static", "parallax_enabled": False}
        if index in (0, 1):
            end_zoom = 1.04 if index == 0 else 1.08
            camera = {
                "type": "push_in", "focus_target": {"id": "characters", "x": 480, "y": 270},
                "from": {"x": 480, "y": 270, "zoom": 1}, "to": {"x": 480, "y": 270, "zoom": end_zoom},
                "screen_target": {"x": 0.5, "y": 0.5}, "easing": "easeInOut", "parallax_enabled": True,
            }
        elif index == 2:
            camera = {
                "type": "push_in", "focus_target": {"id": "characters", "x": 480, "y": 270},
                "from": {"x": 480, "y": 270, "zoom": 1}, "to": {"x": 480, "y": 270, "zoom": 1.05},
                "screen_target": {"x": 0.5, "y": 0.5}, "easing": "easeInOut", "parallax_enabled": True,
            }
        elif index == 3:
            camera = {
                "type": "pull_out", "focus_target": {"id": "characters", "x": 480, "y": 270},
                "from": {"x": 480, "y": 270, "zoom": 1.05}, "to": {"x": 480, "y": 270, "zoom": 1.02},
                "screen_target": {"x": 0.5, "y": 0.5}, "easing": "easeInOut", "parallax_enabled": True,
            }
        else:
            camera = {
                "type": "pull_out", "focus_target": {"id": "characters", "x": 480, "y": 270},
                "from": {"x": 480, "y": 270, "zoom": 1.06}, "to": {"x": 480, "y": 270, "zoom": 1},
                "screen_target": {"x": 0.5, "y": 0.5}, "easing": "easeInOut", "parallax_enabled": True,
            }
        motion_shots.append({
            "shot_id": shot_id, "start_frame": sum(DURATIONS[:index]), "duration_frames": duration,
            "transition": "cut", "performance": {
                "mode": "sequential-comic", "intent": purpose,
                "static_reason": "Synthetic performance fixture holds unrequested layers.", "reviewed": False,
            },
            "camera": camera, "character_performance": perf_a + perf_b,
            "layers": motion_layers,
            "review": {"master_alignment": False, "background_completed": False, "motion_bounds_checked": False,
                       "notes": "Synthetic Character Performance / Camera runtime fixture; not production art."},
        })
    board["shots"] = board_shots
    motion = data["motion_plan"]
    motion.update({"version": "0.4", "asset_mode": "fixture", "shots": motion_shots})
    for name, value in data.items():
        save(project / f"{name}.json", value)
    return project


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    print(build(parser.parse_args().project.resolve()))
