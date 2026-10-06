"""Phase 3 Dialogue & Performance Director contract and timeline tests."""
import tempfile
import unittest
from pathlib import Path

from director import (compile_director_plan, map_reaction, parse_dialogue_beats,
                      resolve_shot_intent)
from make_director_fixtures import _make_project
from pipeline import read, validate


class DirectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.comedy = _make_project(Path(self.temp.name) / 'comedy', 'comedy')
        self.knowledge = _make_project(Path(self.temp.name) / 'knowledge', 'knowledge')

    def tearDown(self):
        self.temp.cleanup()

    def _load(self, project):
        data = {name: read(project / f'{name}.json') for name in
                ('production_brief', 'characters', 'storyboard', 'motion_plan')}
        return read(project / 'director_plan.json'), data

    def test_dialogue_beat_parser_preserves_authored_order_and_ids(self):
        plan, _ = self._load(self.comedy)
        beats = parse_dialogue_beats(plan)
        self.assertEqual(beats[0]['beat_id'], 'establish_hold')
        self.assertEqual(beats[-1]['beat_id'], 'reaction_a_speechless')
        plan['shots'][-1]['beats'][0]['beat_id'] = beats[0]['beat_id']
        with self.assertRaisesRegex(ValueError, 'duplicate beat_id'):
            parse_dialogue_beats(plan)

    def test_shot_intent_and_emphasis_resolve_to_camera_runtime_intent(self):
        resolved = resolve_shot_intent('speaker_closeup', 'static', 'punchline')
        self.assertEqual(resolved['framing'], 'close_up')
        self.assertEqual(resolved['camera_intent'], 'subtle_push')
        self.assertEqual(resolved['type'], 'push_in')

    def test_reaction_mapping_uses_existing_expression_and_performance_capability(self):
        plan, data = self._load(self.comedy)
        source = next(item for item in data['motion_plan']['shots'] if item['shot_id'] == 'shot_004')
        board = next(item for item in data['storyboard']['shots'] if item['id'] == 'shot_004')
        character = next(item for item in data['characters']['characters'] if item['id'] == 'bo')
        mapped = map_reaction('speechless', character, source, board, 22)
        self.assertEqual(mapped['expression'], 'surprised')
        self.assertEqual(mapped['events'][0]['preset'], 'blink')
        self.assertEqual(mapped['shot_intent'], 'listener_reaction')
        self.assertEqual(mapped['camera_intent'], 'subtle_push')

    def test_compiled_director_timeline_is_authoritative_and_contiguous(self):
        plan, data = self._load(self.comedy)
        rendered = compile_director_plan(plan, data)
        self.assertEqual(rendered, compile_director_plan(plan, data))
        shots = rendered['motion_plan']['shots']
        cursor = 0
        for shot in shots:
            self.assertEqual(shot['start_frame'], cursor)
            cursor += shot['duration_frames']
        self.assertEqual(cursor, rendered['production_brief']['format']['duration_frames'])
        first_dialogue = next(item for item in rendered['storyboard']['shots'] if item['id'] == 'comedy_a_question')
        motion = next(item for item in shots if item['shot_id'] == 'comedy_a_question')
        # The five frame pause_after is held in the director-owned shot interval.
        self.assertEqual(motion['duration_frames'] - first_dialogue['dialogue'][-1]['end_frame'], 5)

    def test_reaction_shot_can_be_silent_and_calls_character_and_camera_runtimes(self):
        plan, data = self._load(self.comedy)
        rendered = compile_director_plan(plan, data)
        shot = next(item for item in rendered['motion_plan']['shots'] if item['shot_id'] == 'comedy_b_silent_reaction')
        board = next(item for item in rendered['storyboard']['shots'] if item['id'] == 'comedy_b_silent_reaction')
        self.assertEqual(board['dialogue'], [])
        self.assertEqual(shot['camera']['type'], 'push_in')
        self.assertEqual(shot['camera_intent'], 'subtle_push')
        bo = next(item for item in shot['character_performance'] if item['character_id'] == 'bo')
        self.assertEqual(bo['role'], 'listener')
        self.assertEqual(bo['expression'], 'surprised')
        self.assertEqual(bo['events'][0]['preset'], 'blink')

    def test_punchline_adds_actual_hold_and_changes_camera_and_caption_emphasis(self):
        plan, data = self._load(self.comedy)
        rendered = compile_director_plan(plan, data)
        punchline = next(item for item in rendered['storyboard']['shots'] if item['id'] == 'comedy_b_punchline')
        motion = next(item for item in rendered['motion_plan']['shots'] if item['shot_id'] == 'comedy_b_punchline')
        cue = punchline['dialogue'][0]
        self.assertEqual(cue['emphasis'], 'punchline')
        self.assertEqual(motion['camera_intent'], 'subtle_push')
        self.assertEqual(motion['duration_frames'] - cue['end_frame'], 18)

    def test_speaker_listener_assignment_maps_explanation_to_phase2_gesture(self):
        plan, data = self._load(self.knowledge)
        rendered = compile_director_plan(plan, data)
        shot = next(item for item in rendered['motion_plan']['shots'] if item['shot_id'] == 'knowledge_explanation')
        bo = next(item for item in shot['character_performance'] if item['character_id'] == 'bo')
        lin = next(item for item in shot['character_performance'] if item['character_id'] == 'lin')
        self.assertEqual(bo['role'], 'speaker')
        self.assertEqual([event['preset'] for event in bo['events']], ['point', 'point'])
        self.assertEqual(lin['role'], 'listener')

    def test_both_example_plans_pass_pipeline_and_runtime_validation(self):
        for project in (self.comedy, self.knowledge):
            _, errors, _ = validate(project)
            self.assertEqual(errors, [])

    def test_reveal_cuts_on_the_setup_line_and_holds_before_speech(self):
        plan, data = self._load(self.comedy)
        punch = next(index for index, entry in enumerate(plan['shots']) if entry['instance_id'] == 'comedy_b_punchline')
        reveal_shot = dict(plan['shots'][punch + 1])
        reveal_shot['instance_id'] = 'comedy_reveal'
        reveal_shot['beats'] = [{'beat_id': 'reveal_prop', 'kind': 'reveal', 'reveal_what': 'what the joke was about',
                                 'pause_before': 0, 'pause_after': 0}] + [
            {**beat, 'beat_id': beat['beat_id'] + '_r'} for beat in reveal_shot['beats']]
        plan['shots'].insert(punch + 1, reveal_shot)
        rendered = compile_director_plan(plan, data)
        board = {shot['id']: shot for shot in rendered['storyboard']['shots']}
        setup = board['comedy_b_punchline']
        self.assertLessEqual(setup['duration_frames'] - setup['dialogue'][-1]['end_frame'], 4, 'cut as the setup line ends')
        reveal = board['comedy_reveal']
        self.assertEqual(reveal['reveal'], {'what': 'what the joke was about', 'hold_frames': 14})
        first_line = min((cue['start_frame'] for cue in reveal['dialogue']), default=reveal['duration_frames'])
        self.assertGreaterEqual(first_line, 14)

    def test_reveal_must_open_a_later_shot(self):
        plan, data = self._load(self.comedy)
        plan['shots'][0]['beats'].insert(0, {'beat_id': 'too_early', 'kind': 'reveal', 'reveal_what': 'x', 'pause_before': 0, 'pause_after': 0})
        with self.assertRaisesRegex(ValueError, 'first shot cannot be a reveal'):
            compile_director_plan(plan, data)
        plan, data = self._load(self.comedy)
        plan['shots'][1]['beats'].append({'beat_id': 'late', 'kind': 'reveal', 'reveal_what': 'x', 'pause_before': 0, 'pause_after': 0})
        with self.assertRaisesRegex(ValueError, 'first beat'):
            compile_director_plan(plan, data)


if __name__ == '__main__':
    unittest.main()
