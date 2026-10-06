"""Measured mouth activity and renderable events for fixed-camera comic acting."""
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
    return errors
