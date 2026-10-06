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


def _resolved_camera_plan(intent, composition, duration, source_motion):
    """Turn a semantic composition target into the Phase 1 camera contract."""
    config = rules()['camera_intents'][intent]
    camera_type = config['type']
    target = composition['target']
    focus = {'id': target.get('id'), 'x': target['x'], 'y': target['y']}
    base = {'x': target['x'], 'y': target['y'], 'zoom': composition['zoom']}
    screen = composition['screen_target']
    depths = {layer['depth'] for layer in source_motion.get('scene_depth_layers', [])}
    # scene_depth_layers is supplied by the caller to avoid teaching Camera about Scene.
    moving = camera_type != 'static'
    parallax = moving and len(depths) > 1
    if not moving:
        return {'type': 'static', 'focus_target': focus, 'from': base, 'to': dict(base),
                'parallax_enabled': False, 'screen_target': screen, 'easing': 'easeInOut'}
    end = {**base, 'zoom': base['zoom'] + config['zoom_delta']}
    result = {'type': camera_type, 'focus_target': focus, 'from': base, 'to': end,
              'parallax_enabled': parallax, 'screen_target': screen, 'easing': 'easeInOut'}
    if camera_type == 'follow':
        result['follow_path'] = [{'frame': 0, 'x': base['x'], 'y': base['y']},
                                 {'frame': max(1, duration - 1), 'x': end['x'], 'y': end['y']}]
    return result


