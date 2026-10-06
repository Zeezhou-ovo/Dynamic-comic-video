"""Pre-preview quality gate for dynamic comic projects.

The gate reports structural and timing risks without pretending to replace visual
review. ``--autofix`` only repairs safe timeline metadata bounds.
"""
import argparse
import json
from pathlib import Path
import wave


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def issue(report, severity, category, shot, message, fix=None):
    item = {"severity": severity, "category": category, "shot": shot, "message": message}
    if fix:
        item["fix"] = fix
    report["issues"].append(item)


# Pacing thresholds in seconds; converted to frames with the project fps.
# A shot may hold longer than these limits when the extra frames are authored
# as a reaction (``direction.reaction_hold_frames``) or carry a visible event.
MAX_IDLE_LEAD_SECONDS = 1.0
MAX_IDLE_TAIL_SECONDS = 1.0
MIN_PUNCHLINE_HOLD_SECONDS = 0.4
REVEAL_MAX_CUT_DELAY_SECONDS = 0.5   # cut to the reveal as the setup line ends
MIN_REVEAL_HOLD_SECONDS = 0.5        # let the audience see the reveal before the next line
TAIL_EVENT_KEYS = ("action_events", "expression_events", "visual_events", "sound_events")


def _seconds(frames, fps):
    return round(frames / fps, 2)


def _event_frames(timeline):
    """Yield (start, end) of every authored performance event in a timeline."""
    for key in TAIL_EVENT_KEYS:
        for event in timeline.get(key, []):
            start = event.get("start_frame")
            end = event.get("end_frame", start)
            if isinstance(start, int) and isinstance(end, int):
                yield start, max(start, end)


def _prop_starts(motion_shot):
    return [event["start_frame"] for layer in (motion_shot or {}).get("layers", [])
            for event in (layer.get("prop_motion") or {}).get("events", [])]


def _acted_between(timeline, motion_shot, start, end):
    """Something visible or audible begins in [start, end): an event or a prop motion."""
    return _has_event_in(timeline, start, end) or any(start <= frame < end for frame in _prop_starts(motion_shot))


def check_reveals_and_ending(report, board, motion, fps):
    """Reveal shots cut on the setup line and hold before speech; the final line gets a reaction."""
    motion_by_id = {item["shot_id"]: item for item in motion.get("shots", [])}
    shots = board["shots"]
    max_delay = round(REVEAL_MAX_CUT_DELAY_SECONDS * fps)
    for index, shot in enumerate(shots):
        reveal = shot.get("reveal")
        if not reveal:
            continue
        sid = shot["id"]
        motion_shot = motion_by_id.get(sid) or {}
        timeline = motion_shot.get("timeline") or {}
        if index:
            previous = shots[index - 1]
            lines = previous.get("dialogue") or []
            prev_timeline = (motion_by_id.get(previous["id"]) or {}).get("timeline") or {}
            cut = prev_timeline.get("cut_at_frame", previous["duration_frames"])
            if lines and cut - max(c["end_frame"] for c in lines) > max_delay:
                delay = cut - max(c["end_frame"] for c in lines)
                issue(report, "Major", "reveal", sid,
                      f"setup line in {previous['id']} ends {_seconds(delay, fps)}s before the cut to the reveal; cut as the line ends (≤ {_seconds(max_delay, fps)}s)",
                      f"shorten {previous['id']} after its last line")
        hold = reveal.get("hold_frames", round(MIN_REVEAL_HOLD_SECONDS * fps))
        lines = shot.get("dialogue") or []
        first = min((c["start_frame"] for c in lines), default=shot["duration_frames"])
        if first < hold:
            issue(report, "Major", "reveal", sid,
                  f"someone speaks {_seconds(first, fps)}s into the reveal ({reveal['what']}); hold at least {_seconds(hold, fps)}s first",
                  "start the first line later in the reveal shot")
        if not _acted_between(timeline, motion_shot, 0, max(1, first)):
            issue(report, "Minor", "reveal", sid,
                  "the reveal hold has no visible or audible event (prop motion, expression, sound)",
                  "let the revealed thing move or make a sound once")
    if shots and shots[-1].get("dialogue"):
        last = shots[-1]
        motion_shot = motion_by_id.get(last["id"]) or {}
        timeline = motion_shot.get("timeline") or {}
        end = max(c["end_frame"] for c in last["dialogue"])
        cut = timeline.get("cut_at_frame", last["duration_frames"])
        if not _acted_between(timeline, motion_shot, max(0, end - 2), max(cut, end)):
            issue(report, "Minor", "ending", last["id"],
                  "the video ends on the last line with no reaction; finish on a reaction beat (expression, prop, sound) before the cut",
                  "add a short reaction after the last line")


