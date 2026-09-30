"""Contract checks for the additive motion_plan 0.4 camera fields."""
import tempfile
import unittest
from pathlib import Path

from make_camera_parallax_fixture import build
from pipeline import local, read, save, validate
from production import render_payload


class CameraPlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = build(Path(self.temp.name) / "camera-project")

    def tearDown(self):
        self.temp.cleanup()

    def motion(self):
        return read(self.project / "motion_plan.json")

    def update_motion(self, motion):
        save(self.project / "motion_plan.json", motion)

    def test_camera_fixture_contract_and_assets_pass(self):
        _data, errors, _warnings = validate(self.project, assets=True)
        self.assertEqual(errors, [])

    def test_render_payload_carries_camera_and_explicit_depth(self):
        data, errors, _warnings = validate(self.project)
        self.assertEqual(errors, [])
        payload = render_payload(self.project, data, local)
        self.assertEqual(payload["version"], "0.4")
        self.assertEqual(payload["shots"][1]["camera"]["type"], "push_in")
        self.assertEqual({layer["depth"] for layer in payload["shots"][1]["layers"]}, {
            "foreground", "character", "midground", "background", "sky",
        })

    def test_moving_camera_with_multiple_depths_requires_parallax(self):
        motion = self.motion()
        motion["shots"][1]["camera"]["parallax_enabled"] = False
        self.update_motion(motion)
        errors = validate(self.project)[1]
        self.assertTrue(any("requires parallax" in error for error in errors))

    def test_follow_path_must_cover_local_shot_frames(self):
        motion = self.motion()
        shot = motion["shots"][2]
        shot["camera"]["type"] = "follow"
        shot["camera"]["follow_path"] = [
            {"frame": 1, "x": 430, "y": 335},
            {"frame": 47, "x": 590, "y": 335},
        ]
        self.update_motion(motion)
        errors = validate(self.project)[1]
        self.assertTrue(any("cover local frames 0..duration-1" in error for error in errors))

    def test_v04_rejects_per_layer_camera_motion(self):
        motion = self.motion()
        motion["shots"][1]["layers"][0]["to"]["scale"] = 1.1
        self.update_motion(motion)
        errors = validate(self.project)[1]
        self.assertTrue(any("camera owns scene framing" in error for error in errors))

    def test_pan_direction_must_match_camera_positions(self):
        motion = self.motion()
        shot = motion["shots"][2]
        shot["camera"]["from"], shot["camera"]["to"] = shot["camera"]["to"], shot["camera"]["from"]
        self.update_motion(motion)
        errors = validate(self.project)[1]
        self.assertTrue(any("pan_right must move camera x right" in error for error in errors))

    def test_old_contract_rejects_new_camera_fields(self):
        motion = self.motion()
        motion["version"] = "0.3"
        self.update_motion(motion)
        errors = validate(self.project)[1]
        self.assertTrue(any("require motion_plan 0.4" in error for error in errors))

    def test_static_camera_rejects_different_end_pose(self):
        motion = self.motion()
        motion["shots"][0]["camera"].update({
            "from": {"x": 480, "y": 270, "zoom": 1},
            "to": {"x": 481, "y": 270, "zoom": 1},
        })
        self.update_motion(motion)
        errors = validate(self.project)[1]
        self.assertTrue(any("static camera from/to poses must match" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
