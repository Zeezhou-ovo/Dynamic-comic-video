#!/usr/bin/env python3
"""Validate the renderer-agnostic plan used by the painted-frame route."""
import json
import math
import sys
from pathlib import Path

CAMERA_SHOTS = {"wide", "medium", "close_up"}
CAMERA_MOTIONS = {"static", "push_in", "pull_out", "pan", "follow", "reveal"}
DEPTH_LAYERS = ("foreground", "character", "midground", "background", "sky")
LIGHTING_CHANGES = {"none", "subtle", "strong"}
TRANSITIONS = {"cut", "dissolve", "fade", "foreground_wipe"}
EMPHASIS = {"shot_size_change", "push_in", "character_reaction", "lighting_change", "intentional_pause"}

def fail(message):
    print(f"ERROR: {message}")
    raise SystemExit(1)

def positive_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0

def text_value(value):
    return isinstance(value, str) and bool(value.strip())

def validate_animation_plan(shot, index):
    card = shot.get("animation_plan")
    if not isinstance(card, dict): fail(f"shot {index} needs animation_plan before rendering")
    keys = ("narrative_goal", "visual_focus", "camera_shot", "camera_motion", "primary_action",
            "secondary_motion", "depth_layers", "parallax_enabled", "ambient_motion",
            "lighting_change", "pause_before", "pause_after", "transition", "important_moment", "emphasis")
    for key in keys:
        if key not in card: fail(f"shot {index} animation_plan missing: {key}")
    for key in ("narrative_goal", "visual_focus", "primary_action"):
        if not text_value(card[key]): fail(f"shot {index} needs non-empty {key}")
    for key, choices in (("camera_shot", CAMERA_SHOTS), ("camera_motion", CAMERA_MOTIONS),
                         ("lighting_change", LIGHTING_CHANGES), ("transition", TRANSITIONS)):
        if card[key] not in choices: fail(f"shot {index} has invalid {key}: {card[key]}")
    for key, limit in (("secondary_motion", 2), ("ambient_motion", 3)):
        value = card[key]
        if not isinstance(value, list) or len(value) > limit or any(not text_value(item) for item in value):
            fail(f"shot {index} {key} must be a list of at most {limit} non-empty motions")
    layers = card["depth_layers"]
    if not isinstance(layers, dict) or set(layers) != set(DEPTH_LAYERS):
        fail(f"shot {index} depth_layers must explicitly define {', '.join(DEPTH_LAYERS)}")
    if any(value is not None and not text_value(value) for value in layers.values()):
        fail(f"shot {index} depth_layers entries must be text or null")
    if not isinstance(card["parallax_enabled"], bool): fail(f"shot {index} parallax_enabled must be boolean")
    moving = card["camera_motion"] != "static"
    if moving and not text_value(card.get("camera_purpose")):
        fail(f"shot {index} camera motion needs a narrative camera_purpose")
    if moving and sum(value is not None for value in layers.values()) > 1 and not card["parallax_enabled"]:
        fail(f"shot {index} moving camera with multiple depth layers requires parallax")
    for key in ("pause_before", "pause_after"):
        value = card[key]
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 0:
            fail(f"shot {index} {key} must be non-negative seconds")
    if card["pause_before"] + card["pause_after"] > float(shot["end"]) - float(shot["start"]):
        fail(f"shot {index} pauses exceed shot duration")
    if not isinstance(card["important_moment"], bool): fail(f"shot {index} important_moment must be boolean")
    emphasis = card["emphasis"]
    if not isinstance(emphasis, list) or any(item not in EMPHASIS for item in emphasis):
        fail(f"shot {index} emphasis must use approved visual emphasis modes")
    if card["important_moment"] and not emphasis: fail(f"shot {index} important moment needs visual emphasis")
    return moving

def validate(path):
    source = Path(path)
    if not source.exists(): fail(f"plan not found: {source}")
    try: plan = json.loads(source.read_text())
    except json.JSONDecodeError as exc: fail(f"invalid JSON: {exc}")
    for key in ("fps", "duration", "width", "height", "shots"):
        if key not in plan: fail(f"missing top-level field: {key}")
    if not isinstance(plan["shots"], list) or not plan["shots"]: fail("shots must be a non-empty list")
    if any(not positive_number(plan[key]) for key in ("fps", "duration", "width", "height")):
        fail("fps, duration, width and height must be positive")
    if plan.get("planVersion", 1) not in (1, 2, 3): fail("unsupported planVersion")
    previous = 0.0
    moving_count = 0
    static_without_reason = []
    for index, shot in enumerate(plan["shots"]):
        required = ("start", "end", "action") if plan.get("planVersion") == 3 else ("start", "end", "action", "camera")
        for key in required:
            if key not in shot: fail(f"shot {index} missing field: {key}")
        try: start, end = float(shot["start"]), float(shot["end"])
        except (TypeError, ValueError): fail(f"shot {index} start and end must be numbers")
        if not math.isfinite(start) or not math.isfinite(end): fail(f"shot {index} has non-finite timing")
        if start < previous or end <= start: fail(f"shot {index} is not ordered or has no duration")
        if end > float(plan["duration"]): fail(f"shot {index} ends after duration")
        if any(float(t) < start or float(t) > end for t in shot.get("beatEvents", [])):
            fail(f"shot {index} has beatEvents outside its time range")
        if plan.get("planVersion") == 2:
            director = shot.get("director")
            if not isinstance(director, dict): fail(f"shot {index} needs a director card")
            for key in ("narrativeGoal", "visualFocus", "primaryMotion", "secondaryMotions",
                        "ambientMotions", "depth", "lighting", "effects", "timing", "transition"):
                if key not in director: fail(f"shot {index} director card missing: {key}")
            if not director["narrativeGoal"] or not director["visualFocus"] or not director["primaryMotion"]:
                fail(f"shot {index} needs a narrative goal, focus and primary motion")
            if not isinstance(director["secondaryMotions"], list) or len(director["secondaryMotions"]) > 2:
                fail(f"shot {index} allows at most two secondary motions")
            if not isinstance(director["ambientMotions"], list):
                fail(f"shot {index} ambientMotions must be a list")
            if not isinstance(director["timing"], dict):
                fail(f"shot {index} timing must be an object")
            if shot["camera"] not in ("STATIC", "PUSH_IN", "PULL_OUT", "PAN_LEFT", "PAN_RIGHT", "FOLLOW", "REVEAL", "TILT", "ORBIT"):
                fail(f"shot {index} has unknown camera mode")
        if plan.get("planVersion") == 3:
            if not text_value(shot["action"]): fail(f"shot {index} needs an action")
            if abs(start - previous) > 1e-6: fail(f"shot {index} leaves a timeline gap")
            moving = validate_animation_plan(shot, index)
            if moving: moving_count += 1
            elif not text_value(shot["animation_plan"].get("static_necessity")):
                static_without_reason.append(index)
        previous = end
    if plan.get("planVersion") == 3:
        if abs(previous - float(plan["duration"])) > 1e-6: fail("shots must cover the full duration")
        if moving_count * 2 < len(plan["shots"]) and static_without_reason:
            fail(f"fewer than half of shots move; static shots {static_without_reason} need static_necessity")
    elif previous < float(plan["duration"]): print("WARNING: shots do not cover the full duration")
    print(f"OK: {len(plan['shots'])} shots, {plan['fps']} fps, {plan['duration']} seconds")

if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "validate":
        print("Usage: python3 scripts/procedural.py validate production/plan.json")
        raise SystemExit(2)
    validate(sys.argv[2])
