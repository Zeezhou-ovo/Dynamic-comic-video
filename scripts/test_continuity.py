"""Pre-generation continuity checks: posture/placement and shot/reverse-shot backgrounds."""
import unittest

from continuity import posture_warnings, prompt_instructions, reverse_pairs, reverse_warnings


def shot(sid, characters, camera="front", background="wall with board", scene="office"):
    return {"id": sid, "characters": characters,
            "direction": {"scene_id": scene, "camera_position": camera, "background_view": background}}


def char(cid, posture=None, placement=None, change=None):
    item = {"character_id": cid}
    if posture:
        item["posture"] = posture
    if placement:
        item["placement"] = placement
    if change:
        item["posture_change"] = change
    return item


class ContinuityTests(unittest.TestCase):
    def test_unshown_posture_change_is_flagged(self):
        board = {"shots": [
            shot("s1", [char("cat", "seated", "behind the desk")]),
            shot("s2", [char("capy", "seated")], camera="reverse", background="shelves"),
            shot("s3", [char("cat", "standing", "in front of the desk"), char("capy", "riding")], camera="wide"),
        ]}
        warnings = posture_warnings(board)
        self.assertEqual([(w["shot"], w["check"]) for w in warnings], [("s3", "posture"), ("s3", "posture")])
        self.assertIn("cat is seated in s1 but standing here", warnings[0]["message"])

    def test_bracketed_notes_do_not_count_as_a_move(self):
        board = {"shots": [shot("s1", [char("capy", "riding", "木马上（画面外）")]), shot("s2", [char("capy", "riding", "木马上")])]}
        self.assertEqual(posture_warnings(board), [])

    def test_explained_change_and_other_scenes_are_fine(self):
        board = {"shots": [
            shot("s1", [char("cat", "seated", "behind the desk")]),
            shot("s2", [char("cat", "standing", "in front of the desk", change="slams the desk and stands up in this shot")]),
            shot("s3", [char("cat", "lying")], scene="home"),
        ]}
        self.assertEqual(posture_warnings(board), [])

    def test_placement_change_is_flagged_when_posture_matches(self):
        board = {"shots": [shot("s1", [char("cat", "standing", "by the window")]),
                           shot("s2", [char("cat", "standing", "by the door")])]}
        self.assertEqual([w["check"] for w in posture_warnings(board)], ["placement"])

    def test_reverse_pair_detection_and_same_background_warning(self):
        board = {"shots": [
            shot("s1", [char("cat")], camera="facing right", background="green board and window"),
            shot("s2", [char("capy")], camera="facing left", background="green board and window"),
            shot("s3", [char("cat"), char("capy")], camera="wide"),
        ]}
        self.assertEqual(list(reverse_pairs(board)), ["s2"])
        self.assertEqual([w["check"] for w in reverse_warnings(board)], ["reverse_background"])
        board["shots"][1]["direction"]["background_view"] = "door and coat rack"
        self.assertEqual(reverse_warnings(board), [])

    def test_prompt_lines_carry_posture_and_reverse_angle(self):
        board = {"shots": [
            shot("s1", [char("cat", "seated", "behind the desk")], camera="facing right", background="green board"),
            shot("s2", [char("capy", "riding")], camera="facing left", background="door"),
            shot("s3", [char("cat", "seated", "behind the desk")], camera="wide"),
        ]}
        lines = prompt_instructions(board, "s2")
        self.assertTrue(any("Reverse angle of s1" in line and "not 'green board'" in line for line in lines))
        self.assertIn("capy: riding", lines)
        self.assertTrue(any("same as the previous shot" in line for line in prompt_instructions(board, "s3")))
        self.assertEqual(prompt_instructions({"shots": [shot("x", [char("a")])]}, "x"), [])


if __name__ == "__main__":
    unittest.main()
