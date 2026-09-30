"""Semantic dialogue director and deterministic compilation into existing runtimes."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from production import wav_timing

RULES_PATH = Path(__file__).resolve().parents[1] / 'config' / 'director_rules.json'


def rules():
    return json.loads(RULES_PATH.read_text(encoding='utf-8'))


def parse_dialogue_beats(value):
    """Validate and flatten semantic dialogue/reaction/pause beats in authored order."""
    shots = value.get('shots', [])
    beats = [beat for shot in shots for beat in shot['beats']]
    ids = [beat['beat_id'] for beat in beats]
    if len(ids) != len(set(ids)):
        raise ValueError('director_plan contains duplicate beat_id values')
    return beats


def resolve_shot_intent(intent, requested_camera=None, emphasis='normal'):
    config = rules()
    shot = config['shot_intents'][intent]
    camera = requested_camera or shot['camera']
    emphasis_camera = config['emphasis'][emphasis]['camera']
    priority = {'static': 0, 'subtle_push': 1, 'follow': 1, 'stronger_push': 2}
    if priority[emphasis_camera] > priority[camera]:
        camera = emphasis_camera
    return {**shot, 'camera_intent': camera, **config['camera_intents'][camera]}


def _manifest_for(characters, character_id):
    return next(item for item in characters if item['id'] == character_id)


def _event(event_id, preset, start, duration, part=None):
    # Leave the last frame available for deterministic settle and respect the
    # Phase 2 event envelope's ordered prepare / peak / settle / end phases.
    end = max(start, min(duration - 1, start + max(3, min(12, duration // 2))))
    peak = start + max(0, (end - start) // 3)
    settle = peak + max(0, (end - peak) // 2)
    item = {'event_id': event_id, 'preset': preset, 'start_frame': start,
            'peak_frame': peak, 'settle_frame': settle, 'end_frame': end}
    if part:
        item['part'] = part
    return item


def map_reaction(kind, character, source_motion, source_board, duration, start_frame=0,
                 strength='medium'):
    """Resolve reaction semantics using config and only declared/available assets."""
    config = rules()['reactions'][kind]
    capabilities = character.get('capabilities', {})
    expression = next((name for name in config['expression_candidates']
                       if name in capabilities.get('expressions', [])), None)
    board_layers = {layer['id']: layer for layer in source_board['layers']}
    layers = [layer for layer in source_motion['layers']
              if board_layers.get(layer['layer_id'], {}).get('character_id') == character['id']]
    state_names = {name for layer in layers for name in layer.get('state_assets', {})}
    if expression and f'expression:{expression}' not in state_names:
        expression = None
    preset = config['event']
    if preset == 'blink' and 'blink' not in {name for layer in layers for name in layer.get('state_assets', {})}:
        preset = None
    if preset and preset in ('nod', 'shake_head') and 'head' not in capabilities.get('parts', []):
        preset = None
    if preset == 'small_bounce' and 'body' not in capabilities.get('parts', []):
        preset = None
    if preset and preset in ('point', 'raise_hand') and not ({'arm', 'left_arm', 'right_arm'} & set(capabilities.get('parts', []))):
        preset = None
    events = [_event(f'reaction_{kind}', preset, start_frame, duration,
                     rules()['event_part'].get(preset))] if preset and duration > start_frame else []
    amplitude = {'subtle': .55, 'medium': .75, 'strong': 1.0}[strength]
    for event in events:
        event['amplitude'] = amplitude
    return {'expression': expression, 'events': events,
            'shot_intent': config['shot_intent'], 'camera_intent': config['camera'],
            'hold_frames': config['hold_frames']}


def _camera_plan(intent, focus, duration, framing, source_motion, canvas):
    config = rules()['camera_intents'][intent]
    camera_type = config['type']
    base_zoom = {'wide': 1.0, 'medium': 1.04, 'close_up': 1.8}[framing]
    pose = {'x': focus[0], 'y': focus[1], 'zoom': base_zoom}
    screen_target = {'x': focus[0] / canvas['width'], 'y': focus[1] / canvas['height']}
    if camera_type == 'static':
        return {'type': 'static', 'focus_target': {'x': focus[0], 'y': focus[1]},
                'from': pose, 'to': dict(pose), 'parallax_enabled': False,
                'screen_target': screen_target, 'easing': 'easeInOut'}
    end = {**pose, 'zoom': base_zoom + config['zoom_delta']}
    depths = {layer.get('depth', 'character') for layer in source_motion['layers']}
    parallax = len(depths) > 1
    result = {'type': camera_type, 'focus_target': {'x': focus[0], 'y': focus[1]},
            'from': pose, 'to': end, 'parallax_enabled': parallax,
            'screen_target': screen_target, 'easing': 'easeInOut'}
    if camera_type == 'follow':
        result['follow_path'] = [
            {'frame': 0, 'x': pose['x'], 'y': pose['y']},
            {'frame': max(1, duration - 1), 'x': end['x'], 'y': end['y']},
        ]
    return result


def compile_director_plan(plan, data, project=None):
    """Return a render-ready data copy whose absolute frame timeline is director-owned."""
    parse_dialogue_beats(plan)
    if plan.get('project_id') != data['storyboard'].get('project_id'):
        raise ValueError('director_plan project_id mismatch')
    board = data['storyboard']
    motion = data['motion_plan']
    board_by_id = {shot['id']: shot for shot in board['shots']}
    motion_by_id = {shot['shot_id']: shot for shot in motion['shots']}
    chars = data['characters']['characters']
    character_ids = {char['id'] for char in chars}
    timeline_board, timeline_motion = [], []
    absolute_cursor = 0
    for entry in plan['shots']:
        source_id = entry['source_shot_id']
        if source_id not in board_by_id or source_id not in motion_by_id:
            raise ValueError('director_plan references unknown source shot '+source_id)
        source_board = board_by_id[source_id]
        source_motion = motion_by_id[source_id]
        visible = [char['character_id'] for char in source_board['characters']]
        beats = entry['beats']
        speakers = {beat.get('speaker') for beat in beats if beat['kind'] == 'dialogue'}
        listeners = {item for beat in beats if beat['kind'] == 'dialogue' for item in beat.get('listeners', [])}
        listeners.update(beat['reaction_target'] for beat in beats if beat['kind'] == 'reaction')
        if not speakers | listeners <= character_ids:
            raise ValueError('director_plan uses unknown speaker/listener '+entry['instance_id'])
        if not speakers | listeners <= set(visible):
            raise ValueError('speaker/listener is not visible in source shot '+source_id)
        focus_character = entry.get('focus_character') or next(iter(speakers or visible), visible[0])
        if focus_character not in visible:
            raise ValueError('focus_character is not visible in source shot '+source_id)
        # Existing storyboard order is the authored stage layout. The resolver
        # derives a normalized focus anchor instead of accepting camera numbers.
        canvas = data['production_brief']['format']
        focus = ((.32 if visible.index(focus_character) == 0 and len(visible) > 1 else
                  .68 if len(visible) > 1 else .5) * canvas['width'], .46 * canvas['height'])
        beat_shot_intents = {beat['shot_intent'] for beat in beats if beat.get('shot_intent')}
        if len(beat_shot_intents) > 1:
            raise ValueError('one shot instance cannot resolve multiple shot_intent values '+entry['instance_id'])
        shot_intent = next(iter(beat_shot_intents), entry['shot_intent'])
        requested_camera = entry['camera_intent']
        reaction_beat = next((beat for beat in beats if beat['kind'] == 'reaction'), None)
        if reaction_beat and requested_camera == 'static':
            requested_camera = rules()['reactions'][reaction_beat['reaction']]['camera']
        resolved = resolve_shot_intent(shot_intent, requested_camera, entry['emphasis'])
        if entry['emphasis'] == 'punchline' and entry['camera_intent'] == 'static':
            resolved = resolve_shot_intent(entry['shot_intent'], 'subtle_push', entry['emphasis'])

        local_cursor = 0
        cues = []
        reaction_specs = []
        emphasis_pause = rules()['emphasis'][entry['emphasis']]['default_pause_frames']
        for beat in beats:
            local_cursor += beat.get('pause_before', 0)
            pause_after = max(beat.get('pause_after', 0), emphasis_pause)
            if beat['kind'] == 'dialogue':
                duration = beat['duration_frames']
                # Authored local audio, when present, determines speech length.
                original = next((cue for cue in source_board.get('dialogue', [])
                                 if cue.get('speaker') == beat['speaker'] and cue.get('text') == beat['text'] and cue.get('audio')), None)
                if original:
                    beat_audio = original['audio']
                    if project is not None:
                        audio_path = Path(project) / beat_audio
                        if not audio_path.resolve().is_relative_to(Path(project).resolve()):
                            raise ValueError('Dialogue audio escapes the project: '+beat_audio)
                        if not audio_path.is_file():
                            raise ValueError('Missing dialogue audio '+beat_audio)
                        duration = wav_timing(audio_path, data['production_brief']['format']['fps'])[0]
                else:
                    beat_audio = None
                cue = {'speaker': beat['speaker'], 'text': beat['text'],
                       'start_frame': local_cursor, 'end_frame': local_cursor + duration,
                       'emphasis': beat.get('emphasis', entry['emphasis']),
                       'beat_id': beat['beat_id']}
                if beat_audio:
                    cue['audio'] = beat_audio
                cues.append(cue)
                local_cursor += duration + pause_after
            elif beat['kind'] == 'reaction':
                target = beat['reaction_target']
                if target not in visible or target not in character_ids:
                    raise ValueError('reaction_target is not visible in source shot '+source_id)
                hold = beat['reaction_hold'] or rules()['reactions'][beat['reaction']]['hold_frames']
                reaction_specs.append((target, beat['reaction'], local_cursor, hold,
                                       beat['beat_id'], beat.get('reaction_strength', 'medium')))
                local_cursor += hold + pause_after
            else:
                local_cursor += beat['duration_frames'] + pause_after
        duration_frames = max(2, local_cursor)
        board_copy = deepcopy(source_board)
        board_copy.update({'id': entry['instance_id'], 'duration_frames': duration_frames,
                           'dialogue': cues, 'shot_size': resolved['framing']})
        if board_copy.get('direction'):
            direction = board_copy['direction']
            next_instance = (plan['shots'][plan['shots'].index(entry) + 1]['instance_id']
                             if plan['shots'].index(entry) + 1 < len(plan['shots']) else None)
            direction.update({
                'camera_position': resolved['camera_intent'],
                'view_id': entry['instance_id'],
                'cut_reason': 'Director plan: '+entry['shot_intent']+' / '+entry['emphasis'],
                'next_shot_id': next_instance,
                'reaction_hold_frames': sum(spec[3] for spec in reaction_specs),
                'listening_reactions': [
                    {'character_id': beat['reaction_target'], 'response': beat['reaction']}
                    for beat in beats if beat['kind'] == 'reaction'
                ],
            })
        motion_copy = deepcopy(source_motion)
        motion_copy.update({'shot_id': entry['instance_id'], 'start_frame': absolute_cursor,
                            'duration_frames': duration_frames,
                            'camera': _camera_plan(resolved['camera_intent'], focus, duration_frames,
                                                   resolved['framing'], source_motion, canvas),
                            'shot_intent': shot_intent, 'camera_intent': resolved['camera_intent'],
                            'framing': resolved['framing'], 'emphasis': entry['emphasis']})
        motion_copy['character_performance'] = []
        for character_id in visible:
            character = _manifest_for(chars, character_id)
            character_intents = [beat.get('performance_intent', beat.get('intent')) for beat in beats
                                 if beat['kind'] == 'dialogue' and beat.get('speaker') == character_id]
            performance_config = rules()['performance_intents']
            mapped_actions = [performance_config[intent] for intent in character_intents if intent in performance_config]
            action_role = next((action['speaker'] for action in mapped_actions if action['speaker'] != 'idle'), 'idle')
            role = ('speaker' if action_role == 'talk' else 'idle') if character_id in speakers else ('listener' if character_id in listeners else 'idle')
            performer = {'character_id': character_id, 'role': role, 'events': []}
            # Intersperse semantic reaction without asking the renderer to make
            # directorial choices. A shot should contain at most one reaction beat.
            target_reaction = next((spec for spec in reaction_specs if spec[0] == character_id), None)
            if target_reaction:
                _, reaction_kind, offset, hold, beat_id, strength = target_reaction
                mapped = map_reaction(reaction_kind, character, source_motion, source_board,
                                      duration_frames, offset, strength)
                performer['expression'] = mapped['expression']
                performer['events'].extend(mapped['events'])
            else:
                for beat in beats:
                    if beat['kind'] != 'dialogue' or beat.get('speaker') != character_id:
                        continue
                    intent = beat.get('performance_intent', beat.get('intent'))
                    if intent not in performance_config:
                        raise ValueError('Unknown performance_intent '+intent)
                    gesture = performance_config[intent].get('gesture')
                    if gesture:
                        cue = next(cue for cue in cues if cue['beat_id'] == beat['beat_id'])
                        performer['events'].append(_event(
                            f'{cue["beat_id"]}_{gesture}', gesture,
                            cue['start_frame'], duration_frames,
                            rules()['event_part'].get(gesture)))
            motion_copy['character_performance'].append(performer)
        timeline_board.append(board_copy)
        timeline_motion.append(motion_copy)
        absolute_cursor += duration_frames
    if absolute_cursor < 2:
        raise ValueError('director_plan timeline must be at least two frames')
    result = deepcopy(data)
    result['storyboard']['shots'] = timeline_board
    result['motion_plan']['shots'] = timeline_motion
    result['production_brief']['format']['duration_frames'] = absolute_cursor
    result['director_plan'] = deepcopy(plan)
    return result


def validate_director_plan(plan, data):
    """Report compile-time semantic incompatibilities with stable, actionable errors."""
    errors = []
    try:
        compiled = compile_director_plan(plan, data)
    except (ValueError, KeyError, StopIteration) as exc:
        return [str(exc)]
    ids = {item['id'] for item in data['characters']['characters']}
    for beat in parse_dialogue_beats(plan):
        if beat['kind'] == 'dialogue':
            for name in [beat['speaker'], *beat['listeners']]:
                if name not in ids:
                    errors.append('Unknown dialogue speaker/listener '+name)
        if beat['kind'] == 'reaction' and beat['reaction_target'] not in ids:
            errors.append('Unknown reaction target '+str(beat['reaction_target']))
    return errors
