"""Local WAV timing, speech activity and content-addressed shot reports."""
import hashlib
import json
import math
import struct
import wave
from pathlib import Path
from acting import asset_names

def wav_timing(path, fps):
    with wave.open(str(path),'rb') as w:
        rate,channels,width,count=w.getframerate(),w.getnchannels(),w.getsampwidth(),w.getnframes()
        if width!=2 or w.getcomptype()!='NONE':
            raise ValueError('Dialogue requires uncompressed 16-bit PCM WAV: '+str(path))
        raw=w.readframes(count)
    samples=struct.unpack('<'+'h'*(len(raw)//2),raw)
    frames=math.ceil(count/rate*fps)
    rms=[]
    for f in range(frames):
        chunk=samples[int(f*rate/fps)*channels:int((f+1)*rate/fps)*channels]
        rms.append(math.sqrt(sum(v*v for v in chunk)/max(1,len(chunk))))
    threshold=max(180,max(rms,default=0)*.09)
    # Coarse amplitude-gated open/close, deliberately not phoneme lip sync.
    speaking=[i for i,v in enumerate(rms) if v>threshold and int(i/(fps*.10))%2==0]
    return frames,speaking

def files_for_shot(data, shot):
    board=next(b for b in data['storyboard']['shots'] if b['id']==shot['shot_id'])
    refs=[c['reference']['image'] for c in data['characters']['characters'] if c['id'] in {p['character_id'] for p in board['characters']}]
    return list(dict.fromkeys([board['master']]+refs+[p for l in shot['layers'] for p in asset_names(l)]+[c['audio'] for c in board.get('dialogue',[]) if c.get('audio')]))

def inventory(project,data,resolve):
    previous={}
    old=project/'asset_report.json'
    if old.is_file():
        previous={s['shot_id']:s['fingerprint'] for s in json.loads(old.read_text(encoding='utf-8')).get('shots',[])}
    result=[]
    for s in data['motion_plan']['shots']:
        sid=s['shot_id']; board=next(b for b in data['storyboard']['shots'] if b['id']==sid)
        files=[]
        for name in files_for_shot(data,s):
            p=resolve(project,name)
            files.append({'path':name,'exists':p.is_file(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None})
        identities=[c for c in data['characters']['characters'] if c['id'] in {p['character_id'] for p in board['characters']}]
        scene=next((v for v in data['storyboard'].get('scenes',[]) if v['id']==board.get('direction',{}).get('scene_id')),None)
        signature={'shot':s,'board':board,'scene':scene,'brief':data['production_brief'],'characters':identities,'files':files}
        fingerprint=hashlib.sha256(json.dumps(signature,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        result.append({'shot_id':sid,'fingerprint':fingerprint,'changed':previous.get(sid)!=fingerprint,'missing':[f['path'] for f in files if not f['exists']],'files':files})
    return {'shots':result,'missing_count':sum(len(s['missing']) for s in result),'visual_acceptance':'pending: files and timing checks do not establish visual quality'}

def check_dialogue(project,data,resolve,assets=False,shot_id=None):
    errors=[]; fps=data['production_brief']['format']['fps']
    v3=data['motion_plan']['version'] in ('0.3','0.4')
    for shot in data['storyboard']['shots']:
        if shot_id and shot['id']!=shot_id: continue
        plan=next(s for s in data['motion_plan']['shots'] if s['shot_id']==shot['id'])
        present={c['character_id'] for c in shot['characters']}
        speakers={c['speaker'] for c in shot.get('dialogue',[])}
        for layer in plan['layers']:
            speech=layer.get('acting',{}).get('speech')
            if speech and (speech['speaker'] not in present or speech['speaker'] not in speakers):
                errors.append('Speech driver has no visible speaking character '+shot['id'])
        for cue in shot.get('dialogue',[]):
            if v3 and assets and data['motion_plan']['asset_mode']=='production' and (not cue.get('audio') or cue.get('timing_source')!='audio'):
                errors.append('Production dialogue needs measured local audio '+shot['id'])
            if not assets or not cue.get('audio'): continue
            try:
                frames,_=wav_timing(resolve(project,cue['audio']),fps)
                if abs(frames-(cue['end_frame']-cue['start_frame']))>1:
                    errors.append('Audio/dialogue duration mismatch '+shot['id'])
            except (OSError,ValueError,wave.Error) as e:
                errors.append('Invalid dialogue audio '+shot['id']+': '+str(e))
    return errors

def render_payload(project,data,resolve,shot_id=None):
    shots=[]; fps=data['production_brief']['format']['fps']
    version=data['motion_plan']['version']
    for s in data['motion_plan']['shots']:
        if shot_id and s['shot_id']!=shot_id: continue
        board=next(b for b in data['storyboard']['shots'] if b['id']==s['shot_id'])
        storyboard_layers={layer['id']:layer for layer in board['layers']}
        cues=[]
        for c in board.get('dialogue',[]):
            cue=dict(c)
            cue['mouth_open_frames']=wav_timing(resolve(project,c['audio']),fps)[1] if c.get('audio') else []
            cues.append(cue)
        motion_layers=[]
        for layer in s['layers']:
            runtime_layer=dict(layer)
            if version != '0.4' and not runtime_layer.get('depth'):
                role=storyboard_layers.get(layer['layer_id'],{}).get('role')
                runtime_layer['depth']={
                    'background':'background', 'panel_base':'background',
                    'character':'character', 'foreground':'foreground',
                    'effects':'midground',
                }.get(role,'character')
            motion_layers.append(runtime_layer)
        runtime_shot={**s,'layers':motion_layers,'start_frame':0 if shot_id else s['start_frame'],'dialogue':cues}
        if version != '0.4':
            runtime_shot.pop('camera',None)
        shots.append(runtime_shot)
    fmt=dict(data['production_brief']['format'])
    if shot_id: fmt['duration_frames']=shots[0]['duration_frames']
    return {'format':fmt,**data['motion_plan'],'shots':shots}

def check_direction(data):
    if data['motion_plan']['version'] not in ('0.3','0.4'): return [],[]
    errors=[]; warnings=[]; board=data['storyboard']; scenes=board.get('scenes',[])
    scene_ids={s['id'] for s in scenes}
    if not scenes or len(scene_ids)!=len(scenes): errors.append('motion_plan 0.3 requires unique scene space records')
    for i,shot in enumerate(board['shots']):
        sid=shot['id']; d=shot.get('direction')
        if not d:
            errors.append('Missing independent shot direction '+sid); continue
        if not shot.get('source_panel'):
            errors.append('motion_plan 0.3 shot must identify source comic panel '+sid)
        if d['scene_id'] not in scene_ids: errors.append('Unknown scene '+sid)
        next_id=board['shots'][i+1]['id'] if i+1<len(board['shots']) else None
        if d['next_shot_id']!=next_id: errors.append('Next shot continuity link mismatch '+sid)
        visible={c['character_id'] for c in shot['characters']}
        speakers={c['speaker'] for c in shot.get('dialogue',[])}
        reactions=[r['character_id'] for r in d['listening_reactions']]
        if len(reactions)!=len(set(reactions)) or not set(reactions)<=visible:
            errors.append('Invalid listening reaction characters '+sid)
        if shot.get('dialogue') and not (visible-speakers)<=set(reactions):
            errors.append('Missing visible listener reaction '+sid)
        if shot.get('dialogue'):
            expected=shot['duration_frames']-shot['dialogue'][-1]['end_frame']
            if d['reaction_hold_frames']!=expected: errors.append('Reaction hold does not match dialogue end '+sid)
        elif d['reaction_hold_frames']>shot['duration_frames']:
            errors.append('Reaction hold exceeds shot duration '+sid)
        if i:
            prev=board['shots'][i-1].get('direction',{})
            if (prev.get('scene_id'),prev.get('view_id'))==(d['scene_id'],d['view_id']):
                warnings.append({'shot':sid,'check':'background_view','message':'Adjacent shots repeat the same background view; visually verify a motivated new composition','exception':shot.get('repetition_exception','')})
    return errors,warnings