def _has_event_in(timeline, start, end):
    """True when an authored event begins inside [start, end), i.e. the hold is acted, not idle."""
    return any(start <= e_start < end for e_start, _ in _event_frames(timeline))


def _punchline_ends(shot, timeline):
    """Frames where a punchline line finishes inside this shot."""
    ends = set()
    dialogue = shot.get("dialogue", [])
    for cue in dialogue:
        if cue.get("emphasis") == "punchline" or cue.get("priority") == "punchline":
            ends.add(cue["end_frame"])
    for event in timeline.get("subtitle_events", []):
        if event.get("emphasis") == "punchline" or event.get("priority") == "punchline":
            ends.add(event.get("end_frame", 0))
    for event in timeline.get("visual_events", []):
        if event.get("priority") != "punchline":
            continue
        start = event.get("start_frame", 0)
        overlapping = [cue["end_frame"] for cue in dialogue if cue["start_frame"] <= start <= cue["end_frame"]]
        ends.add(max(overlapping) if overlapping else event.get("end_frame", start))
    return sorted(ends)


def check_pacing(report, board, motion, fps):
    """Report dead air, missing punchline holds and reverse shots sharing one background."""
    motion_by_id = {item["shot_id"]: item for item in motion.get("shots", [])}
    shots = board["shots"]
    max_lead = round(MAX_IDLE_LEAD_SECONDS * fps)
    max_tail = round(MAX_IDLE_TAIL_SECONDS * fps)
    min_hold = round(MIN_PUNCHLINE_HOLD_SECONDS * fps)
    silent_total = 0
    total = 0
    for index, shot in enumerate(shots):
        sid = shot["id"]
        duration = shot["duration_frames"]
        total += duration
        dialogue = sorted(shot.get("dialogue", []), key=lambda cue: cue["start_frame"])
        timeline = (motion_by_id.get(sid) or {}).get("timeline") or {}
        direction = shot.get("direction", {})
        cut_at = timeline.get("cut_at_frame", duration)
        if not isinstance(cut_at, int) or not 0 <= cut_at <= duration:
            cut_at = duration
        if not dialogue:
            continue
        spoken = sum(max(0, min(cue["end_frame"], cut_at) - cue["start_frame"]) for cue in dialogue)
        silent_total += max(0, cut_at - spoken)

        lead = dialogue[0]["start_frame"]
        if lead > max_lead and not _has_event_in(timeline, 0, lead):
            issue(report, "Minor", "pacing", sid,
                  f"{_seconds(lead, fps)}s of idle screen before the first line",
                  "start the line earlier, shorten the shot head, or author a visible action")

        last_end = max(cue["end_frame"] for cue in dialogue)
        tail = cut_at - last_end
        allowance = max_tail + int(direction.get("reaction_hold_frames") or 0)
        if tail > allowance and not _has_event_in(timeline, last_end, cut_at):
            issue(report, "Minor", "pacing", sid,
                  f"{_seconds(tail, fps)}s of idle screen after the last line (allowed {_seconds(allowance, fps)}s)",
                  "cut sooner, or turn the hold into an authored reaction")

        next_shot = shots[index + 1] if index + 1 < len(shots) else None
        for end in _punchline_ends(shot, timeline):
            later = [cue["start_frame"] for cue in dialogue if cue["start_frame"] >= end]
            if later:
                hold = min(later) - end
            elif next_shot and next_shot.get("dialogue"):
                hold = (cut_at - end) + min(cue["start_frame"] for cue in next_shot["dialogue"])
            else:
                continue
            if hold < min_hold:
                issue(report, "Major", "punchline", sid,
                      f"Punchline is followed by speech after {_seconds(hold, fps)}s; leave at least {_seconds(min_hold, fps)}s to land",
                      "add pause_after, reaction_hold_frames, or a silent reaction/reveal shot")

        if next_shot:
            here, there = direction, next_shot.get("direction", {})
            cast_here = {c.get("character_id") for c in shot.get("characters", [])}
            cast_there = {c.get("character_id") for c in next_shot.get("characters", [])}
            if (here.get("scene_id") and here.get("scene_id") == there.get("scene_id")
                    and len(cast_here) == 1 and len(cast_there) == 1 and cast_here != cast_there
                    and here.get("background_view") and here.get("background_view") == there.get("background_view")
                    and here.get("camera_position") != there.get("camera_position")):
                issue(report, "Minor", "reverse_shot", next_shot["id"],
                      "Shot/reverse-shot pair shares the same background view; the reverse angle should show the opposite side of the room",
                      "redraw the background from the reverse camera position or record a repetition_exception")
    if total:
        report["pacing"] = {"silent_frames": silent_total, "total_frames": total, "silent_ratio": round(silent_total / total, 3)}


