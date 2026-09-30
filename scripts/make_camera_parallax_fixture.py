"""Build a synthetic five-depth scene for the Camera/Parallax Remotion test."""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw

from pipeline import ROOT, read, save


WIDTH, HEIGHT = 960, 540
LAYER_SPECS = (
    ("bg", "background", "background", 0, "Opaque base environment"),
    ("sky", "effects", "sky", 5, "Moon and stars"),
    ("mid", "effects", "midground", 10, "Distant ridge and trees"),
    ("subject", "effects", "character", 20, "Stable geometric subject used as camera focus"),
    ("fg", "foreground", "foreground", 30, "Near branches and stones"),
)


def _draw_layers(folder: Path, variation: int) -> None:
    folder.mkdir(parents=True, exist_ok=True)

    background = Image.new("RGBA", (WIDTH, HEIGHT), "#26374a")
    draw = ImageDraw.Draw(background)
    draw.rectangle((0, 330, WIDTH, HEIGHT), fill="#52685d")
    draw.rectangle((0, 440, WIDTH, HEIGHT), fill="#354c45")
    background.save(folder / "bg.png")

    sky = Image.new("RGBA", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(sky)
    draw.ellipse((740, 58, 822, 140), fill="#f2dfad")
    for index in range(32):
        x = (index * 173 + 41) % WIDTH
        y = 26 + (index * 71) % 230
        radius = 2 + index % 3
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill="#e8e3cf")
    sky.save(folder / "sky.png")

    midground = Image.new("RGBA", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(midground)
    draw.polygon([(-80, 380), (90, 278), (260, 360), (430, 250), (610, 345), (770, 270), (1040, 365), (1040, 560), (-80, 560)], fill="#65796d")
    for x, y, width, height in [(90, 355, 75, 150), (270, 340, 92, 185), (770, 350, 86, 180), (900, 380, 70, 130)]:
        draw.polygon([(x, y - height), (x - width, y), (x + width, y)], fill="#334e49")
        draw.rectangle((x - 7, y - 4, x + 7, y + 75), fill="#493f38")
    midground.save(folder / "mid.png")

    subject = Image.new("RGBA", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(subject)
    cx, cy = 500 + variation * 3, 335
    draw.ellipse((cx - 34, cy - 112, cx + 34, cy - 44), fill="#e6a45f", outline="#182a35", width=5)
    draw.polygon([(cx - 25, cy - 94), (cx - 45, cy - 148), (cx - 2, cy - 116)], fill="#e6a45f", outline="#182a35")
    draw.polygon([(cx + 20, cy - 97), (cx + 48, cy - 142), (cx + 38, cy - 80)], fill="#e6a45f", outline="#182a35")
    draw.ellipse((cx - 17, cy - 85, cx - 10, cy - 75), fill="#182a35")
    draw.ellipse((cx + 10, cy - 85, cx + 17, cy - 75), fill="#182a35")
    draw.polygon([(cx - 42, cy - 45), (cx + 42, cy - 45), (cx + 58, cy + 54), (cx - 58, cy + 54)], fill="#5282a0", outline="#182a35")
    draw.line((cx - 25, cy + 50, cx - 43, cy + 112), fill="#e6a45f", width=18)
    draw.line((cx + 25, cy + 50, cx + 43, cy + 112), fill="#e6a45f", width=18)
    subject.save(folder / "subject.png")

    foreground = Image.new("RGBA", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(foreground)
    draw.polygon([(0, 540), (0, 390), (58, 348), (100, 540)], fill="#233d38")
    draw.polygon([(0, 402), (95, 372), (148, 345), (100, 393), (30, 430)], fill="#35594a")
    draw.polygon([(960, 540), (960, 405), (906, 360), (860, 540)], fill="#29473e")
    for x, y, radius in [(150, 500, 27), (330, 525, 19), (745, 505, 30), (850, 530, 23)]:
        draw.ellipse((x - radius, y - radius // 2, x + radius, y + radius // 2), fill="#354d48")
    foreground.save(folder / "fg.png")

    master = background.copy()
    for name in ("sky.png", "mid.png", "subject.png", "fg.png"):
        master.alpha_composite(Image.open(folder / name).convert("RGBA"))
    master.save(folder.parent / "master.png")


def build(project: Path) -> Path:
    if project.exists():
        raise FileExistsError(f"Use a new output directory: {project}")
    project.mkdir(parents=True)

    data = {name: read(ROOT / "examples/library" / f"{name}.json") for name in (
        "production_brief", "characters", "storyboard", "motion_plan",
    )}
    project_id = "camera-parallax-fixture"
    for item in data.values():
        item["project_id"] = project_id

    brief = data["production_brief"]
    brief.update({
        "title": "Camera and parallax runtime fixture",
        "original_content": "A layered landscape holds still for a wide establishing view. The camera advances toward the figure. The camera pans right across the path.",
        "content_preservation": ["Keep the simple subject and layered landscape readable."],
        "setting": {"place": "Synthetic layered landscape", "era": "timeless", "culture": "technical test"},
        "visual_language": "Simple, high-contrast geometric shapes for renderer verification.",
        "tone": "neutral technical test",
        "format": {"width": WIDTH, "height": HEIGHT, "fps": 24, "duration_frames": 144},
        "assumptions": ["All artwork is synthetic test geometry, not production art."],
    })
    data["characters"]["characters"] = []

    board = data["storyboard"]
    board["scenes"] = [{
        "id": "layered-landscape",
        "space": "Sky above a far ridge, midground trees, a centered figure and near branches.",
        "time": "night",
        "lighting": "Moonlit test palette with clear silhouettes.",
        "anchors": ["moon upper-right", "figure near center", "near branches at both edges"],
    }]
    base_beats = [
        ("b1", "A layered landscape holds still for a wide establishing view.", "Establish the five depth planes.", "stillness"),
        ("b2", "The camera advances toward the figure.", "Make the subject larger while the planes scale at different rates.", "focus"),
        ("b3", "The camera pans right across the path.", "Keep the figure readable while near and far layers separate.", "movement"),
    ]
    board["beats"] = [{"id": item[0], "source_excerpt": item[1], "change": item[2], "emotion": item[3]} for item in base_beats]
    view_specs = [
        ("wide", "center", "static", "The full five-plane landscape remains still."),
        ("medium", "center", "push_in", "The camera pushes toward the figure without moving the artwork."),
        ("medium", "right_third", "pan_right", "The camera pans right; the figure remains readable as depth layers drift at different rates."),
    ]
    layer_specs = []
    for layer_id, role, depth, z, description in LAYER_SPECS:
        layer_specs.append({"id": layer_id, "role": role, "elements": description, "method": "extract", "reason": f"Camera test depth: {depth}"})

    shots = []
    for index, (shot_size, composition_tag, motion, purpose) in enumerate(view_specs):
        shot_id = f"shot_{index + 1:03d}"
        next_id = f"shot_{index + 2:03d}" if index < 2 else None
        shots.append({
            "id": shot_id,
            "source_panel": f"camera-test-{index + 1}",
            "beat_id": f"b{index + 1}",
            "duration_frames": 48,
            "purpose": purpose,
            "transition": "cut",
            "setting": "Synthetic layered landscape",
            "shot_size": shot_size,
            "angle": "eye_level",
            "composition": purpose,
            "composition_tag": composition_tag,
            "characters": [],
            "continuity": "The same test landscape assets continue across all three camera demonstrations.",
            "master": f"shots/{shot_id}/master.png",
            "layers": [dict(layer) for layer in layer_specs],
            "repetition_exception": "Repeated views are intentional: this fixture isolates the camera transform.",
            "dialogue": [],
            "direction": {
                "scene_id": "layered-landscape",
                "camera_position": motion,
                "background_view": f"camera-test-view-{index + 1}",
                "view_id": f"camera-test-view-{index + 1}",
                "incoming_state": "The same neutral scene is ready for a camera test.",
                "outgoing_state": "The current camera movement is complete.",
                "micro_actions": "Subject art deliberately holds still; this test isolates camera and parallax.",
                "cut_reason": "Switch to the next camera behavior.",
                "next_shot_id": next_id,
                "handoff": "Keep the same layered world while changing only the authored camera state.",
                "reaction_hold_frames": 0,
                "listening_reactions": [],
            },
        })
    board["shots"] = shots

    motions = []
    for index, (_, _, motion, _) in enumerate(view_specs):
        shot_id = f"shot_{index + 1:03d}"
        camera = {"type": "static", "parallax_enabled": False}
        if motion == "push_in":
            camera = {
                "type": "push_in",
                "focus_target": {"id": "subject", "x": 500, "y": 335},
                "from": {"x": 500, "y": 335, "zoom": 1.0},
                "to": {"x": 500, "y": 335, "zoom": 1.45},
                "easing": "easeInOut",
                "screen_target": {"x": 500 / WIDTH, "y": 0.62},
                "parallax_enabled": True,
            }
        elif motion == "pan_right":
            camera = {
                "type": "pan_right",
                "focus_target": {"id": "subject", "x": 480, "y": 335},
                "from": {"x": 480, "y": 335, "zoom": 1.2},
                "to": {"x": 540, "y": 335, "zoom": 1.2},
                "easing": "easeInOut",
                "screen_target": {"x": 0.5, "y": 0.62},
                "parallax_enabled": True,
            }
        plan_layers = []
        for layer_id, _role, depth, z, _description in LAYER_SPECS:
            plan_layers.append({
                "layer_id": layer_id,
                "asset": f"shots/{shot_id}/layers/{layer_id}.png",
                "depth": depth,
                "z": z,
                "from": {"x": 0, "y": 0, "scale": 1},
                "to": {"x": 0, "y": 0, "scale": 1},
            })
        motions.append({
            "shot_id": shot_id,
            "start_frame": index * 48,
            "duration_frames": 48,
            "transition": "cut",
            "performance": {
                "mode": "sequential-comic",
                "intent": "Hold the simple subject still so the test isolates camera motion.",
                "static_reason": "Synthetic camera fixture; character performance is outside this phase.",
                "reviewed": False,
            },
            "camera": camera,
            "layers": plan_layers,
            "review": {
                "master_alignment": False,
                "background_completed": False,
                "motion_bounds_checked": False,
                "notes": "Synthetic camera/parallax test geometry; not production art.",
            },
        })
        _draw_layers(project / "shots" / shot_id / "layers", index)

    motion_plan = data["motion_plan"]
    motion_plan.update({"version": "0.4", "asset_mode": "fixture", "shots": motions})
    for name, value in data.items():
        save(project / f"{name}.json", value)
    return project


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    print(build(args.project.resolve()))
