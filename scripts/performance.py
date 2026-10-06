"""Measured mouth activity and renderable events for fixed-camera comic acting.

Ported from the local performance upgrade (three/four-level mouths, expression
pose swaps, sound files, drawn comic effects) and extended with rigid prop
motion, layers attached to a prop, and a whole-video audio bed.
"""
import json
import math
import struct
import wave


def wav_shapes(path, fps):
    """Return energy-based shapes. Round vowels require explicit authored cues."""
    with wave.open(str(path), 'rb') as stream:
        rate, channels, width, count = (stream.getframerate(), stream.getnchannels(),
                                        stream.getsampwidth(), stream.getnframes())
        if width != 2 or stream.getcomptype() != 'NONE':
            raise ValueError('Dialogue requires uncompressed 16-bit PCM WAV: ' + str(path))
        samples = struct.unpack('<' + 'h' * (count * channels), stream.readframes(count))
    rms = []
    for frame in range(math.ceil(count / rate * fps)):
        chunk = samples[int(frame * rate / fps) * channels:int((frame + 1) * rate / fps) * channels]
        rms.append(math.sqrt(sum(value * value for value in chunk) / max(1, len(chunk))))
    peak = max(rms, default=0)
    silence = max(180, peak * .09)
    shapes = ['closed' if value <= silence else
              'small' if value < peak * .40 else
              'open' if value < peak * .78 else 'wide' for value in rms]
    return shapes


def event_assets(shot):
    timeline = shot.get('timeline') or {}
    return list(dict.fromkeys(
        [event['asset'] for event in timeline.get('sound_events', []) if event.get('asset')] +
        [event['asset'] for event in timeline.get('visual_events', []) if event.get('asset')] +
        [event['pose_asset'] for event in timeline.get('expression_events', []) if event.get('pose_asset')]))


def _pcm_wav_frames(path, fps):
    with wave.open(str(path), 'rb') as stream:
        if stream.getsampwidth() != 2 or stream.getcomptype() != 'NONE':
            raise ValueError('requires 16-bit PCM WAV')
        return stream.getnframes() / stream.getframerate() * fps


def check_extractions(shot, resolve, project):
    """Layers made by extract_layer.py must be approved and unchanged since approval."""
    from extract_layer import manifest_for_asset, stale_outputs
    errors = []
    seen = set()
    for layer in shot['layers']:
        manifest_path = manifest_for_asset(resolve(project, '.'), layer['asset'])
        if manifest_path is None or manifest_path in seen:
            continue
        seen.add(manifest_path)
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        name = manifest_path.name
        if not manifest.get('reviewed'):
            errors.append('Extracted layer review sheet not approved ' + shot['shot_id'] + '/' + name)
        stale = stale_outputs(resolve(project, '.'), manifest)
        if stale:
            errors.append('Extracted layer changed after extraction/approval ' + shot['shot_id'] + '/' + name + ': ' + ', '.join(map(str, stale)))
    return errors


def check_props(shot, roles, resolve=None, project=None, assets=False):
    """Prop motion must move a separated transparent cut-out above a full-frame plate."""
    errors = []
    sid = shot['shot_id']
    layers = {layer['layer_id']: layer for layer in shot['layers']}
    for layer in shot['layers']:
        lid = layer['layer_id']
        motion = layer.get('prop_motion')
        if motion:
            if roles.get(lid) in ('background', 'panel_base') or layer.get('region'):
                errors.append('Prop motion needs a separated cut-out layer, not a background or region patch ' + sid + '/' + lid)
            if layer.get('acting', {}).get('speech'):
                errors.append('Prop motion layer cannot carry speech; attach a mouth layer instead ' + sid + '/' + lid)
            plates = [other for other in shot['layers'] if other['z'] < layer['z'] and not other.get('region') and not other.get('prop_motion')]
            if not plates:
                errors.append('Prop motion needs a full-frame plate layer below it ' + sid + '/' + lid)
            previous = -1
            for event in sorted(motion['events'], key=lambda item: item['start_frame']):
                if not 0 <= event['start_frame'] < event['end_frame'] <= shot['duration_frames']:
                    errors.append('Prop motion event outside shot ' + sid + '/' + event['event_id'])
                if event['start_frame'] < previous:
                    errors.append('Overlapping prop motion events ' + sid + '/' + lid)
                previous = event['end_frame']
                if event['kind'] == 'rock' and not (event.get('period_frames') and event.get('decay_frames')):
                    errors.append('Rock needs period_frames and decay_frames so it settles instead of looping ' + sid + '/' + event['event_id'])
            if assets and project is not None:
                from PIL import Image
                try:
                    with Image.open(resolve(project, layer['asset'])) as image:
                        alpha = image.convert('RGBA').getchannel('A').getextrema()
                    if alpha[0] == 255:
                        errors.append('Prop motion layer must be a transparent cut-out ' + sid + '/' + lid)
                except (OSError, ValueError) as error:
                    errors.append('Invalid prop layer ' + sid + '/' + lid + ': ' + str(error))
        target = layer.get('attach_to')
        if target:
            parent = layers.get(target)
            if parent is None or not parent.get('prop_motion') or target == lid:
                errors.append('attach_to must name a prop_motion layer in the same shot ' + sid + '/' + lid)
            elif layer.get('prop_motion'):
                errors.append('Attached layer cannot have its own prop motion ' + sid + '/' + lid)
            elif layer['z'] <= parent['z']:
                errors.append('Attached layer must sit above its prop ' + sid + '/' + lid)
    return errors