def audio_frames(path, fps):
    try:
        with wave.open(str(path), "rb") as stream:
            return round(stream.getnframes() / stream.getframerate() * fps)
    except (OSError, wave.Error):
        return None


def scan(project, autofix=False):
    project = Path(project).resolve()
    brief = read(project / "production_brief.json")
    chars = read(project / "characters.json")
    board = read(project / "storyboard.json")
    motion = read(project / "motion_plan.json")
    fps = brief["format"]["fps"]
    by_id = {shot["id"]: shot for shot in board["shots"]}
    report = {
        "version": "0.1",
        "project_id": brief["project_id"],
        "status": "PASS",
        "checks": {},
        "issues": [],
        "automatic_corrections": [],
        "requires_user_review": ["pixel-level identity, anatomy, seams, and acting naturalness"],
    }
    identities = {c["id"]: c.get("identity", {}) for c in chars.get("characters", [])}
    scenes = {scene["id"] for scene in board.get("scenes", [])}
    previous_tags = []
    action_counts = {}
    sequential = motion.get("version") == "0.3" or any(
        (item.get("performance") or {}).get("mode") == "sequential-comic" for item in motion.get("shots", [])
    )

    for shot in board["shots"]:
        sid = shot["id"]
        direction = shot.get("direction", {})
        if sequential and direction.get("scene_id") not in scenes:
            issue(report, "Critical", "scene_continuity", sid, "Shot references an unknown scene space")
        if sequential and shot.get("transition") != "cut":
            issue(report, "Critical", "cut", sid, "Dynamic comic shot must use a direct CUT")
        previous_tags.append((shot.get("shot_size"), shot.get("composition_tag"), shot.get("setting")))
        if len(previous_tags) >= 3 and len(set(previous_tags[-3:])) == 1:
            issue(report, "Minor", "repetition", sid, "Three consecutive shots repeat the same visual tags")

        dialogue = shot.get("dialogue", [])
        last_end = 0
        for cue in dialogue:
            start, end = cue["start_frame"], cue["end_frame"]
            if start < last_end or not 0 <= start < end <= shot["duration_frames"]:
                issue(report, "Major", "subtitle_sync", sid, "Dialogue interval is outside the shot or overlaps another cue")
            last_end = end
            if cue.get("audio"):
                audio_path = project / cue["audio"]
                if audio_path.is_file():
                    frames = audio_frames(audio_path, fps)
                    if frames is not None and frames > shot["duration_frames"]:
                        issue(report, "Major", "audio", sid, "Audio is longer than its shot duration")

        motion_shot = next((item for item in motion["shots"] if item["shot_id"] == sid), None)
        if not motion_shot:
            issue(report, "Critical", "timeline", sid, "Motion shot is missing")
            continue
        timeline = motion_shot.get("timeline")
        if timeline:
            if timeline.get("duration_frames") != shot["duration_frames"]:
                old = timeline.get("duration_frames")
                if autofix:
                    timeline["duration_frames"] = shot["duration_frames"]
                    report["automatic_corrections"].append({"shot": sid, "field": "timeline.duration_frames", "from": old, "to": shot["duration_frames"]})
                else:
                    issue(report, "Major", "timeline", sid, "Timeline duration does not match shot duration", "set to shot duration")
            cut_at = timeline.get("cut_at_frame", shot["duration_frames"])
            if cut_at < 0 or cut_at > shot["duration_frames"]:
                if autofix:
                    if cut_at > shot["duration_frames"]:
                        timeline["cut_at_frame"] = shot["duration_frames"]
                        report["automatic_corrections"].append({"shot": sid, "field": "timeline.cut_at_frame", "from": cut_at, "to": shot["duration_frames"]})
                    else:
                        issue(report, "Major", "cut", sid, "CUT is before the shot start")
                else:
                    message = "CUT is later than the shot duration" if cut_at > shot["duration_frames"] else "CUT is before the shot start"
                    issue(report, "Major", "cut", sid, message, "clamp to shot duration" if cut_at > shot["duration_frames"] else None)
            for key in ("subtitle_events", "speech_intervals", "visual_events", "music_duck_events"):
                for event in timeline.get(key, []):
                    start = event.get("start_frame", 0)
                    end = event.get("end_frame", start + 1)
                    if start < 0 or end <= start or end > shot["duration_frames"]:
                        issue(report, "Major", "timeline", sid, f"{key} contains an out-of-bounds interval")
            for key in ("action_events", "expression_events", "sound_events"):
                for event in timeline.get(key, []):
                    phases = [event.get(name) for name in ("start_frame", "peak_frame", "settle_frame", "end_frame")]
                    if any(value is None for value in phases) or any(value < 0 or value > shot["duration_frames"] for value in phases):
                        issue(report, "Major", "timeline", sid, f"{key} contains an out-of-bounds event phase")
                    elif phases != sorted(phases):
                        issue(report, "Major", "timeline", sid, f"{key} contains event phases out of order")
            for event in timeline.get("blink_events", []):
                frame = event.get("frame", -1)
                if frame < 0 or frame >= shot["duration_frames"]:
                    issue(report, "Major", "timeline", sid, "blink_events contains an out-of-bounds frame")

        actions = 0
        visible_characters = {character.get("character_id") for character in shot.get("characters", [])}
        speech_speakers = {
            layer.get("acting", {}).get("speech", {}).get("speaker")
            for layer in motion_shot.get("layers", [])
            if layer.get("acting", {}).get("speech")
        }
        for cue in dialogue:
            speaker = cue.get("speaker")
            if speaker in visible_characters and speaker not in speech_speakers:
                issue(report, "Major", "mouth_sync", sid, f"Visible dialogue speaker {speaker} has no speech mouth layer")
        for layer in motion_shot.get("layers", []):
            acting = layer.get("acting", {})
            actions += len(acting.get("events", []))
            if acting.get("poses"):
                actions += max(0, len(acting["poses"]) - 2)
            if acting.get("speech") and not dialogue:
                issue(report, "Major", "mouth_sync", sid, "Mouth speech layer exists without dialogue timing")
            if motion_shot.get("performance", {}).get("mode") in ("sequential-comic", "fixed-camera-micro"):
                for key in ("from", "to"):
                    transform = layer.get(key, {})
                    if transform.get("x", 0) or transform.get("y", 0) or transform.get("scale", 1) != 1:
                        issue(report, "Major", "motion_naturalness", sid, "Fixed-camera shot contains whole-layer movement")
        action_counts[sid] = actions
        if actions > 2:
            issue(report, "Minor", "motion_density", sid, f"Shot contains {actions} acting events; ordinary dialogue usually needs 0–2")

    check_pacing(report, board, motion, fps)
    check_reveals_and_ending(report, board, motion, fps)

    for cid, identity in identities.items():
        anchors = identity.get("distinctive_features") or identity.get("anchors")
        if not anchors:
            issue(report, "Major", "character_consistency", None, f"Character {cid} has no recorded identity anchors")

    categories = {
        "character_consistency": "角色一致性",
        "scene_continuity": "场景连续性",
        "motion_naturalness": "动作自然度",
        "mouth_sync": "嘴型同步",
        "subtitle_sync": "字幕同步",
        "audio": "音频",
        "cut": "CUT 节奏",
        "repetition": "重复构图",
        "motion_density": "动作密度",
        "timeline": "统一时间轴",
        "pacing": "空白与节奏",
        "punchline": "笑点停顿",
        "reverse_shot": "正反打背景",
        "reveal": "揭示节奏",
        "ending": "结尾反应",
    }
    for key, label in categories.items():
        report["checks"][key] = "FIX" if any(i["category"] == key for i in report["issues"]) else "PASS"
    severities = [item["severity"] for item in report["issues"]]
    if "Critical" in severities:
        report["status"] = "BLOCKED"
    elif "Major" in severities:
        report["status"] = "FIX_REQUIRED"
    elif "Minor" in severities:
        report["status"] = "PASS_WITH_NOTES"
    report["summary"] = {"Critical": severities.count("Critical"), "Major": severities.count("Major"), "Minor": severities.count("Minor")}
    if autofix and report["automatic_corrections"]:
        save(project / "motion_plan.json", motion)
    save(project / "quality_report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    parser.add_argument("--autofix", action="store_true")
    args = parser.parse_args()
    report = scan(args.project, args.autofix)
    print(json.dumps({"status": report["status"], "summary": report["summary"], "report": str((args.project / "quality_report.json").resolve())}, ensure_ascii=False))
    return 1 if report["status"] in ("BLOCKED", "FIX_REQUIRED") else 0


if __name__ == "__main__":
    raise SystemExit(main())
