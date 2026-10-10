"""Contract and render-payload checks for the optional V2 animation system."""
import tempfile
import unittest
from pathlib import Path

from make_character_performance_fixture import build
from pipeline import local, read, save, validate
from production import render_payload


class V2AnimationPlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = build(Path(self.temp.name) / "v2-project")
        characters = read(self.project / "characters.json")
        character = characters["characters"][0]
        capabilities = character.setdefault("capabilities", {"parts": [], "poses": [], "expressions": []})
        capabilities.setdefault("poses", [])
        for pose in ("idle", "dash"):
            if pose not in capabilities["poses"]:
                capabilities["poses"].append(pose)
        save(self.project / "characters.json", characters)

        first_shot = read(self.project / "storyboard.json")["shots"][0]
        visible_character = first_shot["characters"][0]["character_id"]
        animation = {
            "version": "0.1",
            "project_id": read(self.project / "production_brief.json")["project_id"],
            "shots": [{
                "shot_id": first_shot["id"],
                "characters": [{
                    "character_id": visible_character,
                    "pose_clips": [{
                        "clip_id": "dash",
                        "start_frame": 2,
                        "anticipation_end_frame": 4,
                        "action_end_frame": 8,
                        "hold_end_frame": 12,
                        "end_frame": 16,
                        "base_pose": "idle",
                        "action_pose": "dash",
                        "smear": True,
                        "translate": {"x": -80, "y": 0},
                        "squash_stretch": {"x": 0.15, "y": -0.1}
                    }]
                }],
                "effects": [{
                    "event_id": "burst",
                    "effect_type": "radial_burst",
                    "start_frame": 4,
                    "end_frame": 10,
                    "intensity": 0.8
                }]
            }]
        }
        save(self.project / "animation_system.json", animation)

    def tearDown(self):
        self.temp.cleanup()

    def test_optional_animation_contract_passes(self):
        _data, errors, _warnings = validate(self.project)
        self.assertEqual(errors, [])

    def test_render_payload_carries_animation_per_shot(self):
        data, errors, _warnings = validate(self.project)
        self.assertEqual(errors, [])
        payload = render_payload(self.project, data, local)
        animated = payload["shots"][0]["animation"]
        self.assertEqual(animated["characters"][0]["pose_clips"][0]["action_pose"], "dash")
        self.assertEqual(animated["effects"][0]["effect_type"], "radial_burst")

    def test_pose_clip_must_fit_inside_shot(self):
        animation = read(self.project / "animation_system.json")
        animation["shots"][0]["characters"][0]["pose_clips"][0]["end_frame"] = 9999
        save(self.project / "animation_system.json", animation)
        errors = validate(self.project)[1]
        self.assertTrue(any("Invalid pose clip frame order/range" in error for error in errors))

    def test_unknown_pose_is_rejected_when_capabilities_are_declared(self):
        animation = read(self.project / "animation_system.json")
        animation["shots"][0]["characters"][0]["pose_clips"][0]["action_pose"] = "teleport"
        save(self.project / "animation_system.json", animation)
        errors = validate(self.project)[1]
        self.assertTrue(any("Unknown pose capability" in error for error in errors))

    def test_effect_must_fit_inside_shot(self):
        animation = read(self.project / "animation_system.json")
        animation["shots"][0]["effects"][0]["end_frame"] = 9999
        save(self.project / "animation_system.json", animation)
        errors = validate(self.project)[1]
        self.assertTrue(any("Invalid animation effect range" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
