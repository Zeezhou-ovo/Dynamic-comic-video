"""Finite animation validation; transforms alone cannot prove convincing acting."""
def asset_names(layer):
    a=layer.get('acting',{}); speech=a.get('speech',{})
    return list(dict.fromkeys([layer['asset']]+[p['asset'] for p in a.get('poses',[])]+[speech[k] for k in ('closed_asset','open_asset') if k in speech]+list(speech.get('shape_assets',{}).values())+list(layer.get('state_assets',{}).values())))

def check_acting(shot, production, assets, roles):
    timeline=shot.get('timeline') or {}
    # Event-driven expression swaps and prop motion are real acting, not camera moves.
    errors=[]; active=any(e.get('pose_asset') for e in timeline.get('expression_events',[])) or any(l.get('prop_motion') for l in shot['layers'])
    sid=shot['shot_id']; perf=shot.get('performance')
    if not perf: errors.append('Missing performance plan '+sid)
    micro=(perf or {}).get('mode')=='fixed-camera-micro'
    fixed=micro or (perf or {}).get('mode')=='sequential-comic'
    for layer in shot['layers']:
        if fixed and any(layer[t]!={'x':0,'y':0,'scale':1} for t in ('from','to')):
            errors.append('Fixed-camera mode requires identity layer framing '+sid+'/'+layer['layer_id'])
        a=layer.get('acting')
        if not a: continue
        keys=a['keys']; poses=a.get('poses',[])
        for group in (keys,poses):
            if not group: continue
            frames=[k['frame'] for k in group]
            if frames[0]!=0 or frames!=sorted(set(frames)) or frames[-1]>=shot['duration_frames']:
                errors.append('Invalid acting frames '+sid+'/'+layer['layer_id'])
        changing=len({(k['x'],k['y'],k['rotation'],k['opacity'],k.get('scale',1)) for k in keys})>1
        pose_change=len({p['asset'] for p in poses})>1
        speech=a.get('speech')
        events=a.get('events',[])
        if events:
            previous_end=-1; signatures=[]
            for event in events:
                start,peak,settle,end=(event[k] for k in ('start_frame','peak_frame','settle_frame','end_frame'))
                if not (start<=peak<=settle<=end<shot['duration_frames']):
                    errors.append('Invalid event phases; require prepare/action/settle within shot '+sid+'/'+layer['layer_id'])
                if start<previous_end:
                    errors.append('Overlapping acting events on one layer '+sid+'/'+layer['layer_id'])
                previous_end=end
                signatures.append((event['trigger'],event['description']))
            if len(signatures)!=len(set(signatures)):
                errors.append('Repeated identical acting event; actions must be event-triggered '+sid+'/'+layer['layer_id'])
        # A layer with no event remains a stable hold by default. Keys may hold that state;
        # they must not be used as an always-on sine/cosine-style loop.
        if len(keys)>=6:
            values=[(k['x'],k['y'],k['rotation'],k['opacity'],k.get('scale',1)) for k in keys]
            alternating=all(values[i]==values[i-2] for i in range(2,len(values)))
            returning=(values[0]==values[-1] and values[1]==values[-2] and values[2]==values[-3])
            if (alternating or returning) and len(set(values))>1:
                errors.append('Periodic acting loop is not allowed; return to a stable hold '+sid+'/'+layer['layer_id'])
        if speech:
            if poses: errors.append('Speech and explicit poses cannot share one mouth track '+sid)
            if a['part']!='mouth' or speech['closed_asset']==speech['open_asset']:
                errors.append('Speech requires mouth part and distinct assets '+sid)
            else: active=True
        if fixed:
            if roles.get(layer['layer_id']) in ('background','panel_base') and (speech or pose_change or any(k['x'] or k['y'] or k['rotation'] or k['opacity']!=1 or k.get('scale',1)!=1 for k in keys)):
                errors.append('Fixed-camera background must remain unchanged '+sid)
            if micro and any(abs(k['rotation'])>2 for k in keys):
                errors.append('Micro acting rotation exceeds 2 degrees '+sid+'/'+layer['layer_id'])
        # Whole-cutout movement is still camera-like; local joints or new drawings count.
        if roles.get(layer['layer_id'])!='background' and (pose_change or (a['part']!='whole' and changing)):
            active=True
    if not active and not shot.get('character_performance') and not (perf or {}).get('static_reason'):
        errors.append('Camera-only shot requires acting or justified static hold '+sid)
    if production and assets and not (perf or {}).get('reviewed'):
        errors.append('Performance visual review incomplete '+sid)
    return errors


PRESET_PARTS = {
    'idle': ('body',), 'talk': ('body', 'mouth'), 'nod': ('head',),
    'shake_head': ('head',), 'blink': ('eyes',), 'small_bounce': ('body',),
}


