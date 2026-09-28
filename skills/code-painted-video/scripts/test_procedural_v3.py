"""Behavior checks for the rendering gate used by new procedural projects."""
import copy
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from procedural import validate

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "assets" / "painted-frame-starter" / "plan.example.json"


class ProceduralPlanV3Tests(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads(SAMPLE.read_text())

    def run_plan(self, expected_failure=False):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "plan.json"
            path.write_text(json.dumps(self.plan))
            with redirect_stdout(StringIO()):
                if expected_failure:
                    with self.assertRaises(SystemExit):
                        validate(path)
                else:
                    validate(path)

    def test_example_plan_passes(self):
        self.run_plan()

    def test_missing_primary_action_blocks_render(self):
        del self.plan["shots"][0]["animation_plan"]["primary_action"]
        self.run_plan(expected_failure=True)

    def test_moving_camera_requires_parallax_with_depth(self):
        card = self.plan["shots"][0]["animation_plan"]
        card["camera_motion"] = "pan"
        card["camera_purpose"] = "Follow the light across the ground"
        card["parallax_enabled"] = False
        self.run_plan(expected_failure=True)

    def test_static_majority_needs_narrative_reason(self):
        self.plan["shots"] = [copy.deepcopy(self.plan["shots"][0]) for _ in range(3)]
        for i, shot in enumerate(self.plan["shots"]):
            shot["start"], shot["end"] = i * 2, (i + 1) * 2
        self.plan["duration"] = 6
        del self.plan["shots"][1]["animation_plan"]["static_necessity"]
        self.run_plan(expected_failure=True)

    def test_important_moment_requires_emphasis(self):
        self.plan["shots"][0]["animation_plan"]["important_moment"] = True
        self.run_plan(expected_failure=True)


if __name__ == "__main__":
    unittest.main()
