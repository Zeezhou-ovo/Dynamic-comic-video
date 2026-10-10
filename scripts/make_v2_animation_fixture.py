"""Build the first V2 limited-animation technical fixture on top of the V1 character runtime fixture."""
from __future__ import annotations

import argparse
from pathlib import Path
from PIL import Image

from make_character_performance_fixture import build as build_character_fixture
from pipeline import read, save


def _shift_variant(src: Path, dst: Path, dx: int, dy: int) -> None:
    image = Image.open(src).convert("RGBA")
    shifted = Image.new("RGBA", image.size)
    shifted.alpha_composite(image, (dx, dy))
    shifted.save(dst)


def build(project: Path) -> Path:
    build_character_fixture(project)

    brief = read(project / "production_brief.json")
    brief["title"] = "V2 limited-animation dash fixture"
    brief["original_content"] += " Lin anticipates, dashes left with a stretched pose, hits an impact beat, then settles."
    brief["content_preservation"].append("Demonstrate V2 pose clips and comic effects without breaking V1 character performance.")
    save(project / "production_brief.json", brief)

    characters = read(project / "characters.json")
    lin = next(item for item in characters["characters"] if item["id"] == "lin")
    poses = lin.setdefault("capabilities", {}).setdefault("poses", [])
    for pose in ("idle", "dash"):
        if pose not in poses:
            poses.append(pose)
    save(project / "characters.json", characters)

    motion = read(project / "motion_plan.json")
    first = motion["shots"][0]
    first["camera"] = {
        "type": "push_in",
        "focus_target": {"id": "lin", "x": 300, "y": 290},
        "from": {"x": 480, "y": 270, "zoom": 1.0},
        "to": {"x": 430, "y": 270, "zoom": 1.12},
        "screen_target": {"x": 0.45, "y": 0.54},
        "easing": "easeInOut",
        "parallax_enabled": True
    }

    # Add a synthetic dash-pose state to each Lin part in shot 1. These are
    # technical assets only; production characters should use authored pose art.
    layer_dir = project / "shots" / "shot_001" / "layers"
    for layer in first["layers"]:
        if layer.get("character_id") != "lin":
            continue
        src = project / layer["asset"]
        dash_name = src.stem + "_dash.png"
        dash_path = layer_dir / dash_name
        _shift_variant(src, dash_path, -22, -8)
        layer.setdefault("state_assets", {})["pose:dash"] = f"shots/shot_001/layers/{dash_name}"

    save(project / "motion_plan.json", motion)

    animation = {
        "version": "0.1",
        "project_id": brief["project_id"],
        "shots": [{
            "shot_id": "shot_001",
            "characters": [{
                "character_id": "lin",
                "pose_clips": [{
                    "clip_id": "lin_dash",
                    "start_frame": 6,
                    "anticipation_end_frame": 10,
                    "action_end_frame": 17,
                    "hold_end_frame": 26,
                    "end_frame": 36,
                    "base_pose": "idle",
                    "action_pose": "dash",
                    "smear": True,
                    "rotation_deg": -7,
                    "translate": {"x": -150, "y": -6},
                    "squash_stretch": {"x": 0.22, "y": -0.14}
                }]
            }],
            "effects": [
                {
                    "event_id": "dash_lines",
                    "effect_type": "speed_lines",
                    "start_frame": 10,
                    "end_frame": 23,
                    "intensity": 1.0,
                    "position": [0.42, 0.5],
                    "size": 0.72
                },
                {
                    "event_id": "dash_burst",
                    "effect_type": "radial_burst",
                    "start_frame": 14,
                    "end_frame": 21,
                    "intensity": 0.34,
                    "position": [0.39, 0.48],
                    "color": "#f0c64f"
                },
                {
                    "event_id": "dash_shake",
                    "effect_type": "screen_shake",
                    "start_frame": 15,
                    "end_frame": 22,
                    "intensity": 1.15
                },
                {
                    "event_id": "dash_flash",
                    "effect_type": "flash",
                    "start_frame": 15,
                    "end_frame": 18,
                    "intensity": 0.7
                }
            ]
        }]
    }
    save(project / "animation_system.json", animation)
    return project


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    print(build(parser.parse_args().project.resolve()))