def check_character_performance(motion_shot, board_shot, characters, plan_version='0.4'):
    """Validate requested character events against declared parts and mapped assets."""
    errors = []
    performers = motion_shot.get('character_performance', [])
    if performers and plan_version != '0.4':
        errors.append('character_performance requires motion_plan 0.4 '+motion_shot['shot_id'])
    seen = set()
    visible = {item['character_id'] for item in board_shot['characters']}
    board_layers = {layer['id']: layer for layer in board_shot['layers']}
    plan_layers = motion_shot['layers']
    char_by_id = {item['id']: item for item in characters}

    for performer in performers:
        sid = motion_shot['shot_id']
        cid = performer['character_id']
        if cid in seen:
            errors.append('Duplicate character_performance '+sid+'/'+cid)
        seen.add(cid)
        if cid not in visible:
            errors.append('Character performance target is not visible '+sid+'/'+cid)
        character = char_by_id.get(cid)
        capability = (character or {}).get('capabilities')
        if not capability:
            errors.append('Character capability manifest is required '+sid+'/'+cid)
            continue
        declared_parts = set(capability['parts'])
        declared_poses = set(capability['poses'])
        declared_expressions = set(capability['expressions'])
        layers_by_part = {}
        for layer in plan_layers:
            board_layer = board_layers.get(layer['layer_id'], {})
            if board_layer.get('character_id') != cid:
                continue
            part = layer.get('acting', {}).get('part')
            if part:
                layers_by_part.setdefault(part, []).append(layer)

        def has_part(part):
            aliases = {'arm': ('arm', 'left_arm', 'right_arm'), 'left_arm': ('left_arm', 'arm'), 'right_arm': ('right_arm', 'arm')}
            accepted = aliases.get(part, (part,))
            return any(name in declared_parts and name in layers_by_part for name in accepted)

        for part in ('body', 'head', 'eyes', 'mouth', 'left_arm', 'right_arm', 'hair'):
            if part in declared_parts and part not in layers_by_part and not (part in ('left_arm', 'right_arm') and 'arm' in layers_by_part):
                errors.append('Manifest declares missing rendered part '+sid+'/'+cid+'/'+part)

        if performer['role'] in ('idle', 'listener') and not has_part('body'):
            errors.append('idle/listener role requires a rendered body part '+sid+'/'+cid)
        if performer['role'] == 'speaker' and not (has_part('body') and has_part('mouth')):
            errors.append('speaker role requires rendered body and mouth parts '+sid+'/'+cid)

        if performer.get('pose') and performer['pose'] not in declared_poses:
            errors.append('Requested pose is absent from capability manifest '+sid+'/'+cid+'/'+performer['pose'])
        if performer.get('expression') and performer['expression'] not in declared_expressions:
            errors.append('Requested expression is absent from capability manifest '+sid+'/'+cid+'/'+performer['expression'])
        for state_kind, state_name in (('pose', performer.get('pose')), ('expression', performer.get('expression'))):
            if not state_name:
                continue
            state_key = f'{state_kind}:{state_name}'
            if not any(state_key in layer.get('state_assets', {}) for layers in layers_by_part.values() for layer in layers):
                errors.append('Requested '+state_kind+' has no mapped state asset '+sid+'/'+cid+'/'+state_key)

        event_ids = set()
        for event in performer['events']:
            if event['event_id'] in event_ids:
                errors.append('Duplicate character event id '+sid+'/'+cid+'/'+event['event_id'])
            event_ids.add(event['event_id'])
            if not (0 <= event['start_frame'] <= event['peak_frame'] <= event['settle_frame'] <= event['end_frame'] < motion_shot['duration_frames']):
                errors.append('Invalid character event phases '+sid+'/'+cid+'/'+event['event_id'])
            preset = event['preset']
            required = PRESET_PARTS.get(preset, ())
            if preset in ('point', 'raise_hand'):
                target = event.get('part')
                if target and target not in ('right_arm', 'left_arm', 'arm'):
                    errors.append(preset+' preset part must be an arm '+sid+'/'+cid+'/'+target)
                elif target and not has_part(target):
                    errors.append(preset+' preset requires a rendered arm part '+sid+'/'+cid+'/'+target)
                elif not target and not any(has_part(part) for part in ('right_arm', 'left_arm', 'arm')):
                    errors.append(preset+' preset requires a rendered arm part '+sid+'/'+cid)
            else:
                for part in required:
                    if not has_part(part):
                        errors.append(preset+' preset requires a rendered '+part+' part '+sid+'/'+cid)
            if preset == 'blink' and not any('blink' in layer.get('state_assets', {}) for layer in layers_by_part.get('eyes', [])):
                errors.append('blink preset requires an eyes layer with a blink state asset '+sid+'/'+cid)
            if preset == 'talk':
                mouth_layers = layers_by_part.get('mouth', [])
                has_speech_assets = any(layer.get('acting', {}).get('speech') or {'open', 'closed'} <= set(layer.get('state_assets', {})) for layer in mouth_layers)
                if not has_speech_assets:
                    errors.append('talk preset requires mapped open/closed mouth assets '+sid+'/'+cid)

    return errors
