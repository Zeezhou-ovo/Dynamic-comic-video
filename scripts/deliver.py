"""Run the local delivery gate for a dynamic-comic project.

The gate combines contract validation, the pre-preview quality report, human
visual review evidence, the revision ledger, and a local ffprobe inspection of
the final MP4.  It never installs packages, uploads files, or changes project
inputs.  A report is written even when delivery is blocked so the next action
is explicit and repeatable.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from pipeline import validate
from project_state import (
    _read_visual_review,
    _resolve_preview_reference,
    _visual_review_issues,
    file_sha256,
    open_revision_entries,
    source_fingerprint,
)


PASS_QUALITY_STATUSES = {"PASS", "PASS_WITH_NOTES"}
# Short-video platforms normalise speech-led clips to roughly -14 LUFS; quieter
# uploads sound weak next to neighbouring videos. These are advisory targets.
TARGET_LUFS = -14.0
LUFS_TOLERANCE = 2.0
MAX_TRUE_PEAK_DBTP = -1.0
DIGITAL_SILENCE_DB = -60
MAX_DIGITAL_SILENCE_RATIO = 0.25


def _which(command):
    """Resolve a local executable on Windows and POSIX without shell lookup."""
    names = [command]
    if os.name == "nt":
        names.extend([f"{command}.exe", f"{command}.cmd"])
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    return None


def _fps(value):
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and "/" in value:
        numerator, denominator = value.split("/", 1)
        try:
            return float(numerator) / float(denominator)
        except (ValueError, ZeroDivisionError):
            return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _probe_media(path):
    """Read the playable video stream metadata with the local ffprobe binary."""
    command = _which("ffprobe")
    if not command:
        raise RuntimeError("ffprobe is required to prove that the delivery MP4 is playable")
    result = subprocess.run(
        [
            command,
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type,width,height,avg_frame_rate:format=duration",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        message = (result.stderr or "ffprobe failed").strip()
        raise RuntimeError(message)
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError("ffprobe returned invalid JSON") from error
    streams = [item for item in data.get("streams", []) if item.get("codec_type") == "video"]
    if not streams:
        raise RuntimeError("MP4 contains no video stream")
    stream = streams[0]
    duration = (data.get("format") or {}).get("duration")
    try:
        duration = float(duration)
    except (TypeError, ValueError):
        duration = None
    return {
        "width": stream.get("width"),
        "height": stream.get("height"),
        "fps": _fps(stream.get("avg_frame_rate")),
        "duration_seconds": duration,
    }


def _measure_audio(path):
    """Measure integrated loudness, true peak and digital silence with local ffmpeg.

    Returns None when the file has no audio stream.
    """
    command = _which("ffmpeg")
    if not command:
        raise RuntimeError("ffmpeg not found; loudness was not measured")
    result = subprocess.run(
        [
            command, "-hide_banner", "-nostats", "-i", str(path), "-vn",
            "-af", f"ebur128=peak=true,silencedetect=n={DIGITAL_SILENCE_DB}dB:d=0.3",
            "-f", "null", "-",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    log = result.stderr or ""
    if "does not contain any stream" in log or "matches no streams" in log or "Output file does not contain" in log:
        return None
    if result.returncode != 0:
        raise RuntimeError((log.strip().splitlines() or ["ffmpeg failed"])[-1])
    summary = log[log.rfind("Summary:"):] if "Summary:" in log else ""
    integrated = re.search(r"I:\s+(-?[\d.]+|-inf)\s+LUFS", summary)
    if not integrated:
        return None
    peak = re.search(r"True peak:\s+Peak:\s+(-?[\d.]+|-inf)\s+dBFS", summary)
    durations = [float(value) for value in re.findall(r"silence_duration:\s*([\d.]+)", log)]
    total = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", log)
    seconds = int(total.group(1)) * 3600 + int(total.group(2)) * 60 + float(total.group(3)) if total else None
    starts = [float(value) for value in re.findall(r"silence_start:\s*([\d.]+)", log)]
    if seconds and len(starts) > len(durations):  # silence runs to the end of the file
        durations.append(max(0.0, seconds - starts[-1]))
    as_float = lambda match: float(match.group(1)) if match and match.group(1) != "-inf" else None
    return {
        "integrated_lufs": as_float(integrated),
        "true_peak_dbtp": as_float(peak),
        "digital_silence_seconds": round(sum(durations), 3),
        "digital_silence_ratio": round(sum(durations) / seconds, 3) if seconds else None,
    }


def _check_audio(media_check):
    """Advisory loudness report; it never blocks delivery because targets vary by platform."""
    path = media_check.get("path")
    if media_check.get("status") != "PASS" or not path:
        return {"name": "audio_loudness", "status": "SKIPPED", "warnings": ["media check did not pass"]}
    try:
        measured = _measure_audio(path)
    except (OSError, RuntimeError) as error:
        return {"name": "audio_loudness", "status": "SKIPPED", "warnings": [str(error)]}
    if measured is None:
        return {"name": "audio_loudness", "status": "PASS", "warnings": [], "note": "no audio stream"}
    warnings = []
    lufs = measured["integrated_lufs"]
    if lufs is None or abs(lufs - TARGET_LUFS) > LUFS_TOLERANCE:
        shown = "silent" if lufs is None else f"{lufs:.1f} LUFS"
        warnings.append(f"integrated loudness {shown}; short-video target is {TARGET_LUFS:.0f} ± {LUFS_TOLERANCE:.0f} LUFS")
    peak = measured["true_peak_dbtp"]
    if peak is not None and peak > MAX_TRUE_PEAK_DBTP:
        warnings.append(f"true peak {peak:.1f} dBTP exceeds {MAX_TRUE_PEAK_DBTP:.0f} dBTP; risk of clipping after platform encoding")
    ratio = measured["digital_silence_ratio"]
    if ratio is not None and ratio > MAX_DIGITAL_SILENCE_RATIO:
        warnings.append(f"{ratio:.0%} of the video is digital silence; add low room tone or music bed under pauses")
    return {"name": "audio_loudness", "status": "PASS", "warnings": warnings, "measurement": measured}


def _check_contracts(root):
    try:
        data, errors, warnings = validate(root, assets=True)
    except Exception as error:  # malformed or missing input must become report evidence
        return {
            "name": "contracts",
            "status": "FAIL",
            "errors": [f"contract validation failed: {error}"],
            "warnings": [],
        }
    return {
        "name": "contracts",
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "warnings": warnings,
        "project_id": data.get("production_brief", {}).get("project_id"),
    }


def _check_quality(root):
    path = root / "quality_report.json"
    if not path.is_file():
        return {"name": "quality_gate", "status": "FAIL", "errors": ["quality_report.json"]}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return {"name": "quality_gate", "status": "FAIL", "errors": ["valid quality_report.json"]}
    status = data.get("status") if isinstance(data, dict) else None
    if status not in PASS_QUALITY_STATUSES:
        return {
            "name": "quality_gate",
            "status": "FAIL",
            "errors": [f"quality_report.json status must be PASS or PASS_WITH_NOTES (got {status!r})"],
            "reported_status": status,
        }
    return {
        "name": "quality_gate",
        "status": "PASS",
        "reported_status": status,
        "warnings": list(data.get("issues", [])) if status == "PASS_WITH_NOTES" else [],
    }


def _check_visual_review(root):
    path = root / "visual_review.json"
    if not path.is_file():
        return {"name": "visual_review", "status": "FAIL", "errors": ["visual_review.json"]}
    data = _read_visual_review(path)
    if data is None:
        return {"name": "visual_review", "status": "FAIL", "errors": ["valid visual_review.json"]}
    preview_reference = data.get("preview")
    preview = _resolve_preview_reference(root, preview_reference) if preview_reference else None
    issues = _visual_review_issues(root, path, preview_path=preview, data=data)
    if issues:
        return {
            "name": "visual_review",
            "status": "FAIL",
            "errors": issues,
            "review_status": data.get("review_status"),
        }
    return {
        "name": "visual_review",
        "status": "PASS",
        "review_status": data.get("review_status"),
        "preview": str(preview),
        "frames": len(data.get("frames", [])),
    }


def _check_revisions(root):
    entries, error = open_revision_entries(root)
    if error:
        return {"name": "revisions", "status": "FAIL", "errors": [error]}
    if entries:
        return {
            "name": "revisions",
            "status": "FAIL",
            "errors": [f"{item.get('id', '?')}: {item.get('feedback', 'open revision')}" for item in entries],
            "open": [item.get("id") for item in entries],
        }
    return {"name": "revisions", "status": "PASS", "open": []}


def _check_media(root, contract_check, visual_check):
    preview = visual_check.get("preview")
    if not preview:
        return {"name": "media", "status": "FAIL", "errors": ["approved visual review preview"]}
    path = Path(preview)
    if not path.is_file() or path.stat().st_size == 0:
        return {"name": "media", "status": "FAIL", "errors": [f"non-empty MP4: {path}"]}
    try:
        metadata = _probe_media(path)
    except (OSError, RuntimeError) as error:
        return {"name": "media", "status": "FAIL", "errors": [str(error)], "path": str(path)}

    brief = {}
    try:
        brief = json.loads((root / "production_brief.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        pass
    expected = (brief.get("format") or {}) if isinstance(brief, dict) else {}
    errors = []
    for key in ("width", "height"):
        if metadata.get(key) is None:
            errors.append(f"MP4 metadata missing {key}")
        elif expected.get(key) is not None and metadata.get(key) != expected[key]:
            errors.append(f"MP4 {key}={metadata.get(key)}; expected {expected[key]}")
    expected_fps = _fps(expected.get("fps"))
    if expected_fps:
        if metadata.get("fps") is None:
            errors.append("MP4 metadata missing fps")
        elif abs(metadata["fps"] - expected_fps) > 0.01:
            errors.append(f"MP4 fps={metadata['fps']}; expected {expected_fps}")
    duration_frames = expected.get("duration_frames")
    duration = metadata.get("duration_seconds")
    if duration_frames is not None and expected_fps:
        if duration is None:
            errors.append("MP4 metadata missing duration")
        else:
            expected_duration = float(duration_frames) / expected_fps
            tolerance = max(0.08, 1.0 / expected_fps + 0.03)
            if abs(duration - expected_duration) > tolerance:
                errors.append(f"MP4 duration={duration:.3f}s; expected {expected_duration:.3f}s ± {tolerance:.3f}s")
    if errors:
        return {
            "name": "media",
            "status": "FAIL",
            "errors": errors,
            "path": str(path),
            "sha256": file_sha256(path),
            "metadata": metadata,
        }
    return {
        "name": "media",
        "status": "PASS",
        "path": str(path),
        "sha256": file_sha256(path),
        "metadata": metadata,
    }


def check(project, output=None):
    """Run and persist the delivery gate, returning its JSON report."""
    root = Path(project).resolve()
    report_path = Path(output).resolve() if output else root / "delivery_report.json"
    checks = []
    contracts = _check_contracts(root)
    checks.append(contracts)
    checks.append(_check_quality(root))
    visual = _check_visual_review(root)
    checks.append(visual)
    checks.append(_check_revisions(root))
    media = _check_media(root, contracts, visual)
    checks.append(media)
    checks.append(_check_audio(media))
    blocking = [f"{item['name']}: {error}" for item in checks if item.get("status") == "FAIL" for error in item.get("errors", [])]
    report = {
        "version": "0.1",
        "project": str(root),
        "status": "PASS" if not blocking else "FAIL",
        "checks": checks,
        "blocking_issues": blocking,
        "source_fingerprint": source_fingerprint(root),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report["report"] = str(report_path)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run the local dynamic-comic delivery gate")
    parser.add_argument("project", type=Path)
    parser.add_argument("--output", type=Path, help="Where to write delivery_report.json")
    args = parser.parse_args(argv)
    report = check(args.project, args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
