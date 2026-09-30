"""Composition and manifest regressions for the Phase 4 scene system."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator
from composition_resolver import resolve_composition, validate_scene_manifests
from pipeline import ROOT, read


def manifests():
    scene = {
        "version": "0.1", "project_id": "scene-test", "scene_id": "room",
        "coordinate_system": "normalized-0-to-1", "reference_size": {"width": 960, "height": 540},
        "layers": [
            {"id": "root", "parent_id": None, "kind": "group", "depth": "background", "z": 0, "visible": True},
            {"id": "bg", "parent_id": "root", "kind": "render_layer", "depth": "background", "asset": "scene/bg.png", "fit": "canvas", "z": 0, "visible": True},
            {"id": "mid", "parent_id": "root", "kind": "render_layer", "depth": "midground", "asset": "scene/mid.png", "fit": "canvas", "z": 5, "visible": True},
            {"id": "people", "parent_id": "root", "kind": "group", "depth": "character", "z": 10, "visible": True},
        ],
        "objects": [{"id": "book", "parent_id": "root", "asset": "scene/book.png", "depth": "foreground",
                      "anchor_id": "book", "position": [0.5, 0.76], "size": [0.2, 0.1], "pivot": [0.5, 0.5], "z": 30, "visible": True}],
        "character_slots": {
            "left": {"parent_id": "people", "position": [0.3, 0.82], "scale": 0.8, "facing": 1, "z": 12, "depth": "character"},
            "right": {"parent_id": "people", "position": [0.7, 0.82], "scale": 0.8, "facing": -1, "z": 13, "depth": "character"},
        },
        "character_instances": [{"character_id": "a", "slot_id": "left", "visible": True},
                                {"character_id": "b", "slot_id": "right", "visible": True}],
        "composition_anchors": {"center": [0.5, 0.5], "book": {"position": [0.5, 0.76], "bounds": {"left": 0.4, "top": 0.7, "right": 0.6, "bottom": 0.82}}},
        "camera_safe_bounds": {"left": 0.05, "top": 0.05, "right": 0.95, "bottom": 0.95},
        "background_coverage_bounds": {"left": 0, "top": 0, "right": 1, "bottom": 1},
    }
    characters = []
    for cid in ("a", "b"):
        characters.append({
            "character_id": cid, "reference_size": {"width": 260, "height": 360}, "root_anchor": [0.5, 0.95],
            "anchors": {
                "root": [0.5, 0.95],
                "body": {"position": [0.5, 0.75], "bounds": {"left": 0.15, "top": 0.45, "right": 0.85, "bottom": 0.99}},
                "face": {"position": [0.5, 0.38], "bounds": {"left": 0.25, "top": 0.2, "right": 0.75, "bottom": 0.55}},
                "head": {"position": [0.5, 0.4], "bounds": {"left": 0.18, "top": 0.15, "right": 0.82, "bottom": 0.62}},
            },
            "bounds": {"left": 0.1, "top": 0.1, "right": 0.9, "bottom": 1.0},
            "parts": {"body": {"asset": f"chars/{cid}/body.png", "pixel_size": {"width": 260, "height": 360},
                                 "anchor": [0.5, 0.95], "pivot": [0.5, 0.95], "depth": "character", "z": 0, "state_assets": {}}},
        })
    return scene, {"version": "0.1", "project_id": "scene-test", "coordinate_system": "normalized-0-to-1", "characters": characters}


class SceneCompositionTests(unittest.TestCase):
    def setUp(self):
        self.scene, self.assets = manifests()

    def resolve(self, intent, visible=("a", "b"), **kwargs):
        return resolve_composition(self.scene, self.assets, intent, visible,
                                   viewport={"width": 960, "height": 540}, **kwargs)

    def test_manifest_schemas_accept_normalized_scene_and_character_assets(self):
        for name, value in (("scene_manifest", self.scene), ("character_assets", self.assets)):
            schema = read(ROOT / "schemas" / f"{name}.schema.json")
            self.assertEqual(list(Draft202012Validator(schema).iter_errors(value)), [])

    def test_invalid_anchor_is_rejected_by_manifest_schema(self):
        invalid = json.loads(json.dumps(self.assets))
        invalid["characters"][0]["anchors"]["face"]["position"] = [1.2, 0.4]
        schema = read(ROOT / "schemas/character_assets.schema.json")
        self.assertTrue(list(Draft202012Validator(schema).iter_errors(invalid)))

    def test_character_face_world_anchor_is_used_in_closeup(self):
        result = self.resolve("speaker_closeup", ("b",), focus_character="b")
        slot = self.scene["character_slots"]["right"]
        expected_x = slot["position"][0] * 960
        expected_y = (slot["position"][1] + (0.38 - 0.95) * 360 * 0.8 / 540) * 540
        self.assertEqual(result["target_type"], "face_anchor")
        self.assertAlmostEqual(result["target"]["subject_x"], expected_x)
        self.assertAlmostEqual(result["target"]["subject_y"], expected_y)
        self.assertEqual(result["target"]["id"], "b")

    def test_two_shot_centers_the_actual_slot_bounds(self):
        result = self.resolve("two_shot")
        self.assertEqual(result["target_type"], "characters_bounds")
        self.assertAlmostEqual(result["target"]["subject_x"], 480)
        self.assertEqual(result["scene_instances"], [
            {"character_id": "a", "slot_id": "left", "visible": True},
            {"character_id": "b", "slot_id": "right", "visible": True},
        ])

    def test_two_shot_zoom_adapts_to_distance_and_slot_bindings(self):
        near = json.loads(json.dumps(self.scene))
        near["character_slots"]["right"]["position"][0] = 0.48
        near_result = resolve_composition(near, self.assets, "two_shot", ["a", "b"], viewport={"width": 960, "height": 540})
        far_result = self.resolve("two_shot")
        self.assertGreater(near_result["zoom"], far_result["zoom"])
        swapped = self.resolve("two_shot", ("a", "b"), character_bindings={"a": "right", "b": "left"})
        self.assertAlmostEqual(swapped["target"]["subject_x"], 480)

    def test_two_shot_scales_for_different_output_size(self):
        result = resolve_composition(self.scene, self.assets, "two_shot", ["a", "b"],
                                     viewport={"width": 1280, "height": 720})
        self.assertGreater(result["zoom"], 0)
        self.assertAlmostEqual(result["target"]["subject_x"], 480)

    def test_closeup_and_medium_use_face_and_body_bounds(self):
        closeup = self.resolve("speaker_closeup", ("a",), focus_character="a")
        medium = self.resolve("speaker_medium", ("a",), focus_character="a")
        self.assertEqual(closeup["target_type"], "face_anchor")
        self.assertEqual(medium["target_type"], "body_anchor")
        self.assertGreater(closeup["zoom"], 0)
        self.assertGreater(medium["zoom"], 0)

    def test_insert_targets_object_anchor_not_scene_center(self):
        result = self.resolve("insert", (), focus_object="book", visible_objects=["book"])
        self.assertEqual(result["target_type"], "object_anchor")
        self.assertEqual(result["target"]["id"], "book")
        self.assertAlmostEqual(result["target"]["subject_x"], 480)
        self.assertAlmostEqual(result["target"]["subject_y"], 410.4)

    def test_invalid_character_slot_binding_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown scene slot"):
            self.resolve("speaker_closeup", ("a",), focus_character="a", character_bindings={"a": "missing"})

    def test_safe_bounds_keep_extreme_character_focus_covered(self):
        scene = json.loads(json.dumps(self.scene))
        scene["character_slots"]["right"]["position"][0] = 0.96
        result = resolve_composition(scene, self.assets, "speaker_closeup", ["b"], focus_character="b",
                                     viewport={"width": 960, "height": 540}, parallax_enabled=True)
        self.assertTrue(result["safe_clamped"])
        self.assertGreaterEqual(result["target"]["x"], scene["camera_safe_bounds"]["left"] * 960)
        self.assertLessEqual(result["target"]["x"], scene["camera_safe_bounds"]["right"] * 960)

    def test_resolver_never_guesses_a_character_array_order(self):
        first = self.resolve("speaker_closeup", ("b", "a"), focus_character="a")
        second = self.resolve("speaker_closeup", ("a", "b"), focus_character="a")
        self.assertEqual(first["target"], second["target"])

    def test_scene_asset_validation_reports_missing_manifest_asset(self):
        with tempfile.TemporaryDirectory() as folder:
            errors = validate_scene_manifests(self.scene, self.assets,
                [{"id": "a", "capabilities": {"parts": ["body"], "poses": [], "expressions": []}},
                 {"id": "b", "capabilities": {"parts": ["body"], "poses": [], "expressions": []}}],
                Path(folder), lambda root, name: root / name,
                {"width": 960, "height": 540})
        self.assertTrue(any("Missing Scene Asset scene/bg.png" in item for item in errors))


if __name__ == "__main__":
    unittest.main()