def check_audio_bed(project, data, resolve, assets=False):
    bed = data['motion_plan'].get('audio_bed')
    if not bed or not assets:
        return []
    try:
        _pcm_wav_frames(resolve(project, bed['asset']), data['production_brief']['format']['fps'])
    except (OSError, ValueError, wave.Error) as error:
        return ['Invalid audio_bed: ' + str(error)]
    return []


def check_performance(project, data, resolve, assets=False, shot_id=None):
    """Reject unsafe paths, silent fallback claims and events that cannot render."""
    errors = []
    fps = data['production_brief']['format']['fps']
    fmt = data['production_brief']['format']
    production = data['motion_plan']['asset_mode'] == 'production'
    for shot in data['motion_plan']['shots']:
        sid = shot['shot_id']
        if shot_id and sid != shot_id:
            continue
        board = next(item for item in data['storyboard']['shots'] if item['id'] == sid)
        timeline = shot.get('timeline') or {}
        layers = {layer['layer_id']: layer for layer in shot['layers']}
        roles = {layer['id']: layer['role'] for layer in board['layers']}
        errors.extend(check_props(shot, roles, resolve, project, assets))
        if assets and production:
            errors.extend(check_extractions(shot, resolve, project))
        cues = board.get('dialogue', [])
        previous = {}
        for event in timeline.get('mouth_events', []):
            start, end, speaker = event['start_frame'], event['end_frame'], event['speaker']
            cue = next((cue for cue in cues if cue['speaker'] == speaker and
                        cue['start_frame'] <= start < end <= cue['end_frame']), None)
            if cue is None or start < previous.get(speaker, 0):
                errors.append('Mouth event overlaps or leaves speaker dialogue ' + sid)
            previous[speaker] = end
            speech = [layer.get('acting', {}).get('speech', {}) for layer in layers.values()]
            if event['shape'] not in ('closed', 'open') and not any(
                    track.get('speaker') == speaker and event['shape'] in track.get('shape_assets', {})
                    for track in speech):
                errors.append('Mouth shape has no matching asset ' + sid + '/' + event['shape'])
        for cue in timeline.get('subtitle_events', []):
            if not 0 <= cue['start_frame'] < cue['end_frame'] <= shot['duration_frames']:
                errors.append('Subtitle event outside shot ' + sid)
        for event in timeline.get('visual_events', []):
            if not 0 <= event['start_frame'] < event['end_frame'] <= shot['duration_frames']:
                errors.append('Visual event outside shot ' + sid)
            if event['effect_type'] == 'background_simplify':
                if not event.get('asset') or 'background' not in roles.values():
                    errors.append('Background simplify needs a replacement asset and separated background ' + sid)
        expression_end = {}
        for event in timeline.get('expression_events', []):
            if not event.get('pose_asset'):
                continue  # Legacy descriptive event; actual poses remain on acting tracks.
            lid = event.get('layer_id')
            layer = layers.get(lid)
            if layer is None or roles.get(lid) in ('background', 'panel_base') or layer.get('acting', {}).get('speech'):
                errors.append('Expression pose requires a non-mouth character part layer ' + sid)
            if not 0 <= event['start_frame'] < event['end_frame'] <= shot['duration_frames'] or event['start_frame'] < expression_end.get(lid, 0):
                errors.append('Expression pose outside shot or overlaps on layer ' + sid)
            expression_end[lid] = event['end_frame']
            if assets and layer:
                from PIL import Image
                try:
                    with Image.open(resolve(project, event['pose_asset'])) as image:
                        alpha = image.convert('RGBA').getchannel('A').getextrema()
                        if image.size != (fmt['width'], fmt['height']):
                            errors.append('Expression pose canvas mismatch ' + sid)
                        if not layer.get('region') and (alpha[0] == 255 or alpha[1] == 0):
                            errors.append('Expression pose requires nonempty transparent layer ' + sid)
                except (OSError, ValueError) as error:
                    errors.append('Invalid expression pose ' + sid + ': ' + str(error))
        for event in timeline.get('sound_events', []):
            start, end = event['start_frame'], event['end_frame']
            if not 0 <= start < end <= shot['duration_frames']:
                errors.append('Sound event outside shot ' + sid)
            if not event.get('asset'):
                if production and assets:
                    errors.append('Production sound event needs local WAV asset ' + sid)
                continue
            if assets:
                try:
                    with wave.open(str(resolve(project, event['asset'])), 'rb') as stream:
                        available = stream.getnframes() / stream.getframerate() * fps
                        if stream.getsampwidth() != 2 or stream.getcomptype() != 'NONE':
                            errors.append('Sound event requires 16-bit PCM WAV ' + sid)
                        if event.get('source_start_frame', 0) + end - start > math.ceil(available) + 1:
                            errors.append('Sound event exceeds source WAV duration ' + sid)
                except (OSError, ValueError, wave.Error) as error:
                    errors.append('Invalid sound event audio ' + sid + ': ' + str(error))
        if assets:
            for event in timeline.get('visual_events', []):
                if event.get('asset'):
                    from PIL import Image
                    try:
                        with Image.open(resolve(project, event['asset'])) as image:
                            if image.size != (fmt['width'], fmt['height']) or image.convert('RGBA').getchannel('A').getextrema() != (255, 255):
                                errors.append('Background replacement must be full-canvas opaque image ' + sid)
                    except (OSError, ValueError) as error:
                        errors.append('Invalid background replacement ' + sid + ': ' + str(error))
    if not shot_id:
        errors.extend(check_audio_bed(project, data, resolve, assets))
    return errors
