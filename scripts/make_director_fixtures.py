"""Create deterministic synthetic visual fixtures for the Phase 3 director renders."""
from __future__ import annotations

import argparse
from pathlib import Path

from make_character_performance_fixture import build as build_performance_fixture
from pipeline import read, save


def _shot(instance, source, intent, camera, emphasis, *beats, focus=None):
    return {
        'instance_id': instance, 'source_shot_id': source,
        'shot_intent': intent, 'camera_intent': camera, 'emphasis': emphasis,
        **({'focus_character': focus} if focus else {}), 'beats': list(beats),
    }


def _dialogue(beat_id, speaker, text, duration, intent, emotion, emphasis='normal',
              listeners=(), pause_before=0, pause_after=0, performance=None, shot_intent=None):
    value = {
        'beat_id': beat_id, 'kind': 'dialogue', 'speaker': speaker, 'text': text,
        'intent': intent, 'emotion': emotion, 'emphasis': emphasis,
        'listeners': list(listeners), 'performance_intent': performance or intent,
        'duration_frames': duration, 'pause_before': pause_before, 'pause_after': pause_after,
    }
    if shot_intent:
        value['shot_intent'] = shot_intent
    return value


def _reaction(beat_id, target, reaction, hold, pause_after=0):
    return {'beat_id': beat_id, 'kind': 'reaction', 'reaction_target': target,
            'reaction': reaction, 'reaction_hold': hold, 'pause_before': 0,
            'pause_after': pause_after}


def _make_project(project: Path, kind: str):
    build_performance_fixture(project)
    data = {name: read(project / f'{name}.json') for name in
            ('production_brief', 'characters', 'storyboard', 'motion_plan')}
    plan = {'version': '0.1', 'project_id': data['storyboard']['project_id'],
            'timing_source': 'director_plan', 'shots': []}
    if kind == 'comedy':
        plan['shots'] = [
            _shot('comedy_establish', 'shot_001', 'two_shot', 'static', 'normal',
                  {'beat_id': 'establish_hold', 'kind': 'pause', 'duration_frames': 10,
                   'pause_before': 0, 'pause_after': 0}),
            _shot('comedy_a_question', 'shot_002', 'speaker_medium', 'static', 'normal',
                  _dialogue('line_a_late', 'lin', '你昨天不是说今天一定不会迟到吗？', 62,
                            'ask', 'skeptical', listeners=['bo'], pause_after=5)),
            _shot('comedy_b_reply', 'shot_003', 'two_shot', 'static', 'normal',
                  _dialogue('line_b_yes', 'bo', '对啊。', 20, 'confirm', 'calm',
                            listeners=['lin'], pause_after=4)),
            _shot('comedy_a_time', 'shot_002', 'speaker_medium', 'static', 'important',
                  _dialogue('line_a_time', 'lin', '现在几点？', 28, 'ask', 'curious',
                            'important', ['bo'], pause_after=5)),
            _shot('comedy_b_silent_reaction', 'shot_004', 'listener_reaction', 'subtle_push', 'awkward',
                  _reaction('reaction_b_pause', 'bo', 'speechless', 22, pause_after=8), focus='bo'),
            _shot('comedy_b_punchline', 'shot_003', 'speaker_closeup', 'subtle_push', 'punchline',
                  _dialogue('line_b_punchline', 'bo', '这个问题不重要。', 36, 'joke', 'deadpan',
                            'punchline', ['lin'], pause_after=18), focus='bo'),
            _shot('comedy_a_speechless', 'shot_005', 'listener_reaction', 'static', 'awkward',
                  _reaction('reaction_a_speechless', 'lin', 'speechless', 24, pause_after=6), focus='lin'),
        ]
        data['production_brief'].update({
            'title': 'Phase 3 Dialogue Director · Comedy',
            'original_content': '你昨天不是说今天一定不会迟到吗？对啊。现在几点？这个问题不重要。',
            'tone': 'dry comedy; quiet timing and reaction holds',
        })
    elif kind == 'knowledge':
        plan['shots'] = [
            _shot('knowledge_question', 'shot_001', 'two_shot', 'static', 'normal',
                  _dialogue('question', 'lin', '为什么冰块会浮在水面上？', 48,
                            'ask', 'curious', listeners=['bo'], pause_after=8)),
            _shot('knowledge_explanation', 'shot_004', 'speaker_medium', 'static', 'normal',
                  _dialogue('explain_1', 'bo', '水结成冰时会膨胀，体积变大。', 55,
                            'explain', 'clear', listeners=['lin'], performance='explain_with_point', pause_after=5),
                  _dialogue('explain_2', 'bo', '同样重量占的空间更多，所以密度变小。', 64,
                            'explain', 'clear', listeners=['lin'], performance='explain_with_point')),
            _shot('knowledge_example', 'shot_002', 'two_shot', 'static', 'normal',
                  _dialogue('everyday_example', 'lin', '就像同一团面包发起来，占的位置更多？', 58,
                            'ask', 'understanding', listeners=['bo'], pause_after=5)),
            _shot('knowledge_confirmation', 'shot_004', 'speaker_medium', 'static', 'normal',
                  _dialogue('confirm', 'bo', '对，水的重量没变，但冰的密度更低，所以会浮起来。', 72,
                            'confirm', 'warm', listeners=['lin']))
        ]
        data['production_brief'].update({
            'title': 'Phase 3 Dialogue Director · Knowledge',
            'original_content': '为什么冰块会浮在水面上？水结成冰时会膨胀，体积变大。同样重量占的空间更多，所以密度变小。就像同一团面包发起来，占的位置更多？对，水的重量没变，但冰的密度更低，所以会浮起来。',
            'tone': 'calm, clear, patient explanation with one modest gesture',
        })
    else:
        raise ValueError('Unknown director fixture: '+kind)
    for narrative_beat in data['storyboard']['beats']:
        narrative_beat['source_excerpt'] = data['production_brief']['original_content']
    for name, value in data.items():
        save(project / f'{name}.json', value)
    save(project / 'director_plan.json', plan)
    return project


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind', choices=('comedy', 'knowledge'))
    parser.add_argument('project', type=Path)
    args = parser.parse_args()
    print(_make_project(args.project.resolve(), args.kind))
