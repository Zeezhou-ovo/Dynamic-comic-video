"""Resolve numeric directing policies into semantic Phase 3 plans, never coordinates."""
from copy import deepcopy

from manifest_validation import ROOT, read_json, validate_schema, registry_path


def resolve_mode(mode_id, overrides=None):
    overrides = {} if overrides is None else overrides
    manifest = read_json(registry_path('modes', mode_id))
    validate_schema('mode_manifest', manifest)
    if manifest['mode_id'] != mode_id:
        raise ValueError('Mode registry ID mismatch')
    validate_schema('production_profile', {'version': '0.1', 'mode_id': mode_id,
                    'template_id': 'validation', 'scene_id': 'validation', 'overrides': overrides})
    result = deepcopy(manifest)
    for section, values in overrides.items():
        result['policy'][section].update(values)
    validate_schema('mode_manifest', result)
    p = result['policy']
    if p['camera']['strength'] > 0 and not p['parallax']['enabled'] and any(
            p['camera'][key] != 'static' for key in ('intent', 'emphasis_intent')):
        raise ValueError('Moving multilayer camera requires parallax; use static camera when disabling it')
    return result


def direct_with_mode(script, mode, source_shot_ids, visible_characters):
    """Content → policy → Shot/Performance/Reaction Intent. All timing in frames."""
    validate_schema('dialogue_script', script)
    validate_schema('mode_manifest', mode)
    if not source_shot_ids:
        raise ValueError('Mode Resolver requires at least one source shot')
    if len({b['beat_id'] for b in script['beats']}) != len(script['beats']):
        raise ValueError('Duplicate content beat_id')
    p = mode['policy']
    shots, pending = [], []
    group_index = 0

    def normal_camera():
        cadence = p['camera']['motion_every_n_shots']
        return p['camera']['intent'] if cadence and (len(shots)+1) % cadence == 0 else 'static'

    def flush(emphasis='normal'):
        nonlocal pending, group_index
        if not pending:
            return
        emphasis_shot = emphasis != 'normal'
        intents = p['shot']['normal_intents']
        intent = p['shot']['emphasis_intent'] if emphasis_shot else intents[group_index % len(intents)]
        # Multiple speakers in a grouped shot must both remain framed.
        if len({b.get('speaker') for b in pending if b['kind'] == 'dialogue'}) > 1:
            intent = 'two_shot'
        shots.append({'instance_id': f'mode_shot_{len(shots)+1:03}',
                      'source_shot_id': source_shot_ids[group_index % len(source_shot_ids)],
                      'shot_intent': intent, 'camera_intent': p['camera']['emphasis_intent'] if emphasis_shot else normal_camera(),
                      'emphasis': emphasis, 'focus_character': pending[0].get('speaker'),
                      'visible_characters': list(visible_characters), 'visible_objects': [], 'beats': pending})
        pending = []
        group_index += 1

    for index, line in enumerate(script['beats']):
        speaker = line['speaker']
        if speaker not in visible_characters:
            raise ValueError('Content speaker not bound/visible: ' + speaker)
        emphasis = line['emphasis']
        if emphasis != 'normal':
            flush()
        duration = max(p['timing']['minimum_line_frames'], round(len(line['text']) * p['timing']['reading_frames_per_character']))
        pending.append({'beat_id': line['beat_id'], 'kind': 'dialogue', 'speaker': speaker,
                        'text': line['text'], 'intent': line['intent'], 'emotion': 'neutral',
                        'emphasis': emphasis, 'listeners': [c for c in visible_characters if c != speaker],
                        'performance_intent': 'explain_with_point' if line['intent'] == 'explain' and p['performance']['explain_gesture'] else line['intent'],
                        'duration_frames': duration,
                        'pause_before': p['timing']['emphasis_pause_before'] if emphasis != 'normal' else 0,
                        'pause_after': p['timing']['emphasis_pause_after'] if emphasis != 'normal' else p['timing']['line_pause_frames']})
        interval = p['reaction']['every_n_beats']
        reaction_due = bool(interval and (index+1) % interval == 0 and line.get('reaction', 'neutral') != 'neutral')
        if emphasis != 'normal' or len(pending) >= p['shot']['max_dialogue_beats'] or reaction_due:
            flush(emphasis)
        if reaction_due:
            flush()
            target = line.get('reaction_target') or next((c for c in visible_characters if c != speaker), speaker)
            if target not in visible_characters:
                raise ValueError('Reaction target not bound/visible: ' + target)
            shots.append({'instance_id': f'mode_shot_{len(shots)+1:03}',
                          'source_shot_id': source_shot_ids[group_index % len(source_shot_ids)],
                          'shot_intent': 'listener_reaction' if p['reaction']['closeup'] else 'two_shot',
                          'camera_intent': normal_camera(), 'emphasis': 'normal',
                          'focus_character': target, 'visible_characters': list(visible_characters), 'visible_objects': [],
                          'beats': [{'beat_id': line['beat_id']+'_reaction', 'kind': 'reaction', 'reaction_target': target,
                                     'reaction': line['reaction'], 'reaction_strength': p['reaction']['strength'],
                                     'reaction_hold': p['reaction']['hold_frames'], 'pause_before': 0, 'pause_after': 0}]})
    flush()
    result = {'version': '0.1', 'project_id': script['project_id'], 'timing_source': 'director_plan',
              'runtime_policy': deepcopy(p), 'shots': shots}
    validate_schema('director_plan', result)
    return result


def plan_metrics(plan):
    from director import parse_dialogue_beats
    beats = parse_dialogue_beats(plan)
    durations = [sum(b.get('duration_frames', b.get('reaction_hold', 0)) + b['pause_before'] + b['pause_after'] for b in s['beats']) for s in plan['shots']]
    camera_strength = plan.get('runtime_policy', {}).get('camera', {}).get('strength', 1)
    return {'shot_count': len(durations), 'average_shot_frames': sum(durations)/len(durations),
            'reaction_shots': sum(any(b['kind']=='reaction' for b in s['beats']) for s in plan['shots']),
            'punchline_hold_frames': sum(b['pause_before']+b['pause_after'] for b in beats if b.get('emphasis')=='punchline'),
            'camera_emphasis': camera_strength * sum({'static':0,'subtle_push':1,'stronger_push':2,'follow':1}[s['camera_intent']] for s in plan['shots'])}
