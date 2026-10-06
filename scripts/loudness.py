"""Static-gain loudness normalisation for rendered previews.

Measures integrated loudness with ffmpeg's EBU R128 analyser, then applies one
fixed gain (keeping the dialogue / room-tone / effect balance the timeline set)
and a peak limiter. The video stream is copied untouched. Runs locally only.
"""
import json
import shutil
import subprocess
from pathlib import Path

TARGET_LUFS = -14.0
PEAK_LIMIT = 0.84  # ≈ -1.5 dBFS sample peak; leaves room for AAC overshoot


def _ffmpeg():
    return shutil.which("ffmpeg")


def measure(path):
    """Integrated loudness in LUFS, or None when there is no measurable audio."""
    ffmpeg = _ffmpeg()
    if not ffmpeg:
        return None
    result = subprocess.run(
        [ffmpeg, "-hide_banner", "-nostats", "-i", str(path), "-vn",
         "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
        capture_output=True, text=True, check=False,
    )
    log = result.stderr or ""
    if result.returncode != 0 or "{" not in log:
        return None
    try:
        value = float(json.loads(log[log.rfind("{"):])["input_i"])
    except (ValueError, KeyError, json.JSONDecodeError):
        return None
    return value if value > -70 else None


def normalize(source, destination, target=TARGET_LUFS):
    """Copy ``source`` to ``destination`` with audio gained to ``target`` LUFS.

    Returns a small report. Falls back to a plain copy (and says why) when
    ffmpeg is missing or the file has no audio.
    """
    source, destination = Path(source), Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    measured = measure(source)
    if measured is None:
        shutil.copy2(source, destination)
        reason = "ffmpeg not found" if not _ffmpeg() else "no measurable audio"
        return {"applied": False, "reason": reason}
    gain = target - measured
    temporary = destination.with_name(destination.stem + ".loudness-tmp" + destination.suffix)
    result = subprocess.run(
        [_ffmpeg(), "-y", "-v", "error", "-i", str(source),
         "-map", "0:v:0", "-map", "0:a:0", "-c:v", "copy",
         "-af", f"volume={gain:.2f}dB,alimiter=limit={PEAK_LIMIT}:level=false",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(temporary)],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        temporary.unlink(missing_ok=True)
        shutil.copy2(source, destination)
        return {"applied": False, "reason": (result.stderr.strip().splitlines() or ["ffmpeg failed"])[-1]}
    temporary.replace(destination)
    return {"applied": True, "measured_lufs": round(measured, 1), "gain_db": round(gain, 2), "target_lufs": target}
