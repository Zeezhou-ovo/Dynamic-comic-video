"""Contract and validation checks for Character Performance Runtime."""
import json
import tempfile
import unittest
from pathlib import Path

from make_character_performance_fixture import build
from acting import check_character_performance
from pipeline import read, save, validate
from production import render_payload
from pipeline import local


class CharacterPlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = build(Path(self.temp.name) / "fixture")

    def tearDown(self):
        self.temp.cleanup()

    def _errors(self):
        _, errors, _ = validate(self.project, assets=True)
        return errors

    def test_complete_fixture_passes_contract_and_layer_asset_checks(self):
        self.assertEqual(self._errors(), [])
        plan = read(self.project / "motion_plan.json")
        moving = [shot for shot in plan["shots"] if shot.get("camera", {}).get("type") != "static"]
        self.assertGreaterEqual(len(moving), len(plan["shots"]) / 2)
        self.assertTrue(all(shot["camera"]["parallax_enabled"] for shot in moving))

    def test_declared_character_part_must_have_a_rendered_layer(self):
        path = self.project / "characters.json"
        data = read(path)
        data["characters"][1]["capabilities"]["parts"].remove("eyes")
        save(path, data)
        errors = self._errors()
        self.assertTrue(any("blink preset requires a rendered eyes part" in error for error in errors), errors)

    def test_requested_action_must_have_compatible_capability_and_asset(self):
        motion_path = self.project / "motion_plan.json"
        motion = read(motion_path)
        motion["shots"][1]["character_performance"][0]["events"][0]["part"] = "hair"
        save(motion_path, motion)
        errors = self._errors()
        self.assertTrue(any("point preset part must be an arm" in error for error in errors), errors)

    def test_camera_parallax_must_keep_background_covering_the_viewport(self):
        path = self.project / "motion_plan.json"
        motion = read(path)
        motion["shots"][1]["camera"] = {
            "type": "pan_right", "focus_target": {"x": 670, "y": 270},
            "from": {"x": 480, "y": 270, "zoom": 1},
            "to": {"x": 520, "y": 270, "zoom": 1},
            "screen_target": {"x": 0.5, "y": 0.5}, "easing": "easeInOut", "parallax_enabled": True,
        }
        save(path, motion)
        errors = self._errors()
        self.assertTrue(any("Camera/Parallax may reveal a background canvas edge" in error for error in errors), errors)

    def test_pose_mapping_must_exist_on_a_character_layer(self):
        motion_path = self.project / "motion_plan.json"
        motion = read(motion_path)
        performer = motion["shots"][1]["character_performance"][0]
        for layer in motion["shots"][1]["layers"]:
            layer.get("state_assets", {}).pop("pose:point", None)
        save(motion_path, motion)
        errors = self._errors()
        self.assertTrue(any("Requested pose has no mapped state asset" in error for error in errors), errors)

    def test_runtime_payload_attaches_manifest_and_character_ids(self):
        data = {name: read(self.project / f"{name}.json") for name in (
            "production_brief", "characters", "storyboard", "motion_plan",
        )}
        payload = render_payload(self.project, data, local)
        shot = payload["shots"][0]
        self.assertEqual(payload["character_capabilities"]["lin"]["parts"][0], "body")
        self.assertEqual(next(layer for layer in shot["layers"] if layer["layer_id"] == "lin_head")["character_id"], "lin")
        self.assertEqual(next(item for item in shot["character_performance"] if item["character_id"] == "lin")["capabilities"]["poses"], ["point"])
        self.assertEqual(shot["dialogue"][0]["speaker"], "lin")

    def test_character_performance_is_restricted_to_motion_plan_04(self):
        characters = read(self.project / "characters.json")["characters"]
        storyboard = read(self.project / "storyboard.json")["shots"][0]
        motion = read(self.project / "motion_plan.json")["shots"][0]
        errors = check_character_performance(motion, storyboard, characters, "0.3")
        self.assertTrue(any("requires motion_plan 0.4" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
