"""Regression tests for the pre-preview timeline quality gate."""
import tempfile
import unittest
from pathlib import Path

from make_dialogue_fixture import build_dialogue
from pipeline import read, save
from quality_gate import scan


class QualityGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = build_dialogue(Path(self.temp.name) / "project")
        motion = read(self.project / "motion_plan.json")
        board = read(self.project / "storyboard.json")
        for shot, board_shot in zip(motion["shots"], board["shots"]):
            cue = board_shot["dialogue"][0]
            shot["timeline"] = {
                "scene_id": "test-room",
                "duration_frames": shot["duration_frames"],
                "audio": cue["audio"],
                "audio_start_frame": cue["start_frame"],
                "subtitle_events": [{"start_frame": cue["start_frame"], "end_frame": cue["end_frame"], "text": cue["text"]}],
                "speech_intervals": [{"start_frame": cue["start_frame"], "end_frame": cue["end_frame"], "speaker": cue["speaker"]}],
                "action_events": [{"event_id": "gesture", "trigger": "speech", "start_frame": 6, "peak_frame": 12, "settle_frame": 16, "end_frame": 20, "description": "one event-driven gesture"}],
                "expression_events": [],
                "blink_events": [{"frame": 24, "description": "one blink"}],
                "sound_events": [],
                "cut_at_frame": shot["duration_frames"],
            }
        # a well-formed piece ends on a reaction after the last line
        motion["shots"][-1]["timeline"]["expression_events"] = [{"event_id": "button", "trigger": "pause", "start_frame": 43, "peak_frame": 44, "settle_frame": 46, "end_frame": 47, "description": "closing reaction"}]
        save(self.project / "motion_plan.json", motion)

    def tearDown(self):
        self.temp.cleanup()

    def test_valid_event_phases_pass(self):
        self.assertEqual(scan(self.project)["summary"], {"Critical": 0, "Major": 0, "Minor": 0})

    def test_event_phase_order_is_reported(self):
        motion = read(self.project / "motion_plan.json")
        motion["shots"][0]["timeline"]["action_events"][0]["peak_frame"] = 5
        save(self.project / "motion_plan.json", motion)
        report = scan(self.project)
        self.assertTrue(any("event phases out of order" in item["message"] for item in report["issues"]))

    def test_blink_bounds_are_reported(self):
        motion = read(self.project / "motion_plan.json")
        motion["shots"][0]["timeline"]["blink_events"][0]["frame"] = 999
        save(self.project / "motion_plan.json", motion)
        report = scan(self.project)
        self.assertTrue(any("blink_events" in item["message"] for item in report["issues"]))

    def test_negative_cut_is_not_autofixed(self):
        motion = read(self.project / "motion_plan.json")
        motion["shots"][0]["timeline"]["cut_at_frame"] = -1
        save(self.project / "motion_plan.json", motion)
        report = scan(self.project, autofix=True)
        self.assertTrue(any(item["category"] == "cut" and "before" in item["message"] for item in report["issues"]))

    def test_visible_speaker_requires_mouth_layer(self):
        motion = read(self.project / "motion_plan.json")
        motion["shots"][0]["layers"] = [
            layer for layer in motion["shots"][0]["layers"]
            if not layer.get("acting", {}).get("speech")
        ]
        save(self.project / "motion_plan.json", motion)
        report = scan(self.project)
        self.assertTrue(any(item["category"] == "mouth_sync" and "no speech mouth layer" in item["message"] for item in report["issues"]))

    def _board(self, edit):
        board = read(self.project / "storyboard.json")
        edit(board)
        save(self.project / "storyboard.json", board)
        return scan(self.project)

    def test_long_idle_tail_after_last_line_is_reported(self):
        def edit(board):
            board["shots"][0]["dialogue"][0]["end_frame"] = 12  # 36 idle frames, allowance 24 + 6
        report = self._board(edit)
        self.assertTrue(any(item["category"] == "pacing" and item["shot"] == "shot_001" and "after the last line" in item["message"] for item in report["issues"]))
        self.assertIn("silent_ratio", report["pacing"])

    def test_authored_reaction_hold_covers_tail(self):
        def edit(board):
            board["shots"][0]["dialogue"][0]["end_frame"] = 12
            board["shots"][0]["direction"]["reaction_hold_frames"] = 12
        report = self._board(edit)
        self.assertFalse(any(item["category"] == "pacing" and item["shot"] == "shot_001" for item in report["issues"]))

    def test_idle_lead_before_first_line_is_reported(self):
        motion = read(self.project / "motion_plan.json")
        motion["shots"][0]["timeline"]["action_events"] = []
        save(self.project / "motion_plan.json", motion)

        def edit(board):
            board["shots"][0]["dialogue"][0]["start_frame"] = 30
        report = self._board(edit)
        self.assertTrue(any(item["category"] == "pacing" and "before the first line" in item["message"] for item in report["issues"]))

    def test_punchline_without_hold_across_cut_is_major(self):
        motion = read(self.project / "motion_plan.json")
        motion["shots"][0]["timeline"]["visual_events"] = [{
            "event_id": "pun", "priority": "punchline", "effect_type": "subtitle_emphasis",
            "start_frame": 20, "end_frame": 40, "description": "double meaning lands",
        }]
        save(self.project / "motion_plan.json", motion)

        def edit(board):
            board["shots"][0]["dialogue"][0]["end_frame"] = 46  # 2 frames to the cut
            board["shots"][1]["dialogue"][0]["start_frame"] = 1  # next speaker starts at once
        report = self._board(edit)
        self.assertEqual(report["status"], "FIX_REQUIRED")
        self.assertTrue(any(item["category"] == "punchline" and item["severity"] == "Major" for item in report["issues"]))

    def test_punchline_with_hold_passes(self):
        motion = read(self.project / "motion_plan.json")
        motion["shots"][0]["timeline"]["visual_events"] = [{
            "event_id": "pun", "priority": "punchline", "effect_type": "subtitle_emphasis",
            "start_frame": 20, "end_frame": 40, "description": "double meaning lands",
        }]
        save(self.project / "motion_plan.json", motion)
        report = scan(self.project)
        self.assertFalse(any(item["category"] == "punchline" for item in report["issues"]))

    def test_reverse_shot_with_same_background_is_noted(self):
        def edit(board):
            first, second = board["shots"][0], board["shots"][1]
            other = dict(second["characters"][0], character_id="bo")
            second["characters"] = [other]
            second["dialogue"][0]["speaker"] = "bo"
            second["direction"]["background_view"] = first["direction"]["background_view"]
        board = read(self.project / "storyboard.json")
        edit(board)
        from quality_gate import check_pacing
        report = {"issues": []}
        check_pacing(report, board, read(self.project / "motion_plan.json"), 24)
        self.assertTrue(any(item["category"] == "reverse_shot" and item["shot"] == "shot_002" for item in report["issues"]))

    def test_ending_without_reaction_is_noted(self):
        motion = read(self.project / "motion_plan.json")
        motion["shots"][-1]["timeline"]["expression_events"] = []
        save(self.project / "motion_plan.json", motion)
        report = scan(self.project)
        self.assertTrue(any(item["category"] == "ending" and item["severity"] == "Minor" for item in report["issues"]))

    def test_prop_motion_counts_as_an_ending_reaction(self):
        motion = read(self.project / "motion_plan.json")
        shot = motion["shots"][-1]
        shot["timeline"]["expression_events"] = []
        shot["layers"][1]["prop_motion"] = {"pivot": [0.5, 0.9], "events": [{"event_id": "wobble", "trigger": "pause", "kind": "lean",
                                              "start_frame": 43, "end_frame": 48, "amplitude_deg": 1, "description": "wobble"}]}
        save(self.project / "motion_plan.json", motion)
        self.assertFalse(any(item["category"] == "ending" for item in scan(self.project)["issues"]))

    def test_reveal_must_follow_the_setup_line_and_hold_before_speech(self):
        def edit(board):
            board["shots"][1]["reveal"] = {"what": "the hidden prop", "hold_frames": 12}
            board["shots"][0]["dialogue"][0]["end_frame"] = 20   # 28 frames between line end and cut
        report = self._board(edit)
        reveal = [item for item in report["issues"] if item["category"] == "reveal"]
        self.assertTrue(any("before the cut" in item["message"] and item["severity"] == "Major" for item in reveal))
        self.assertTrue(any("speaks" in item["message"] for item in reveal), "the line at frame 6 is inside the 12-frame hold")
        self.assertTrue(any(item["severity"] == "Minor" for item in reveal), "nothing happens during the hold")

    def test_well_timed_reveal_passes(self):
        motion = read(self.project / "motion_plan.json")
        motion["shots"][1]["timeline"]["sound_events"] = [{"event_id": "sting", "trigger": "information", "start_frame": 1, "peak_frame": 1, "settle_frame": 2, "end_frame": 5, "description": "reveal sting"}]
        save(self.project / "motion_plan.json", motion)

        def edit(board):
            board["shots"][1]["reveal"] = {"what": "the hidden prop", "hold_frames": 6}
        report = self._board(edit)
        self.assertFalse(any(item["category"] == "reveal" for item in report["issues"]))


if __name__ == "__main__":
    unittest.main()
