"""Tests for the one-command preview orchestration."""
import unittest
from pathlib import Path
from unittest.mock import patch

from preview import review_points, run_incremental_preview, run_preview, run_simple_comic_preview, steps


class PreviewTests(unittest.TestCase):
    def test_steps_put_quality_gate_before_prepare_and_render(self):
        commands = steps(Path("C:/project"), Path("C:/renderer"))
        self.assertIn("validate", commands[0][0])
        self.assertIn("--autofix", commands[1][0])
        self.assertIn("validate", commands[2][0])
        self.assertIn("compile", commands[3][0])
        self.assertIn("prepare", commands[4][0])
        self.assertEqual(commands[-1][0][-2:], ["run", "render"])

    def test_steps_can_include_npm_install(self):
        commands = steps(Path("C:/project"), Path("C:/renderer"), install=True)
        self.assertEqual(commands[-2][0][-1], "ci")
        self.assertEqual(commands[-1][0][-2:], ["run", "render"])

    def test_steps_support_shot_preview_and_review_stills(self):
        points = [{"filename": "shot_001_first.png", "global_frame": 0}]
        commands = steps(Path("C:/project"), Path("C:/renderer"), shot="shot_001", stills=points)
        compile_command = next(command for command, _ in commands if "compile" in command)
        prepare_command = next(command for command, _ in commands if "prepare" in command)
        still_command = next(command for command, _ in commands if "still-frame" in command)
        self.assertEqual(compile_command[-2:], ["--shot", "shot_001"])
        self.assertEqual(prepare_command[-2:], ["--shot", "shot_001"])
        self.assertIn("out/visual-review/shot_001_first.png", still_command)
        self.assertIn("--frame=0", still_command)

    def test_steps_can_skip_preflight_for_cached_shot_render(self):
        commands = steps(Path("C:/project"), Path("C:/renderer"), shot="shot_001", preflight=False)
        self.assertNotIn("validate", [part for command, _ in commands for part in command])
        self.assertTrue(any("compile" in command for command, _ in commands))

    def test_review_points_use_local_frames_for_shot_preview(self):
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            (project / "motion_plan.json").write_text(json.dumps({"shots": [{
                "shot_id": "shot/001", "start_frame": 24, "duration_frames": 10,
            }]}), encoding="utf-8")
            full = review_points(project)
            local = review_points(project, "shot/001")
        self.assertEqual([item["global_frame"] for item in full], [24, 28, 33])
        self.assertEqual([item["global_frame"] for item in local], [0, 4, 9])
        self.assertEqual({item["filename"] for item in full}, {"shot_001_first.png", "shot_001_middle.png", "shot_001_last.png"})

    def test_run_preview_copies_rendered_file(self):
        import tempfile

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = root / "project"
            renderer = root / "renderer"
            project.mkdir()
            renderer.mkdir()
            (project / "production_brief.json").write_text("{}", encoding="utf-8")
            rendered = renderer / "out"
            rendered.mkdir()
            (rendered / "video.mp4").write_bytes(b"preview")
            with patch("preview.subprocess.run") as run:
                destination = run_preview(project, renderer, loudness=False)
            self.assertEqual(destination, (project / "preview.mp4").resolve())
            self.assertEqual(destination.read_bytes(), b"preview")
            self.assertEqual(run.call_count, len(steps(project, renderer)))

    def test_run_preview_normalises_loudness_by_default(self):
        import tempfile

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project, renderer = root / "project", root / "renderer"
            project.mkdir()
            (renderer / "out").mkdir(parents=True)
            (project / "production_brief.json").write_text("{}", encoding="utf-8")
            (renderer / "out" / "video.mp4").write_bytes(b"preview")

            def fake_normalize(source, destination):
                Path(destination).write_bytes(Path(source).read_bytes())
                return {"applied": True, "gain_db": 3.0}

            with patch("preview.subprocess.run"), patch("loudness.normalize", side_effect=fake_normalize) as normalize:
                destination = run_preview(project, renderer)
            normalize.assert_called_once()
            self.assertEqual(destination.read_bytes(), b"preview")

    def test_shot_preview_copies_visual_review_artifacts(self):
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = root / "project"
            renderer = root / "renderer"
            project.mkdir()
            renderer.mkdir()
            (project / "production_brief.json").write_text("{}", encoding="utf-8")
            (project / "motion_plan.json").write_text(json.dumps({"shots": [{
                "shot_id": "shot/001", "start_frame": 12, "duration_frames": 6,
            }]}), encoding="utf-8")
            rendered = renderer / "out"
            review = rendered / "visual-review"
            review.mkdir(parents=True)
            (rendered / "video.mp4").write_bytes(b"preview")
            for position in ("first", "middle", "last"):
                (review / f"shot_001_{position}.png").write_bytes(position.encode())
            with patch("preview.subprocess.run") as run:
                destination = run_preview(project, renderer, shot="shot/001", loudness=False)
            self.assertEqual(destination, (project / "preview_shot_001.mp4").resolve())
            manifest = json.loads((project / "visual_review.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["version"], "0.2")
            self.assertEqual(manifest["scope"]["shot"], "shot/001")
            self.assertEqual(len(manifest["frames"]), 3)
            self.assertTrue(manifest["source_fingerprint"])
            self.assertTrue(manifest["preview_sha256"])
            self.assertTrue(all(frame["sha256"] for frame in manifest["frames"]))
            self.assertTrue(all(not frame["reviewed"] for frame in manifest["frames"]))
            self.assertEqual(run.call_count, len(steps(project, renderer, shot="shot/001", stills=review_points(project, "shot/001"))))

    def test_incremental_preview_renders_then_reuses_unchanged_shot(self):
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = root / "project"
            renderer = root / "renderer"
            project.mkdir()
            renderer.mkdir()
            (project / "production_brief.json").write_text("{}", encoding="utf-8")
            (project / "motion_plan.json").write_text(json.dumps({"shots": [{
                "shot_id": "shot_001", "start_frame": 0, "duration_frames": 6,
            }]}), encoding="utf-8")
            (project / "asset_report.json").write_text(json.dumps({"shots": [{
                "shot_id": "shot_001", "fingerprint": "fp1",
            }]}), encoding="utf-8")
            rendered = renderer / "out"
            review = rendered / "visual-review"
            review.mkdir(parents=True)
            (rendered / "video.mp4").write_bytes(b"preview")
            for position in ("first", "middle", "last"):
                (review / f"shot_001_{position}.png").write_bytes(position.encode())
            with patch("preview.subprocess.run") as run:
                first = run_incremental_preview(project, renderer)
                first_calls = run.call_count
                second = run_incremental_preview(project, renderer)
            self.assertEqual(first["rendered_shots"], ["shot_001"])
            self.assertEqual(second["rendered_shots"], [])
            self.assertEqual(second["cache_hits"], ["shot_001"])
            self.assertGreater(first_calls, run.call_count - first_calls)
            self.assertTrue((project / "incremental_preview.json").is_file())

    def test_simple_comic_preview_uses_local_renderer(self):
        import tempfile

        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"
            project.mkdir()
            (project / "production_brief.json").write_text("{}", encoding="utf-8")
            destination = project / "preview-simple-comic-10s.mp4"

            def fake_run(command, check):
                destination.write_bytes(b"simple-comic")

            with patch("preview.subprocess.run", side_effect=fake_run) as run:
                result = run_simple_comic_preview(project)

            self.assertEqual(result, destination.resolve())
            self.assertTrue(destination.is_file())
            self.assertIn("render_simple_comic_preview.py", str(run.call_args.args[0]))


if __name__ == "__main__":
    unittest.main()
