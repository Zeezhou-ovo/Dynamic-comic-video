"""Tests for extract_layer.py on a synthetic master with a known answer."""
import json
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from extract_layer import approve, extract, main, normalise_hints, stale_outputs
from performance import check_extractions

W, H = 640, 360
WALL = (196, 214, 228)  # BGR, light beige
FLOOR_Y = 250
PILLAR_X = (470, 482)


def synthetic_master(path):
    """Wall with a dark pillar, a floor, and a prop: body + a wall-coloured patch + a thin rocker."""
    image = np.zeros((H, W, 3), np.uint8)
    for y in range(H):
        image[y] = WALL if y < FLOOR_Y else (170, 200, 222)
    image[:FLOOR_Y, PILLAR_X[0]:PILLAR_X[1]] = (120, 140, 160)
    truth = np.zeros((H, W), np.uint8)
    cv2.rectangle(image, (380, 120), (520, 230), (40, 90, 160), -1)        # body
    cv2.rectangle(image, (380, 120), (520, 230), (20, 20, 20), 2)
    cv2.rectangle(truth, (380, 120), (520, 230), 255, -1)
    cv2.rectangle(image, (420, 140), (480, 185), WALL, -1)                # shirt the colour of the wall
    cv2.rectangle(image, (420, 140), (480, 185), (20, 20, 20), 2)
    cv2.ellipse(image, (450, 228), (95, 30), 0, 10, 170, (30, 80, 140), 6)  # rocker arc
    cv2.ellipse(truth, (450, 228), (95, 30), 0, 10, 170, 255, 6)
    cv2.imwrite(str(path), image)
    return truth


class ExtractLayerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name)
        (self.project / "shots").mkdir()
        self.truth = synthetic_master(self.project / "shots/master.png") > 0
        self.hints = {"rect": "360,100,560,270", "fg_box": ["430,150,470,175"], "extend_down_until": FLOOR_Y, "max_angle": 4}

    def tearDown(self):
        self.temp.cleanup()

    def run_extract(self, hints=None):
        return extract(self.project, "shots/master.png", "prop", hints=hints or self.hints)

    def alpha(self):
        return cv2.imread(str(self.project / "layers/prop.png"), cv2.IMREAD_UNCHANGED)[:, :, 3] > 127

    def test_layer_matches_ground_truth_and_hint_recovers_wall_coloured_patch(self):
        manifest_path, manifest = self.run_extract()
        mask = self.alpha()
        iou = (mask & self.truth).sum() / (mask | self.truth).sum()
        self.assertGreater(iou, 0.93)
        self.assertTrue(mask[160, 450], "the patch matching the wall colour must stay in the layer")
        self.assertFalse(mask[50, 100], "the wall is not part of the layer")
        self.assertEqual(manifest["reviewed"], False)
        self.assertEqual(set(manifest["outputs"]), {"layer", "plate", "review"})
        self.assertTrue(manifest_path.name.endswith(".extract.json"))

    def test_plate_fills_the_hole_and_keeps_the_pillar_straight(self):
        self.run_extract()
        plate = cv2.imread(str(self.project / "layers/prop_plate.png")).astype(int)
        self.assertEqual(plate.shape, (H, W, 3))
        inside_wall = plate[200, 400]
        self.assertLess(np.abs(inside_wall - np.array(WALL)).max(), 20, "wall behind the prop is wall-coloured")
        pillar = plate[200, (PILLAR_X[0] + PILLAR_X[1]) // 2]
        self.assertLess(pillar.mean(), np.array(WALL).mean() - 40, "the pillar continues down behind the prop")

    def test_review_sheet_has_four_panels(self):
        _, manifest = self.run_extract()
        sheet = cv2.imread(str(self.project / manifest["outputs"]["review"]["path"]))
        x0, _, x1, _ = manifest["bbox"]
        self.assertGreater(sheet.shape[1], 3.5 * (x1 - x0))

    def test_approve_binds_to_files_and_edits_invalidate_it(self):
        manifest_path, manifest = self.run_extract()
        shot = {"shot_id": "s", "layers": [{"layer_id": "prop", "asset": manifest["outputs"]["layer"]["path"]}]}
        resolve = lambda root, name: Path(root) / name
        self.assertTrue(any("not approved" in e for e in check_extractions(shot, resolve, self.project)))
        approve(self.project, manifest_path.relative_to(self.project), "checked")
        self.assertEqual(check_extractions(shot, resolve, self.project), [])
        layer = self.project / "layers/prop.png"
        image = cv2.imread(str(layer), cv2.IMREAD_UNCHANGED)
        image[0, 0] = (1, 2, 3, 255)
        cv2.imwrite(str(layer), image)
        self.assertEqual(stale_outputs(self.project, json.loads(manifest_path.read_text())), ["layers/prop.png"])
        self.assertTrue(any("changed after" in e for e in check_extractions(shot, resolve, self.project)))
        with self.assertRaises(ValueError):
            approve(self.project, manifest_path, "again")

    def test_plate_asset_finds_its_manifest(self):
        _, manifest = self.run_extract()
        shot = {"shot_id": "s", "layers": [{"layer_id": "base", "asset": manifest["outputs"]["plate"]["path"]}]}
        errors = check_extractions(shot, lambda root, name: Path(root) / name, self.project)
        self.assertTrue(any("not approved" in e for e in errors))

    def test_hints_round_trip_through_a_previous_manifest(self):
        manifest_path, manifest = self.run_extract()
        again = normalise_hints(manifest["hints"])
        self.assertEqual(again["rect"], [360, 100, 560, 270])
        self.assertEqual(again["fg_box"], [[430, 150, 470, 175]])
        code = main(["extract", str(self.project), "--master", "shots/master.png", "--name", "prop2", "--hints", str(manifest_path)])
        self.assertEqual(code, 0)
        self.assertTrue((self.project / "layers/prop2.png").is_file())

    def test_bad_input_is_reported(self):
        self.assertEqual(main(["extract", str(self.project), "--master", "shots/missing.png", "--name", "x", "--rect", "0,0,10,10"]), 1)
        with self.assertRaises(ValueError):
            normalise_hints({})
        with self.assertRaises(ValueError):
            self.run_extract({"rect": "5,5,8,8"})


if __name__ == "__main__":
    unittest.main()