def compile_director_plan(plan, data, project=None, scene_manifest=None, character_asset_manifest=None):
    """Return a render-ready data copy whose absolute frame timeline is director-owned."""
    parse_dialogue_beats(plan)
    policy = plan.get('runtime_policy')
    if policy is not None:
        from manifest_validation import validate_schema
        validate_schema('director_plan', plan)
    parallax_strengths = None
    if policy:
        intensity = policy['parallax']['strength']
        defaults = {'foreground': 1.2, 'character': 1, 'midground': .55, 'background': .2, 'sky': .05}
        parallax_strengths = {depth: 1 + (value - 1) * intensity for depth, value in defaults.items()}
    if plan.get('project_id') != data['storyboard'].get('project_id'):
        raise ValueError('director_plan project_id mismatch')
    board = data['storyboard']
    motion = data['motion_plan']
    board_by_id = {shot['id']: shot for shot in board['shots']}
    motion_by_id = {shot['shot_id']: shot for shot in motion['shots']}
    chars = data['characters']['characters']
    if project is not None:
        project_path = Path(project)
        scene_path = project_path / 'scene_manifest.json'
        character_assets_path = project_path / 'character_assets.json'
        if scene_manifest is None and scene_path.is_file():
            scene_manifest = json.loads(scene_path.read_text(encoding='utf-8'))
        if character_asset_manifest is None and character_assets_path.is_file():
            character_asset_manifest = json.loads(character_assets_path.read_text(encoding='utf-8'))
    phase4 = scene_manifest is not None or character_asset_manifest is not None
    if phase4 and (scene_manifest is None or character_asset_manifest is None):
        raise ValueError('Scene Manifest and Character Asset Manifest must be provided together')
    if phase4:
        from composition_resolver import resolve_composition
        if scene_manifest['project_id'] != plan['project_id'] or character_asset_manifest['project_id'] != plan['project_id']:
            raise ValueError('Scene/Character Asset Manifest project_id mismatch')
    character_ids = {char['id'] for char in chars}
    timeline_board, timeline_motion = [], []
    absolute_cursor = 0
    reveal_rules = rules()['reveal']
    for index, entry in enumerate(plan['shots']):
        if entry['beats'][0]['kind'] != 'reveal' and any(beat['kind'] == 'reveal' for beat in entry['beats']):
            raise ValueError('reveal must be the first beat of its shot '+entry['instance_id'])
        if entry['beats'][0]['kind'] == 'reveal' and index == 0:
            raise ValueError('the first shot cannot be a reveal; it pays off a previous line '+entry['instance_id'])
    for index, entry in enumerate(plan['shots']):
        # a reveal in the next shot pays off this shot's last line: cut as that line ends
        cut_into_reveal = index + 1 < len(plan['shots']) and plan['shots'][index + 1]['beats'][0]['kind'] == 'reveal'
        source_id = entry['source_shot_id']
        if source_id not in board_by_id or source_id not in motion_by_id:
            raise ValueError('director_plan references unknown source shot '+source_id)
        source_board = board_by_id[source_id]
        source_motion = motion_by_id[source_id]
        beats = entry['beats']
        default_visible = [item['character_id'] for item in source_board['characters']]
        if phase4:
            default_visible = [item['character_id'] for item in scene_manifest['character_instances'] if item['visible']]
        visible = list(entry.get('visible_characters', default_visible))
        if len(visible) != len(set(visible)):
            raise ValueError('visible_characters contains duplicates '+entry['instance_id'])
        speakers = {beat.get('speaker') for beat in beats if beat['kind'] == 'dialogue'}
        listeners = {item for beat in beats if beat['kind'] == 'dialogue' for item in beat.get('listeners', [])}
        listeners.update(beat['reaction_target'] for beat in beats if beat['kind'] == 'reaction')
        if not speakers | listeners <= character_ids:
            raise ValueError('director_plan uses unknown speaker/listener '+entry['instance_id'])
        if not speakers | listeners <= set(visible):
            raise ValueError('speaker/listener is not visible in source shot '+source_id)
        first_speaker = next((beat['speaker'] for beat in beats if beat['kind'] == 'dialogue'), None)
        first_reaction = next((beat['reaction_target'] for beat in beats if beat['kind'] == 'reaction'), None)
        focus_character = entry.get('focus_character') or first_speaker or first_reaction or (visible[0] if visible else None)
        if focus_character is not None and focus_character not in visible:
            raise ValueError('focus_character is not visible in source shot '+source_id)
        canvas = data['production_brief']['format']
        beat_shot_intents = [beat['shot_intent'] for beat in beats if beat.get('shot_intent')]
        if len(set(beat_shot_intents)) > 1:
            raise ValueError('one shot instance cannot resolve multiple shot_intent values '+entry['instance_id'])
        shot_intent = beat_shot_intents[0] if beat_shot_intents else entry['shot_intent']
        requested_camera = entry['camera_intent']
        reaction_beat = next((beat for beat in beats if beat['kind'] == 'reaction'), None)
        if reaction_beat and requested_camera == 'static':
            requested_camera = rules()['reactions'][reaction_beat['reaction']]['camera']
        resolved = resolve_shot_intent(shot_intent, requested_camera, entry['emphasis'])
        if entry['emphasis'] == 'punchline' and entry['camera_intent'] == 'static':
            resolved = resolve_shot_intent(entry['shot_intent'], 'subtle_push', entry['emphasis'])

        if policy:
            # Mode resolver owns camera selection; don't promote static holds
            # using legacy reaction/emphasis defaults.
            resolved = {**resolved, 'camera_intent': entry['camera_intent'],
                        **rules()['camera_intents'][entry['camera_intent']]}
        if policy and (policy['camera']['strength'] == 0 or
                       (entry['camera_intent'] == 'static' and policy['camera']['emphasis_intent'] == 'static')):
            # A static policy overrides legacy emphasis/reaction camera promotion.
            resolved = {**resolved, 'camera_intent': 'static', 'type': 'static', 'zoom_delta': 0}

        composition = None
        if phase4:
            depth_count = len({layer['depth'] for layer in scene_manifest['layers'] if layer['kind'] == 'render_layer'})
            composition = resolve_composition(
                scene_manifest, character_asset_manifest, shot_intent, visible,
                focus_character=focus_character, focus_object=entry.get('focus_object'),
                character_bindings=entry.get('character_bindings'),
                visible_objects=entry.get('visible_objects'), viewport=canvas,
                parallax_enabled=(resolved['camera_intent'] != 'static' and depth_count > 1),
                parallax_strengths=parallax_strengths,
            )

        local_cursor = 0
        cues = []
        reaction_specs = []
        emphasis_pause = (0 if policy else rules()['emphasis'][entry['emphasis']]['default_pause_frames'])
        reveal_spec = None
        for beat_index, beat in enumerate(beats):
            local_cursor += beat.get('pause_before', 0)
            pause_after = max(beat.get('pause_after', 0), emphasis_pause)
            if cut_into_reveal and beat_index == len(beats) - 1:
                pause_after = min(pause_after, reveal_rules['max_cut_delay_frames'])
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
            elif beat['kind'] == 'reveal':
                hold = beat.get('duration_frames', reveal_rules['default_hold_frames'])
                reveal_spec = {'what': beat['reveal_what'], 'hold_frames': hold}
                local_cursor += hold + pause_after
            else:
                local_cursor += beat['duration_frames'] + pause_after
        duration_frames = max(2, local_cursor)
        board_copy = deepcopy(source_board)
        board_copy.update({'id': entry['instance_id'], 'duration_frames': duration_frames,
                           'dialogue': cues, 'shot_size': resolved['framing']})
        if reveal_spec:
            board_copy['reveal'] = reveal_spec
        if phase4:
            board_copy['characters'] = [character for character in source_board['characters']
                                        if character['character_id'] in set(visible)]
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
        if composition:
            source_motion = {**source_motion, 'scene_depth_layers': [layer for layer in scene_manifest['layers'] if layer['kind'] == 'render_layer']}
            camera_plan = _resolved_camera_plan(resolved['camera_intent'], composition, duration_frames, source_motion)
            composition['camera_safe_clamped'] = composition['safe_clamped']
            if composition['warnings']:
                composition['camera_safe_warning'] = composition['warnings'][0]
            motion_copy.update({'scene_instances': composition['scene_instances'],
                                'visible_objects': composition['visible_objects'],
                                'composition': composition})
        else:
            legacy_focus = ((.32 if focus_character is not None and visible.index(focus_character) == 0 and len(visible) > 1 else
                             .68 if focus_character is not None and len(visible) > 1 else .5) * canvas['width'], .46 * canvas['height'])
            camera_plan = _camera_plan(resolved['camera_intent'], legacy_focus, duration_frames,
                                       resolved['framing'], source_motion, canvas)
        if policy and camera_plan['type'] != 'static':
            camera_plan['to']['zoom'] = camera_plan['from']['zoom'] + (camera_plan['to']['zoom'] - camera_plan['from']['zoom']) * policy['camera']['strength']
            camera_plan['parallax_enabled'] = camera_plan['parallax_enabled'] and policy['parallax']['enabled']
            camera_plan['parallax_strengths'] = parallax_strengths
        motion_copy.update({'shot_id': entry['instance_id'], 'start_frame': absolute_cursor,
                            'duration_frames': duration_frames,
                            'camera': camera_plan,
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
            if policy:
                for event in performer['events']:
                    event['amplitude'] = event.get('amplitude', 1) * policy['performance']['event_strength']
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
    if policy:
        result['presentation'] = {'subtitle': deepcopy(policy['subtitle'])}
    return result


def validate_director_plan(plan, data, scene_manifest=None, character_asset_manifest=None):
    """Report compile-time semantic incompatibilities with stable, actionable errors."""
    errors = []
    try:
        compiled = compile_director_plan(plan, data, scene_manifest=scene_manifest,
                                         character_asset_manifest=character_asset_manifest)
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
