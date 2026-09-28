#!/usr/bin/env python3
"""Validate the renderer-agnostic plan used by the painted-frame route."""
import json
import sys
from pathlib import Path

def fail(message):
    print(f"ERROR: {message}")
    raise SystemExit(1)

def validate(path):
    source = Path(path)
    if not source.exists(): fail(f"plan not found: {source}")
    try: plan = json.loads(source.read_text())
    except json.JSONDecodeError as exc: fail(f"invalid JSON: {exc}")
    for key in ("fps", "duration", "width", "height", "shots"):
        if key not in plan: fail(f"missing top-level field: {key}")
    if not isinstance(plan["shots"], list) or not plan["shots"]: fail("shots must be a non-empty list")
    if plan["fps"] <= 0 or plan["duration"] <= 0: fail("fps and duration must be positive")
    previous = 0.0
    for index, shot in enumerate(plan["shots"]):
        for key in ("start", "end", "action", "camera"):
            if key not in shot: fail(f"shot {index} missing field: {key}")
        start, end = float(shot["start"]), float(shot["end"])
        if start < previous or end <= start: fail(f"shot {index} is not ordered or has no duration")
        if end > float(plan["duration"]): fail(f"shot {index} ends after duration")
        if any(float(t) < start or float(t) > end for t in shot.get("beatEvents", [])):
            fail(f"shot {index} has beatEvents outside its time range")
        previous = end
    if previous < float(plan["duration"]): print("WARNING: shots do not cover the full duration")
    print(f"OK: {len(plan['shots'])} shots, {plan['fps']} fps, {plan['duration']} seconds")

if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "validate":
        print("Usage: python3 scripts/procedural.py validate production/plan.json")
        raise SystemExit(2)
    validate(sys.argv[2])
