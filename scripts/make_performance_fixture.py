"""Synthetic project exercising the comic performance runtime end to end.

Builds the dialogue fixture, then adds: a rocking prop with an attached mouth,
a sound event, drawn comic effects, keyword subtitle emphasis and an audio
bed. CI prepares and renders it so renderer changes are caught early.

Usage: python scripts/make_performance_fixture.py <project>
"""
import argparse
from pathlib import Path

import make_sfx
from make_dialogue_fixture import build_dialogue
from pipeline import read, save


def build_performance(project):
    project = build_dialogue(Path(project))
    make_sfx.main([str(project)])
    motion = read(project / "motion_plan.json")
    shot = motion["shots"][0]
    duration = shot["duration_frames"]
    body = next(layer for layer in shot["layers"] if layer["layer_id"] == "body")
    body["prop_motion"] = {"pivot": [0.5, 0.9], "roll_radius": 120, "events": [
        {"event_id": "rock", "trigger": "information", "kind": "rock", "start_frame": 0, "end_frame": 30,
         "amplitude_deg": 3, "period_frames": 16, "decay_frames": 14, "description": "settling rock"},
        {"event_id": "lean", "trigger": "speech", "kind": "lean", "start_frame": 32, "end_frame": duration,
         "amplitude_deg": -2, "description": "one lean back"}]}
    for layer in shot["layers"]:
        if layer["layer_id"] != "body" and layer["z"] > body["z"] and layer["layer_id"] != "bg":
            layer["attach_to"] = "body"
    shot["timeline"] = {
        "scene_id": "test-room", "duration_frames": duration, "subtitle_events": [], "speech_intervals": [],
        "action_events": [], "expression_events": [], "blink_events": [], "cut_at_frame": duration,
        "sound_events": [{"event_id": "creak", "trigger": "action", "start_frame": 1, "peak_frame": 1, "settle_frame": 3,
                          "end_frame": 9, "description": "prop creak", "asset": "audio/sfx/creak.wav", "volume": 0.6}],
        "visual_events": [
            {"event_id": "drop", "priority": "emotion", "effect_type": "sweat_drop", "start_frame": 4, "end_frame": 24,
             "description": "sweat drop", "position": [0.62, 0.22], "size": 0.07},
            {"event_id": "lines", "priority": "punchline", "effect_type": "black_line", "start_frame": 30, "end_frame": duration,
             "description": "speechless lines", "position": [0.5, 0.18], "size": 0.1},
            {"event_id": "word", "priority": "emphasis", "effect_type": "subtitle_emphasis", "start_frame": 0, "end_frame": duration,
             "description": "keyword", "keyword": "mouth"},
        ],
    }
    motion["audio_bed"] = {"asset": "audio/sfx/room_tone.wav", "volume": 0.15}
    save(project / "motion_plan.json", motion)
    return project


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    print(build_performance(args.project))


if __name__ == "__main__":
    main()
