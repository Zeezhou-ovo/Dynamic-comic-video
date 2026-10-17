"""End-to-end validation for the cutout-comedy fixture."""
import tempfile
import unittest
from pathlib import Path

from make_cutout_comedy_fixture import build
from pipeline import read, validate


class CutoutComedyFixtureTests(unittest.TestCase):
    def test_fixture_validates_and_uses_static_first_mode(self):
        with tempfile.TemporaryDirectory() as temp:
            project = build(Path(temp) / "cutout")
            _, errors, _ = validate(project)
            self.assertEqual(errors, [])

            motion = read(project / "motion_plan.json")
            self.assertTrue(all(
                shot["performance"]["mode"] == "cutout-comedy"
                for shot in motion["shots"]
            ))

            presets = {
                event["preset"]
                for shot in motion["shots"]
                for performer in shot.get("character_performance", [])
                for event in performer.get("events", [])
            }
            self.assertTrue({
                "head_forward", "lean_back", "body_shake", "double_take"
            } <= presets)


if __name__ == "__main__":
    unittest.main()
