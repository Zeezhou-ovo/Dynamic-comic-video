"""Storyboard continuity checks that run before any image is generated.

Two problems are much cheaper to catch on paper than after drawing:

* a character's posture or placement changes between shots (seated at the
  desk in one shot, standing in front of it in the next) without the change
  being shown or explained;
* a shot / reverse-shot pair (A faces right, then B faces left) drawn with
  the same wall behind both characters.

Posture fields on a storyboard character are optional: ``posture`` (enum),
``placement`` (free text, e.g. "behind the desk") and ``posture_change`` (how
the change is shown, on the shot where it first appears).
"""

import re

POSTURES = ("standing", "seated", "lying", "kneeling", "crouching", "riding", "other")
_NOTE = re.compile(r"[（(][^）)]*[）)]")


def _place(text):
    """Placement for comparison: notes in brackets ("(off screen)") are ignored."""
    return _NOTE.sub("", text or "").strip() or None


def _scene(shot):
    return (shot.get("direction") or {}).get("scene_id")


def posture_warnings(board):
    """Warnings for posture/placement changes between appearances in the same scene."""
    warnings = []
    last = {}
    for shot in board.get("shots", []):
        scene = _scene(shot)
        for character in shot.get("characters", []):
            cid = character["character_id"]
            state = (character.get("posture"), _place(character.get("placement")))
            previous = last.get(cid)
            if previous and previous["scene"] == scene and not character.get("posture_change"):
                (old_posture, old_place), old_shot = previous["state"], previous["shot"]
                if old_posture and state[0] and old_posture != state[0]:
                    warnings.append({
                        "shot": shot["id"], "check": "posture",
                        "message": f"{cid} is {old_posture} in {old_shot} but {state[0]} here; show the change or add posture_change",
                        "exception": shot.get("repetition_exception", ""),
                    })
                elif old_place and state[1] and old_place != state[1]:
                    warnings.append({
                        "shot": shot["id"], "check": "placement",
                        "message": f"{cid} moves from '{old_place}' ({old_shot}) to '{state[1]}' with no shown move; add posture_change",
                        "exception": shot.get("repetition_exception", ""),
                    })
            if state[0] or state[1]:
                last[cid] = {"scene": scene, "state": state, "shot": shot["id"]}
    return warnings


def reverse_pairs(board):
    """{shot_id: previous_shot} for adjacent single-character shots that answer each other."""
    pairs = {}
    shots = board.get("shots", [])
    for previous, shot in zip(shots, shots[1:]):
        here, before = shot.get("direction") or {}, previous.get("direction") or {}
        cast_now = {c["character_id"] for c in shot.get("characters", [])}
        cast_before = {c["character_id"] for c in previous.get("characters", [])}
        if (here.get("scene_id") and here.get("scene_id") == before.get("scene_id")
                and len(cast_now) == 1 and len(cast_before) == 1 and cast_now != cast_before
                and here.get("camera_position") != before.get("camera_position")):
            pairs[shot["id"]] = previous
    return pairs


def reverse_warnings(board):
    warnings = []
    for shot_id, previous in reverse_pairs(board).items():
        shot = next(item for item in board["shots"] if item["id"] == shot_id)
        if (shot.get("direction") or {}).get("background_view") == (previous.get("direction") or {}).get("background_view"):
            warnings.append({
                "shot": shot_id, "check": "reverse_background",
                "message": f"reverse angle of {previous['id']} lists the same background_view; describe the opposite side of the room before drawing",
                "exception": shot.get("repetition_exception", ""),
            })
    return warnings


def prompt_instructions(board, shot_id):
    """Plain-language continuity lines added to a shot's master prompt."""
    lines = []
    shots = board.get("shots", [])
    index = next(i for i, item in enumerate(shots) if item["id"] == shot_id)
    shot = shots[index]
    for character in shot.get("characters", []):
        cid = character["character_id"]
        posture, place = character.get("posture"), character.get("placement")
        if not (posture or place):
            continue
        earlier = next((c for s in reversed(shots[:index]) if _scene(s) == _scene(shot)
                        for c in s.get("characters", []) if c["character_id"] == cid and (c.get("posture") or c.get("placement"))), None)
        state = ", ".join(v for v in (posture, place) if v)
        if character.get("posture_change"):
            lines.append(f"{cid}: {state} — this changes from the previous appearance; show it as: {character['posture_change']}")
        elif earlier and (earlier.get("posture"), earlier.get("placement")) == (posture, place):
            lines.append(f"{cid}: {state} — same as the previous shot; keep it")
        else:
            lines.append(f"{cid}: {state}")
    previous = reverse_pairs(board).get(shot_id)
    if previous:
        avoid = (previous.get("direction") or {}).get("background_view")
        lines.append(
            f"Reverse angle of {previous['id']}: the camera now faces the opposite side of the room, so the background must be "
            f"what is behind the camera in {previous['id']}" + (f", not '{avoid}'" if avoid else "") + "; keep the eyelines facing each other."
        )
    return lines
