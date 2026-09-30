"""Build Phase 4 Scene/Composition and Phase 3→4 dialogue render projects."""
from __future__ import annotations

import argparse
from pathlib import Path

from make_scene_composition_fixture import build as build_scene_fixture
from pipeline import read, save


def _shot(instance, source, intent, camera, emphasis, *beats, **extra):
    return {"instance_id": instance, "source_shot_id": source, "shot_intent": intent,
            "camera_intent": camera, "emphasis": emphasis, **extra, "beats": list(beats)}


def _pause(beat_id, duration):
    return {"beat_id": beat_id, "kind": "pause", "duration_frames": duration,
            "pause_before": 0, "pause_after": 0}


def _dialogue(beat_id, speaker, text, duration, intent, performance, listeners=(), emphasis="normal"):
    return {"beat_id": beat_id, "kind": "dialogue", "speaker": speaker, "text": text,
            "intent": intent, "emotion": "curious" if intent == "ask" else "warm",
            "emphasis": emphasis, "listeners": list(listeners), "performance_intent": performance,
            "duration_frames": duration, "pause_before": 0, "pause_after": 3}


def _reaction(beat_id, target, reaction="interested", hold=20):
    return {"beat_id": beat_id, "kind": "reaction", "reaction_target": target,
            "reaction": reaction, "reaction_hold": hold, "pause_before": 0, "pause_after": 4}


def build(project: Path, kind: str):
    build_scene_fixture(project)
    data = read(project / "production_brief.json")
    if kind == "scene":
        shots = [
            _shot("p4_wide", "shot_001", "establishing_wide", "static", "normal",
                  _pause("wide_hold", 32), visible_objects=["book"]),
            _shot("p4_two_shot", "shot_002", "two_shot", "subtle_push", "normal",
                  _pause("shared_discovery", 30), visible_objects=["book"]),
            _shot("p4_medium_lin", "shot_003", "speaker_medium", "static", "normal",
                  _pause("lin_reads", 28), focus_character="lin"),
            _shot("p4_close_bo", "shot_004", "speaker_closeup", "subtle_push", "important",
                  _pause("bo_notices", 28), focus_character="bo"),
            _shot("p4_reaction_lin", "shot_005", "listener_reaction", "subtle_push", "awkward",
                  _reaction("lin_reacts", "lin", "surprised", 24), focus_character="lin"),
            _shot("p4_insert_book", "shot_003", "insert", "stronger_push", "reveal",
                  _pause("book_glow", 30), visible_characters=[], visible_objects=["book"], focus_object="book"),
            _shot("p4_emphasis_bo", "shot_004", "emphasis_push", "stronger_push", "important",
                  _dialogue("bo_line", "bo", "好像有什么东西在发光。", 32, "react", "neutral", ["lin"], "important"),
                  focus_character="bo"),
        ]
        title = "Phase 4 Scene Composition · seven framings"
    elif kind == "dialogue":
        shots = [
            _shot("p4_dialogue_two_shot", "shot_001", "two_shot", "subtle_push", "normal",
                  _dialogue("lin_question", "lin", "这本书怎么只有一页？", 46, "ask", "ask", ["bo"]),
                  visible_objects=["book"]),
            _shot("p4_dialogue_bo_medium", "shot_004", "speaker_medium", "static", "normal",
                  _dialogue("bo_explain", "bo", "你先把封面翻开看看。", 43, "explain", "explain_with_point", ["lin"]),
                  focus_character="bo", visible_objects=["book"]),
            _shot("p4_dialogue_lin_reaction", "shot_005", "listener_reaction", "subtle_push", "surprise",
                  _reaction("lin_realizes", "lin", "surprised", 24), focus_character="lin", visible_objects=["book"]),
        ]
        title = "Phase 4 · Director to Scene Composition dialogue"
    else:
        raise ValueError("kind must be scene or dialogue")
    plan = {"version": "0.1", "project_id": data["project_id"],
            "timing_source": "director_plan", "shots": shots}
    save(project / "director_plan.json", plan)
    brief = read(project / "production_brief.json")
    brief["title"] = title
    save(project / "production_brief.json", brief)
    return project


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=("scene", "dialogue"))
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    print(build(args.project.resolve(), args.kind))
