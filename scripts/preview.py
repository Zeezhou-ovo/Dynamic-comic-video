"""Run the local validation, quality gate, prepare and Remotion preview steps.

This is intentionally a thin orchestration layer.  It does not generate images,
upload files or change the user's story; it only prepares an external renderer
directory and copies its MP4 back to the production project.
"""
import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from project_state import file_sha256, open_revision_entries, source_fingerprint


ROOT = Path(__file__).resolve().parents[1]


def npm_command():
    """Return the platform-specific npm executable name."""
    return "npm.cmd" if os.name == "nt" else "npm"


def _safe_name(value):
    """Keep shot ids from becoming paths when used in review filenames."""
    return "".join(char if char.isalnum() or char in "-_" else "_" for char in value)


def review_points(project, shot=None):
    """Return first/middle/last local frames for each selected shot."""
    motion_path = Path(project) / "motion_plan.json"
    if not motion_path.is_file():
        return []
    data = json.loads(motion_path.read_text(encoding="utf-8"))
    shots = data.get("shots", [])
    if shot:
        shots = [item for item in shots if item.get("shot_id") == shot]
        if not shots:
            raise ValueError(f"Unknown shot: {shot}")
    points = []
    for item in shots:
        shot_id = item["shot_id"]
        duration = item["duration_frames"]
        local_frames = (0, max(0, (duration - 1) // 2), duration - 1)
        for position, frame in zip(("first", "middle", "last"), local_frames):
            points.append({
                "shot_id": shot_id,
                "position": position,
                "frame": frame,
                "global_frame": frame if shot else item["start_frame"] + frame,
                "filename": f"{_safe_name(shot_id)}_{position}.png",
            })
    return points


def steps(project, renderer, install=False, shot=None, stills=None, preflight=True):
    """Return the ordered commands used by :func:`run_preview`.

    Keeping command construction separate makes the one-click workflow easy to
    test without starting a renderer or touching a real production project.
    """
    python = sys.executable
    pipeline = ROOT / "scripts" / "pipeline.py"
    quality = ROOT / "scripts" / "quality_gate.py"
    validate_command = [python, str(pipeline), "validate", str(project), "--assets"]
    compile_command = [python, str(pipeline), "compile", str(project)]
    prepare_command = [python, str(pipeline), "prepare", str(project), "--renderer", str(renderer)]
    if shot:
        compile_command.extend(["--shot", shot])
        prepare_command.extend(["--shot", shot])
    result = []
    if preflight:
        result.extend([
            (validate_command, project),
            ([python, str(quality), str(project), "--autofix"], project),
            (list(validate_command), project),
        ])
    result.extend([(compile_command, project), (prepare_command, project)])
    if install:
        result.append(([npm_command(), "ci"], renderer))
    result.append(([npm_command(), "run", "render"], renderer))
    for point in stills or []:
        output = f"out/visual-review/{point['filename']}"
        result.append(([
            npm_command(), "run", "still-frame", "--", output,
            f"--frame={point['global_frame']}",
        ], renderer))
    return result


def _run_commands(commands):
    for command, cwd in commands:
        print("RUN:", " ".join(str(part) for part in command))
        subprocess.run(command, cwd=str(cwd), check=True)


def _asset_fingerprints(project):
    report_path = Path(project) / "asset_report.json"
    if not report_path.is_file():
        raise FileNotFoundError(f"Missing asset report after validation: {report_path}")
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise ValueError("asset_report.json is not valid JSON") from error
    shots = report.get("shots") if isinstance(report, dict) else None
    if not isinstance(shots, list):
        raise ValueError("asset_report.json must contain a shots array")
    result = {}
    for item in shots:
        if not isinstance(item, dict) or not item.get("shot_id") or not item.get("fingerprint"):
            raise ValueError("asset_report.json contains an invalid shot fingerprint")
        result[item["shot_id"]] = item["fingerprint"]
    return result


def run_incremental_preview(project, renderer, install=False):
    """Render only shots whose asset fingerprint is absent or changed in the local cache."""
    project = Path(project).resolve()
    renderer = Path(renderer).resolve()
    if not (project / "production_brief.json").is_file():
        raise FileNotFoundError(f"Not a production project: {project}")
    if renderer == project or renderer.is_relative_to(project):
        raise ValueError("Renderer must be outside the production project")
    renderer.mkdir(parents=True, exist_ok=True)
    _run_commands(steps(project, renderer, preflight=True)[:3])
    fingerprints = _asset_fingerprints(project)
    cache_root = project / "incremental-preview"
    cache_root.mkdir(parents=True, exist_ok=True)
    manifest_path = project / "incremental_preview.json"
    old = {}
    if manifest_path.is_file():
        try:
            previous = json.loads(manifest_path.read_text(encoding="utf-8"))
            old = {item["shot_id"]: item for item in previous.get("shots", []) if isinstance(item, dict) and item.get("shot_id")}
        except (OSError, ValueError, json.JSONDecodeError):
            old = {}
    if install:
        _run_commands([([npm_command(), "ci"], renderer)])
    rendered_shots = []
    cache_hits = []
    entries = []
    for shot_id, fingerprint in fingerprints.items():
        safe = _safe_name(shot_id)
        artifact = cache_root / f"{safe}.mp4"
        points = review_points(project, shot_id)
        old_entry = old.get(shot_id, {})
        old_frames = old_entry.get("frames", []) if isinstance(old_entry, dict) else []
        cache_valid = old_entry.get("fingerprint") == fingerprint and artifact.is_file() and len(old_frames) == len(points) and all(
            isinstance(frame, dict)
            and frame.get("image")
            and frame.get("sha256") == file_sha256(project / frame["image"])
            for frame in old_frames
        )
        cache_valid = cache_valid and old_entry.get("artifact_sha256") == file_sha256(artifact)
        if not cache_valid:
            _run_commands(steps(project, renderer, shot=shot_id, stills=points, preflight=False))
            rendered = renderer / "out" / "video.mp4"
            if not rendered.is_file():
                raise FileNotFoundError(f"Remotion did not produce {rendered}")
            shutil.copy2(rendered, artifact)
            frames = []
            for point in points:
                source = renderer / "out" / "visual-review" / point["filename"]
                if not source.is_file():
                    raise FileNotFoundError(f"Remotion did not produce {source}")
                relative = Path("incremental-preview") / "frames" / safe / point["filename"]
                destination = project / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
                frames.append({
                    "shot_id": point["shot_id"],
                    "position": point["position"],
                    "frame": point["frame"],
                    "image": relative.as_posix(),
                    "sha256": file_sha256(destination),
                })
            rendered_shots.append(shot_id)
        else:
            frames = old_frames
            cache_hits.append(shot_id)
        entries.append({
            "shot_id": shot_id,
            "fingerprint": fingerprint,
            "artifact": Path("incremental-preview") / f"{safe}.mp4",
            "artifact_sha256": file_sha256(artifact),
            "frames": frames,
            "status": "rendered" if shot_id in rendered_shots else "cache_hit",
        })
    manifest = {
        "version": "0.1",
        "source_fingerprint": source_fingerprint(project),
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "shots": entries,
        "rendered_shots": rendered_shots,
        "cache_hits": cache_hits,
        "note": "Per-shot cache; run the normal preview command for a full stitched MP4.",
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    return manifest


LAST_LOUDNESS = {}


def run_preview(project, renderer, output=None, install=False, shot=None, loudness=True):
    """Build a full or shot preview MP4 and visual review frame manifest."""
    project = Path(project).resolve()
    renderer = Path(renderer).resolve()
    if not (project / "production_brief.json").is_file():
        raise FileNotFoundError(f"Not a production project: {project}")
    if renderer == project or renderer.is_relative_to(project):
        raise ValueError("Renderer must be outside the production project")
    renderer.mkdir(parents=True, exist_ok=True)
    points = review_points(project, shot)
    if points:
        (renderer / "out" / "visual-review").mkdir(parents=True, exist_ok=True)
    _run_commands(steps(project, renderer, install, shot, points))

    rendered = renderer / "out" / "video.mp4"
    if not rendered.is_file():
        raise FileNotFoundError(f"Remotion did not produce {rendered}")
    destination = (Path(output).resolve() if output else project / (f"preview_{_safe_name(shot)}.mp4" if shot else "preview.mp4"))
    destination.parent.mkdir(parents=True, exist_ok=True)
    if loudness:
        from loudness import normalize
        LAST_LOUDNESS.clear()
        LAST_LOUDNESS.update(normalize(rendered, destination))
    else:
        shutil.copy2(rendered, destination)
    if points:
        review_root = project / "visual-review"
        review_root.mkdir(parents=True, exist_ok=True)
        frames = []
        for point in points:
            source = renderer / "out" / "visual-review" / point["filename"]
            if not source.is_file():
                raise FileNotFoundError(f"Remotion did not produce {source}")
            relative = Path("visual-review") / point["filename"]
            shutil.copy2(source, project / relative)
            frames.append({
                "shot_id": point["shot_id"],
                "position": point["position"],
                "frame": point["frame"],
                "global_frame": point["global_frame"],
                "image": relative.as_posix(),
                "sha256": file_sha256(project / relative),
                "reviewed": False,
            })
        try:
            preview_reference = destination.relative_to(project).as_posix()
        except ValueError:
            preview_reference = str(destination)
        open_revisions, _ = open_revision_entries(project)
        (project / "visual_review.json").write_text(json.dumps({
            "version": "0.2",
            "preview": preview_reference,
            "preview_sha256": file_sha256(destination),
            "source_fingerprint": source_fingerprint(project),
            "supersedes_revisions": [item["id"] for item in open_revisions],
            "scope": {"shot": shot, "full_project": shot is None},
            "frames": frames,
            "review_status": "pending",
            "review_notes": "Inspect identity, seams, contact, occlusion, captions and timing before marking reviewed.",
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destination


def run_simple_comic_preview(project, output=None, motion_config=None):
    """Render the simple-comic finishing pass with local face acting.

    This path is intentionally separate from the Remotion contract: it uses
    approved full-frame masters plus aligned eye/mouth variants and never
    invents a camera move.  It is useful for a quick image-first preview.
    """
    project = Path(project).resolve()
    if not (project / "production_brief.json").is_file():
        raise FileNotFoundError(f"Not a production project: {project}")
    destination = (Path(output).resolve() if output else project / "preview-simple-comic-10s.mp4")
    command = [sys.executable, str(ROOT / "scripts" / "render_simple_comic_preview.py"), str(project), "--output", str(destination)]
    if motion_config:
        command.extend(["--motion-config", str(Path(motion_config).resolve())])
    print("RUN:", " ".join(str(part) for part in command))
    subprocess.run(command, check=True)
    if not destination.is_file():
        raise FileNotFoundError(f"Simple-comic renderer did not produce {destination}")
    return destination


def main():
    parser = argparse.ArgumentParser(description="Build a local Dynamic Comic MP4 preview")
    parser.add_argument("project", type=Path, help="Independent production project directory")
    parser.add_argument("--renderer", type=Path, help="External Remotion renderer directory")
    parser.add_argument("--output", type=Path, help="Destination MP4; defaults to <project>/preview.mp4")
    parser.add_argument("--npm-install", action="store_true", help="Run npm ci before rendering")
    parser.add_argument("--shot", help="Render one shot and rebase its timeline to frame zero")
    parser.add_argument("--incremental", action="store_true", help="Render only changed shots into incremental-preview/")
    parser.add_argument("--simple-comic", action="store_true", help="Use the image-first simple-comic renderer with local eye/mouth variants")
    parser.add_argument("--motion-config", type=Path, help="Face-motion manifest for --simple-comic")
    parser.add_argument("--keep-loudness", action="store_true", help="Copy the render without normalising audio to -14 LUFS")
    args = parser.parse_args()
    if args.simple_comic:
        result = run_simple_comic_preview(args.project, args.output, args.motion_config)
        print(json.dumps({"status": "PASS", "preview": str(result), "renderer": "simple-comic"}, ensure_ascii=False))
        return 0
    if not args.renderer:
        parser.error("--renderer is required unless --simple-comic is used")
    if args.incremental:
        result = run_incremental_preview(args.project, args.renderer, args.npm_install)
        print(json.dumps({"status": "PASS", "incremental": result}, ensure_ascii=False, default=str))
        return 0
    destination = run_preview(args.project, args.renderer, args.output, args.npm_install, args.shot, not args.keep_loudness)
    visual_review = args.project.resolve() / "visual_review.json"
    if not visual_review.is_file():
        visual_review = None
    print(json.dumps({"status": "PASS", "preview": str(destination), "visual_review": str(visual_review) if visual_review else None, "loudness": LAST_LOUDNESS or None}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
