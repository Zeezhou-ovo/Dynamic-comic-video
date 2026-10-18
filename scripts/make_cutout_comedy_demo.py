"""Create a 12.5-second original cutout-comedy demo project with synthetic art."""
from __future__ import annotations

import argparse
from pathlib import Path

from make_character_performance_fixture import build as build_base
from pipeline import read, save

FPS = 24
DURATIONS = (72, 60, 60, 60, 48)
LINES = (
    ("lin", "你作业写完了吗？", 8, 56),
    ("bo", "写完了。", 8, 42),
    ("lin", "借我抄一下。", 8, 45),
    ("bo", "我写的是检讨。", 8, 46),
    (None, None, None, None),
)


def event(event_id, preset, start, peak, settle, end, amplitude=1.0, part=None):
    value = {
        "event_id": event_id,
        "preset": preset,
        "start_frame": start,
        "peak_frame": peak,
        "settle_frame": settle,
        "end_frame": end,
        "amplitude": amplitude,
        "easing": "easeInOut",
    }
    if part:
        value["part"] = part
    return value


def _resize_shot(board_shot, motion_shot, duration):
    board_shot["duration_frames"] = duration
    motion_shot["duration_frames"] = duration

    for layer in motion_shot["layers"]:
        acting = layer.get("acting")
        if acting and acting.get("keys"):
            acting["keys"][-1]["frame"] = duration - 1

    for performer in motion_shot.get("character_performance", []):
        if performer.get("root_keys"):
            performer["root_keys"][-1]["frame"] = duration - 1
        performer["events"] = []

    motion_shot["camera"] = {"type": "static", "parallax_enabled": False}


def build(project: Path) -> Path:
    build_base(project)

    brief = read(project / "production_brief.json")
    chars = read(project / "characters.json")
    board = read(project / "storyboard.json")
    motion = read(project / "motion_plan.json")

    project_id = "cutout-comedy-demo"
    for value in (brief, chars, board, motion):
        value["project_id"] = project_id

    brief.update({
        "title": "Cutout Comedy Demo — 作业",
        "original_content": "你作业写完了吗？ 写完了。 借我抄一下。 我写的是检讨。 两人停住，A反应过来。",
        "content_preservation": [
            "Two characters exchange four short lines.",
            "The last line is the punchline.",
            "Finish on a silent listener reaction rather than more dialogue.",
        ],
        "tone": "deadpan dialogue comedy",
        "visual_language": "Original flat geometric cutout-comedy test art; static-first acting with abrupt readable reactions.",
        "format": {
            "width": brief["format"]["width"],
            "height": brief["format"]["height"],
            "fps": FPS,
            "duration_frames": sum(DURATIONS),
        },
        "assumptions": [
            "Synthetic artwork is a technical demo, not production art.",
            "Dialogue has subtitle timing but no recorded voice in this fixture.",
        ],
    })

    beat_specs = [
        ("b1", "你作业写完了吗？", "A leans in to ask."),
        ("b2", "写完了。", "B answers without extra body motion."),
        ("b3", "借我抄一下。", "A points while making the request."),
        ("b4", "我写的是检讨。", "B delivers the punchline deadpan."),
        ("b5", "两人停住，A反应过来。", "A processes the punchline in silence."),
    ]
    board["beats"] = [
        {"id": bid, "source_excerpt": source, "change": change, "emotion": "comedy"}
        for bid, source, change in beat_specs
    ]

    cursor = 0
    for index, (board_shot, motion_shot, duration, line) in enumerate(
        zip(board["shots"], motion["shots"], DURATIONS, LINES)
    ):
        _resize_shot(board_shot, motion_shot, duration)
        board_shot["beat_id"] = f"b{index + 1}"
        board_shot["purpose"] = beat_specs[index][2]
        board_shot["transition"] = "cut"
        board_shot["repetition_exception"] = "Synthetic demo intentionally reuses one test room while changing performance beats."
        board_shot["dialogue"] = []
        board_shot["direction"]["camera_position"] = "static"
        board_shot["direction"]["reaction_hold_frames"] = 0
        board_shot["direction"]["listening_reactions"] = []
        motion_shot["start_frame"] = cursor
        motion_shot["transition"] = "cut"
        motion_shot["performance"] = {
            "mode": "cutout-comedy",
            "intent": beat_specs[index][2],
            "static_reason": "Static-first cutout comedy; motion only occurs through explicit performance events.",
            "reviewed": False,
        }

        speaker, text, start, end = line
        if speaker:
            cue = {
                "speaker": speaker,
                "text": text,
                "start_frame": start,
                "end_frame": end,
            }
            board_shot["dialogue"] = [cue]
            listener = "bo" if speaker == "lin" else "lin"
            board_shot["direction"]["reaction_hold_frames"] = max(0, duration - end)
            board_shot["direction"]["listening_reactions"] = [
                {"character_id": listener, "response": "hold and react only when explicitly directed"}
            ]

        performers = {p["character_id"]: p for p in motion_shot["character_performance"]}
        for performer in performers.values():
            performer.pop("pose", None)
            performer.pop("expression", None)
            performer["role"] = "idle"
            performer["events"] = []

        if speaker:
            performers[speaker]["role"] = "speaker"
            performers["bo" if speaker == "lin" else "lin"]["role"] = "listener"

        if index == 0:
            performers["lin"]["events"] = [
                event("lin-question", "head_forward", 12, 17, 25, 31, 0.9)
            ]
        elif index == 2:
            performers["lin"]["events"] = [
                event("lin-point", "point", 14, 19, 34, 41, 0.9, "right_arm")
            ]
        elif index == 3:
            performers["lin"]["expression"] = "surprised"
            performers["lin"]["events"] = [
                event("lin-recoil", "lean_back", 42, 47, 53, 57, 1.0)
            ]
            motion_shot["camera"] = {
                "type": "push_in",
                "focus_target": {"id": "characters", "x": 480, "y": 270},
                "from": {"x": 480, "y": 270, "zoom": 1.0},
                "to": {"x": 480, "y": 270, "zoom": 1.08},
                "screen_target": {"x": 0.5, "y": 0.5},
                "easing": "easeInOut",
                "parallax_enabled": True,
            }
        elif index == 4:
            performers["lin"]["role"] = "listener"
            performers["lin"]["expression"] = "surprised"
            performers["lin"]["events"] = [
                event("lin-double-take", "double_take", 5, 10, 18, 24, 1.0)
            ]
            performers["bo"]["role"] = "idle"
            board_shot["direction"]["reaction_hold_frames"] = duration
            board_shot["direction"]["listening_reactions"] = [
                {"character_id": "lin", "response": "double take, then hold completely still"}
            ]

        cursor += duration

    motion["version"] = "0.4"
    motion["asset_mode"] = "fixture"

    save(project / "production_brief.json", brief)
    save(project / "characters.json", chars)
    save(project / "storyboard.json", board)
    save(project / "motion_plan.json", motion)
    return project


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    print(build(parser.parse_args().project.resolve()))
