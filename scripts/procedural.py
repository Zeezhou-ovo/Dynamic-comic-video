"""Bridge the Dynamic Comic planning workflow to a procedural frame renderer.

This route uses an external p5.js animation project with production/plan.json.
It does not reinterpret the existing layered-Remotion contracts.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path


def node_executable():
    found = shutil.which("node")
    if found:
        return found
    bundled = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node"
    if bundled.is_file():
        return str(bundled)
    raise SystemExit("Node.js not found. Install Node.js or run this from a Codex desktop environment.")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def fingerprint(project, plan):
    digest = hashlib.sha256()
    for name in ["production/plan.json", *plan.get("source_files", [])]:
        file = (project / name).resolve()
        if not file.is_relative_to(project) or not file.is_file():
            raise SystemExit(f"Missing or invalid source file: {name}")
        digest.update(file.read_bytes())
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description="Run the procedural frame route for a p5 animation project")
    parser.add_argument("command", choices=("inspect", "check", "sheets", "approve", "render"))
    parser.add_argument("project", type=Path, help="External p5 animation project directory")
    parser.add_argument("--shot", help="Shot ID for approve or a local shot render")
    parser.add_argument("--note", help="Actual visual observation for approve")
    parser.add_argument("--out", help="Render output path within the project")
    parser.add_argument("--range", help="Optional local time span, e.g. 0:4")
    args = parser.parse_args()
    project = args.project.expanduser().resolve()
    plan_path = project / "production/plan.json"
    planner = project / "scripts/production.mjs"
    renderer = project / "scripts/render-local.sh"
    if not plan_path.is_file() or not planner.is_file() or not renderer.is_file():
        raise SystemExit("This project needs production/plan.json, scripts/production.mjs and scripts/render-local.sh")
    plan = read_json(plan_path)

    if args.command == "inspect":
        review_path = project / "out/review/visual_review.json"
        review = read_json(review_path) if review_path.is_file() else None
        current = fingerprint(project, plan)
        output = project / (args.out or "out/video.mp4")
        print(json.dumps({
            "project_id": plan.get("project_id"),
            "mode": "procedural-frame",
            "format": plan.get("format"),
            "shots": [s.get("id") for s in plan.get("shots", [])],
            "review": {
                "exists": review is not None,
                "current": bool(review and review.get("source_sha256") == current),
                "approved_shots": [s["shot_id"] for s in review.get("shots", []) if s.get("reviewed")] if review else [],
            },
            "video_exists": output.is_file(),
        }, ensure_ascii=False, indent=2))
        return

    node = node_executable()
    command = [node, str(planner), args.command]
    if args.command == "approve":
        if not args.shot or not args.note:
            parser.error("approve requires --shot and --note after inspecting the review image")
        command += [f"--shot={args.shot}", f"--note={args.note}"]
    elif args.command == "render":
        if args.shot and args.range:
            parser.error("use either --shot or --range for a local render")
        output = args.out or (f"out/preview_{args.shot}.mp4" if args.shot else "out/video.mp4")
        command = [str(renderer), "--clip", f"--out={output}"]
        span = args.range
        if args.shot:
            shot = next((s for s in plan.get("shots", []) if s.get("id") == args.shot), None)
            if shot is None:
                parser.error(f"unknown shot {args.shot}")
            fps = plan["format"]["fps"]
            start = shot["start_frame"] / fps
            end = (shot["start_frame"] + shot["duration_frames"]) / fps
            span = f"{start:g}:{end:g}"
        if span:
            command.append(f"--range={span}")
    subprocess.run(command, cwd=project, check=True, env={**os.environ, "NODE_BIN": node})


if __name__ == "__main__":
    main()
