"""Create a cutout-comedy fixture from the existing character runtime fixture."""
from __future__ import annotations

import argparse
from pathlib import Path

from make_character_performance_fixture import build as build_base
from pipeline import read, save


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


def build(project: Path) -> Path:
    build_base(project)
    motion_path = project / "motion_plan.json"
    motion = read(motion_path)

    for shot in motion["shots"]:
        shot["performance"]["mode"] = "cutout-comedy"
        shot["performance"]["intent"] = "Static-first cutout comedy fixture; only explicit events may move characters."
        for performer in shot.get("character_performance", []):
            performer["events"] = []

    first = motion["shots"][0]
    lin = next(item for item in first["character_performance"] if item["character_id"] == "lin")
    lin["role"] = "speaker"
    lin["events"] = [event("lin-challenge", "head_forward", 3, 6, 10, 14, 0.9)]

    second = motion["shots"][1]
    bo = next(item for item in second["character_performance"] if item["character_id"] == "bo")
    bo["role"] = "listener"
    bo["expression"] = "surprised"
    bo["events"] = [event("bo-recoil", "lean_back", 4, 7, 12, 17, 1.0)]

    third = motion["shots"][2]
    lin = next(item for item in third["character_performance"] if item["character_id"] == "lin")
    lin["role"] = "idle"
    lin["events"] = [event("lin-breakdown", "body_shake", 3, 6, 12, 18, 1.0)]
    bo = next(item for item in third["character_performance"] if item["character_id"] == "bo")
    bo["role"] = "listener"
    bo["events"] = [event("bo-double-take", "double_take", 3, 7, 12, 18, 0.9)]

    save(motion_path, motion)
    return project


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    print(build(parser.parse_args().project.resolve()))
