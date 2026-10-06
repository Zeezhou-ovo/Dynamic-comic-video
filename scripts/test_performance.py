"""Contract, validation and prepare checks for comic performance fields."""
import json
import shutil
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path

from make_dialogue_fixture import build_dialogue
from pipeline import read, save, validate
from performance import check_props, wav_shapes
from production import render_payload
import make_sfx

SCRIPTS = Path(__file__).resolve().parent


def local(root, name):
    return root / name


class PerformanceContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = build_dialogue(Path(self.temp.name) / "project")
        make_sfx.main([str(self.project)])

    def tearDown(self):
        self.temp.cleanup()

    def motion(self, edit):
        motion = read(self.project / "motion_plan.json")
        edit(motion)
        save(self.project / "motion_plan.json", motion)
        return validate(self.project, assets=True)[1]

    def test_ported_fields_validate(self):
        def edit(motion):
            shot = motion["shots"][0]
            mouth = next(layer for layer in shot["layers"] if layer.get("acting", {}).get("speech"))
            mouth["acting"]["speech"]["shape_assets"] = {"small": mouth["acting"]["speech"]["open_asset"]}
            t = shot.setdefault("timeline", {
                "scene_id": "test-room", "duration_frames": shot["duration_frames"], "subtitle_events": [], "speech_intervals": [],
                "action_events": [], "expression_events": [], "blink_events": [], "sound_events": [], "cut_at_frame": shot["duration_frames"]})
            t["sound_events"] = [{"event_id": "creak", "trigger": "action", "start_frame": 2, "peak_frame": 2, "settle_frame": 4,
                                  "end_frame": 9, "description": "creak", "asset": "audio/sfx/creak.wav", "volume": 0.5}]
            t["mouth_events"] = [{"speaker": "lin", "shape": "small", "start_frame": 6, "end_frame": 9, "source": "authored"}]
            t["visual_events"] = [{"event_id": "drop", "priority": "emotion", "effect_type": "sweat_drop", "start_frame": 4,
                                   "end_frame": 20, "description": "drop", "position": [0.4, 0.2], "size": 0.06, "intensity": 0.8}]
            motion["audio_bed"] = {"asset": "audio/sfx/room_tone.wav", "volume": 0.15}
        self.assertEqual(self.motion(edit), [])

    def test_prop_motion_with_attached_mouth_validates_and_prepares(self):
        def edit(motion):
            shot = motion["shots"][0]
            body = next(layer for layer in shot["layers"] if layer["layer_id"] == "body")
            body["prop_motion"] = {"pivot": [0.5, 0.9], "roll_radius": 120, "events": [
                {"event_id": "rock", "trigger": "information", "kind": "rock", "start_frame": 0, "end_frame": 40,
                 "amplitude_deg": 3, "period_frames": 20, "decay_frames": 20, "description": "reveal rock"}]}
            mouth = next(layer for layer in shot["layers"] if layer.get("acting", {}).get("speech"))
            mouth["attach_to"] = "body"
            motion["audio_bed"] = {"asset": "audio/sfx/room_tone.wav", "volume": 0.15}
        self.assertEqual(self.motion(edit), [])
        renderer = Path(self.temp.name) / "renderer"
        result = subprocess.run(["python3", str(SCRIPTS / "pipeline.py"), "prepare", str(self.project), "--renderer", str(renderer)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((renderer / "public/audio/sfx/room_tone.wav").is_file())
        data = json.loads((renderer / "src/render-data.json").read_text(encoding="utf-8"))
        self.assertEqual(data["audio_bed"]["asset"], "audio/sfx/room_tone.wav")
        cue = data["shots"][0]["dialogue"][0]
        self.assertEqual(len(cue["mouth_shape_frames"]), cue["end_frame"] - cue["start_frame"])

    def test_rock_without_decay_is_rejected(self):
        def edit(motion):
            body = next(layer for layer in motion["shots"][0]["layers"] if layer["layer_id"] == "body")
            body["prop_motion"] = {"pivot": [0.5, 0.9], "events": [
                {"event_id": "loop", "trigger": "action", "kind": "rock", "start_frame": 0, "end_frame": 40, "amplitude_deg": 3, "description": "loop"}]}
        self.assertTrue(any("settles instead of looping" in error for error in self.motion(edit)))

    def test_prop_rules(self):
        shot = {"shot_id": "s", "duration_frames": 30, "layers": [
            {"layer_id": "bg", "asset": "bg.png", "z": 0, "prop_motion": {"pivot": [0.5, 0.5], "events": []}},
            {"layer_id": "patch", "asset": "a.png", "z": 5, "region": [0, 0, 0.1, 0.1], "attach_to": "nothing"},
        ]}
        errors = check_props(shot, {"bg": "background", "patch": "character"})
        self.assertTrue(any("not a background" in error for error in errors))
        self.assertTrue(any("full-frame plate" in error for error in errors))
        self.assertTrue(any("attach_to must name" in error for error in errors))

    def test_invalid_audio_bed_is_reported(self):
        (self.project / "audio/sfx/bad.wav").write_bytes(b"not a wav")
        errors = self.motion(lambda motion: motion.__setitem__("audio_bed", {"asset": "audio/sfx/bad.wav"}))
        self.assertTrue(any("Invalid audio_bed" in error for error in errors))

    def test_kebab_case_easing_is_normalised_for_the_renderer(self):
        def edit(motion):
            arm = next(layer for layer in motion["shots"][0]["layers"] if layer["layer_id"] == "arm")
            arm["acting"]["easing"] = "ease-in-out"
        self.assertEqual(self.motion(edit), [])
        data, _, _ = validate(self.project, assets=True)
        payload = render_payload(self.project, data, local)
        arm = next(layer for layer in payload["shots"][0]["layers"] if layer["layer_id"] == "arm")
        self.assertEqual(arm["acting"]["easing"], "easeInOut")


class SfxAndLoudnessTests(unittest.TestCase):
    def test_generated_sfx_are_pcm_and_mouth_shapes_have_levels(self):
        with tempfile.TemporaryDirectory() as folder:
            make_sfx.main([folder])
            for name in ("creak.wav", "room_tone.wav", "pop.wav"):
                with wave.open(str(Path(folder) / "audio/sfx" / name)) as stream:
                    self.assertEqual(stream.getsampwidth(), 2)
                    self.assertGreater(stream.getnframes(), 1000)
            shapes = wav_shapes(Path(folder) / "audio/sfx/creak.wav", 24)
            self.assertEqual(len(shapes), 8)  # 0.32 s at 24 fps
            self.assertLessEqual(set(shapes), {"closed", "small", "open", "wide"})
            self.assertGreater(len(set(shapes)), 1)

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg not installed")
    def test_loudness_normalisation_reaches_target(self):
        from loudness import measure, normalize
        with tempfile.TemporaryDirectory() as folder:
            source, target = Path(folder) / "in.mp4", Path(folder) / "out.mp4"
            subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=gray:s=320x180:d=3:r=24",
                            "-f", "lavfi", "-i", "sine=frequency=440:duration=3", "-af", "volume=-30dB",
                            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(source)], check=True)
            report = normalize(source, target)
            self.assertTrue(report["applied"])
            self.assertAlmostEqual(measure(target), -14.0, delta=1.0)

    def test_missing_audio_copies_unchanged(self):
        from loudness import normalize
        with tempfile.TemporaryDirectory() as folder:
            source, target = Path(folder) / "in.mp4", Path(folder) / "out.mp4"
            source.write_bytes(b"not really a video")
            report = normalize(source, target)
            self.assertFalse(report["applied"])
            self.assertEqual(target.read_bytes(), source.read_bytes())


if __name__ == "__main__":
    unittest.main()
