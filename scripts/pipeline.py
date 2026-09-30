"""Local-only contract validation, prompt compiler and renderer preparation."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
from jsonschema import Draft202012Validator
from PIL import Image
from acting import asset_names, check_acting, check_character_performance
from production import inventory, check_dialogue, render_payload, check_direction
from director import validate_director_plan, compile_director_plan

ROOT = Path(__file__).resolve().parents[1]
NAMES = ('production_brief', 'characters', 'storyboard', 'motion_plan')
CAMERA_TYPES = {'static', 'push_in', 'pull_out', 'pan_left', 'pan_right', 'follow'}
CAMERA_EASINGS = {'linear', 'easeIn', 'easeOut', 'easeInOut'}
DEPTHS = {'foreground', 'character', 'midground', 'background', 'sky'}
DEFAULT_PARALLAX_STRENGTHS = {
    'foreground': 1.2, 'character': 1.0, 'midground': 0.55,
    'background': 0.2, 'sky': 0.05,
}

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def local(root, name):
    p = (root/name).resolve()
    if not p.is_relative_to(root.resolve()):
        raise ValueError('Asset escapes project: '+name)
    return p

def validate_camera_plan(motion_shot, version, errors, width, height):
    """Validate executable Camera/Parallax fields introduced in motion_plan 0.4."""
    if version != '0.4':
        if 'camera' in motion_shot or any('depth' in layer for layer in motion_shot['layers']):
            errors.append('Camera and depth fields require motion_plan 0.4 '+motion_shot['shot_id'])
        return
    sid = motion_shot['shot_id']
    layers = motion_shot['layers']
    for layer in layers:
        if layer.get('depth') not in DEPTHS:
            errors.append('motion_plan 0.4 layer needs a valid depth '+sid+'/'+layer['layer_id'])
        if any(layer[key] != {'x': 0, 'y': 0, 'scale': 1} for key in ('from', 'to')):
            errors.append('motion_plan 0.4 camera owns scene framing; layer from/to must be identity '+sid+'/'+layer['layer_id'])

    camera = motion_shot.get('camera') or {'type': 'static', 'parallax_enabled': False}
    camera_type = camera.get('type')
    if camera_type not in CAMERA_TYPES:
        errors.append('Invalid camera type '+sid)
        return
    moving = camera_type != 'static'
    from_pose, to_pose = camera.get('from'), camera.get('to')
    focus = camera.get('focus_target')
    if camera.get('easing', 'easeInOut') not in CAMERA_EASINGS:
        errors.append('Invalid camera easing '+sid)
    screen = camera.get('screen_target', {'x': 0.5, 'y': 0.5})
    def finite_number(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    if any(not finite_number(screen.get(axis)) or not 0 <= screen[axis] <= 1 for axis in ('x', 'y')):
        errors.append('Camera screen_target must use normalized x/y '+sid)
    if camera_type == 'static' and from_pose and to_pose and from_pose != to_pose:
        errors.append('static camera from/to poses must match '+sid)

    if moving:
        if not focus or any(not finite_number(focus.get(axis)) for axis in ('x', 'y')):
            errors.append('Moving camera needs a finite focus_target x/y '+sid)
        if not from_pose or not to_pose:
            errors.append('Moving camera needs from and to camera poses '+sid)
        else:
            for pose in (from_pose, to_pose):
                if any(not finite_number(pose.get(axis)) for axis in ('x', 'y', 'zoom')) or not finite_number(pose.get('zoom')) or pose['zoom'] <= 0:
                    errors.append('Camera poses need finite x/y and positive zoom '+sid)
            if camera_type == 'push_in' and to_pose.get('zoom', 0) <= from_pose.get('zoom', 0):
                errors.append('push_in must increase zoom '+sid)
            if camera_type == 'pull_out' and to_pose.get('zoom', 0) >= from_pose.get('zoom', 0):
                errors.append('pull_out must decrease zoom '+sid)
            if camera_type == 'pan_left' and to_pose.get('x', 0) >= from_pose.get('x', 0):
                errors.append('pan_left must move camera x left '+sid)
            if camera_type == 'pan_right' and to_pose.get('x', 0) <= from_pose.get('x', 0):
                errors.append('pan_right must move camera x right '+sid)

    if camera_type == 'follow':
        path = camera.get('follow_path', [])
        duration = motion_shot['duration_frames']
        frames = [point.get('frame') for point in path]
        if len(path) < 2 or frames[0] != 0 or frames[-1] != duration - 1 or frames != sorted(set(frames)):
            errors.append('follow_path must be strictly ordered and cover local frames 0..duration-1 '+sid)
        if any(not finite_number(point.get(axis)) for point in path for axis in ('x', 'y')):
            errors.append('follow_path points need finite x/y '+sid)
        if from_pose and to_pose and len(path) >= 2:
            if (from_pose.get('x'), from_pose.get('y')) != (path[0].get('x'), path[0].get('y')) or (to_pose.get('x'), to_pose.get('y')) != (path[-1].get('x'), path[-1].get('y')):
                errors.append('follow_path endpoints must match camera from/to positions '+sid)
    elif camera.get('follow_path'):
        errors.append('follow_path is only valid for follow camera '+sid)

    depth_names = {layer.get('depth') for layer in layers if layer.get('depth') in DEPTHS}
    parallax_enabled = camera.get('parallax_enabled') is True
    if moving and len(depth_names) > 1 and not parallax_enabled:
        errors.append('Moving camera with multiple depth layers requires parallax '+sid)
    if parallax_enabled:
        strengths = camera.get('parallax_strengths', {})
        values = [strengths.get(depth, DEFAULT_PARALLAX_STRENGTHS[depth]) for depth in depth_names]
        if len(depth_names) < 2 or len(set(values)) < 2:
            errors.append('Parallax needs at least two depth layers with distinct strengths '+sid)

    # Background assets fill the project canvas. Verify endpoint transforms still
    # cover that viewport so camera motion cannot expose empty canvas edges.
    background_depth = 'background' if 'background' in depth_names else ('sky' if 'sky' in depth_names else None)
    if moving and background_depth and from_pose and to_pose and focus:
        strength = camera.get('parallax_strengths', {}).get(background_depth, DEFAULT_PARALLAX_STRENGTHS[background_depth]) if parallax_enabled else 1.0
        anchors = (screen['x'] * width, screen['y'] * height)
        poses = [from_pose, to_pose]
        if camera_type == 'follow' and camera.get('follow_path'):
            last_frame = max(1, motion_shot['duration_frames'] - 1)
            poses = [
                {
                    'x': point['x'], 'y': point['y'],
                    'zoom': from_pose['zoom'] + (to_pose['zoom'] - from_pose['zoom']) * point['frame'] / last_frame,
                }
                for point in camera['follow_path']
            ]
        for pose in poses:
            zoom = 1 + (pose['zoom'] - 1) * strength
            camera_x = focus['x'] + (pose['x'] - focus['x']) * strength
            camera_y = focus['y'] + (pose['y'] - focus['y']) * strength
            translate_x = anchors[0] - camera_x * zoom
            translate_y = anchors[1] - camera_y * zoom
            if (translate_x > 1 or translate_y > 1
                    or translate_x + width * zoom < width - 1
                    or translate_y + height * zoom < height - 1):
                errors.append('Camera/Parallax may reveal a background canvas edge '+sid)

def validate(project, assets=False, shot_id=None):
    data = {n:read(project/(n+'.json')) for n in NAMES}
    errors, warnings = [], []
    director_path = project/'director_plan.json'
    director_plan = read(director_path) if director_path.is_file() else None
    for n, d in data.items():
        schema = read(ROOT/'schemas'/(n+'.schema.json'))
        Draft202012Validator.check_schema(schema)
        for e in Draft202012Validator(schema).iter_errors(d):
            errors.append(f'{n}:{list(e.path)}: {e.message}')
    if director_plan is not None:
        schema = read(ROOT/'schemas/director_plan.schema.json')
        Draft202012Validator.check_schema(schema)
        for e in Draft202012Validator(schema).iter_errors(director_plan):
            errors.append(f'director_plan:{list(e.path)}: {e.message}')
    if errors:
        return data, errors, warnings
    if director_plan is not None:
        errors.extend(validate_director_plan(director_plan, data))
        if not errors:
            directed = compile_director_plan(director_plan, data, project)
            directed_chars = directed['characters']['characters']
            directed_format = directed['production_brief']['format']
            for motion_shot in directed['motion_plan']['shots']:
                board_shot = next(item for item in directed['storyboard']['shots'] if item['id'] == motion_shot['shot_id'])
                errors.extend(check_character_performance(motion_shot, board_shot, directed_chars, directed['motion_plan']['version']))
                validate_camera_plan(motion_shot, directed['motion_plan']['version'], errors,
                                     directed_format['width'], directed_format['height'])
            errors.extend(check_dialogue(project, directed, local, assets, shot_id))
    brief, chars, board, motion = (data[n] for n in NAMES)
    if len({d['project_id'] for d in data.values()}) != 1:
        errors.append('project_id mismatch')
    def unique(items, key, label):
        ids=[s[key] for s in items]
        if len(ids)!=len(set(ids)): errors.append('Duplicate '+label)
        return set(ids)
    cids=unique(chars['characters'],'id','character id')
    bids=unique(board['beats'],'id','beat id')
    sids=unique(board['shots'],'id','shot id')
    mids=unique(motion['shots'],'shot_id','motion shot id')
    if shot_id and shot_id not in sids: errors.append('Unknown selected shot '+shot_id)
    if sids!=mids: errors.append('Storyboard/motion shot set mismatch')
    if [s['id'] for s in board['shots']]!=[s['shot_id'] for s in motion['shots']]: errors.append('Storyboard/motion order mismatch')
    for b in board['beats']:
        if b['source_excerpt'] not in brief['original_content']: errors.append('Beat source is not an original-content excerpt: '+b['id'])
    if bids!={s['beat_id'] for s in board['shots']}: errors.append('Uncovered or unknown narrative beat')
    previous={}; previous_shots=[]
    for shot in board['shots']:
        sid=shot['id']
        if shot['beat_id'] not in bids: errors.append('Unknown beat '+sid)
        layerids=unique(shot['layers'],'id',sid+' layer id')
        present=unique(shot['characters'],'character_id',sid+' performance')
        if not present<=cids: errors.append('Unknown character '+sid)
        if sum(l['role'] in ('background','panel_base') for l in shot['layers'])!=1: errors.append('Need exactly one completed background or static panel base '+sid)
        layerchars={l.get('character_id') for l in shot['layers'] if l['role']=='character' and l.get('character_id')}
        # A deliberate group cutout may contain several named characters. Infer its
        # membership from the declared elements text when no single character_id exists.
        for layer in shot['layers']:
            if layer['role']=='character' and not layer.get('character_id'):
                for character in chars['characters']:
                    if character['name'] in layer.get('elements',''):
                        layerchars.add(character['id'])
        if layerchars!=present: errors.append('Character layer/performance mismatch '+sid)
        for char in shot['characters']:
            cid=char['character_id']; old=previous.get(cid)
            if old and old['pose_tag']==char['pose_tag']:
                warnings.append({'shot':sid,'check':'pose','message':'Same pose as previous appearance','exception':shot['repetition_exception']})
            previous[cid]=char
        previous_shots.append(shot)
        if len(previous_shots)>=3:
            for key in ('shot_size','angle','composition_tag'):
                if len({s[key] for s in previous_shots[-3:]})==1:
                    warnings.append({'shot':sid,'check':key,'message':'Three consecutive identical tags','exception':shot['repetition_exception']})
    direction_errors,direction_warnings=check_direction(data)
    errors.extend(direction_errors); warnings.extend(direction_warnings)
    cursor=0; hashes={}; backgrounds={}
    for item in motion['shots']:
        sid=item['shot_id']; shot=next((s for s in board['shots'] if s['id']==sid),None)
        if item['start_frame']!=cursor: errors.append('Timeline gap/overlap '+sid)
        cursor+=item['duration_frames']
        if not shot: continue
        if item['duration_frames']!=shot['duration_frames']: errors.append('Duration mismatch '+sid)
        sequential=(item.get('performance') or {}).get('mode')=='sequential-comic'
        if motion['version'] in ('0.3','0.4') and (item.get('performance') or {}).get('mode') not in ('sequential-comic','fixed-camera-micro'):
            errors.append('motion_plan '+motion['version']+' requires a fixed comic performance mode '+sid)
        if sequential and ('dialogue' not in shot or shot.get('transition')!='cut'):
            errors.append('Sequential comic requires dialogue (empty for silent shots) and cut transition '+sid)
        caption_end=0
        for cue in shot.get('dialogue',[]):
            if cue['start_frame']<caption_end or not cue['start_frame']<cue['end_frame']<=shot['duration_frames']:
                errors.append('Invalid dialogue timing '+sid)
            caption_end=cue['end_frame']
        lids=unique(item['layers'],'layer_id',sid+' motion layer')
        if lids!={l['id'] for l in shot['layers']}: errors.append('Layer set mismatch '+sid)
        unique(item['layers'],'z',sid+' z order')
        roles={l['id']:l['role'] for l in shot['layers']}
        selected=not shot_id or sid==shot_id
        if motion['version'] in ('0.2','0.3','0.4'):
            errors.extend(check_acting(item,motion['asset_mode']=='production',assets and selected,roles))
        elif assets and motion['asset_mode']=='production':
            errors.append('Legacy 0.1 is parallax-only; migrate motion_plan to 0.2 for production '+sid)
        bgz=[l['z'] for l in item['layers'] if roles.get(l['layer_id']) in ('background','panel_base')]
        if bgz and bgz[0]!=min(l['z'] for l in item['layers']): errors.append('Background must be bottom layer '+sid)
        if assets and selected and motion['asset_mode']=='production' and not all(item['review'][k] for k in ('master_alignment','background_completed','motion_bounds_checked')): errors.append('Production visual review incomplete '+sid)
        width,height=brief['format']['width'],brief['format']['height']
        for layer in item['layers']:
            if roles.get(layer['layer_id'])=='panel_base' and (layer['asset']!=shot['master'] or layer.get('region') or layer.get('acting')):
                errors.append('Panel base must be the unchanged original master '+sid)
            if 'region' in layer:
                x,y,w,h=layer['region']
                if w<=0 or h<=0 or x+w>1 or y+h>1: errors.append('Invalid local patch region '+sid)
            if any(r=='panel_base' for r in roles.values()):
                a=layer.get('acting',{})
                if a and (not layer.get('region') or any(k['x'] or k['y'] or k['rotation'] or k['opacity']!=1 for k in a['keys'])):
                    errors.append('Panel patch requires fixed local replacement region '+sid)
            for t in (layer['from'],layer['to']):
                if abs(t['x'])>(t['scale']-1)*width/2+1e-6 or abs(t['y'])>(t['scale']-1)*height/2+1e-6: errors.append('Motion can reveal canvas edge '+sid+'/'+layer['layer_id'])
        if item.get('character_performance'):
            errors.extend(check_character_performance(item,shot,chars['characters'],motion['version']))
            for performer in item['character_performance']:
                root_keys=performer.get('root_keys',[])
                frames=[key['frame'] for key in root_keys]
                if root_keys and (frames[0]!=0 or frames!=sorted(set(frames)) or frames[-1]>=item['duration_frames']):
                    errors.append('Invalid character root transform frames '+sid+'/'+performer['character_id'])
        if assets and selected:
            for name,role in [(shot['master'],'master')]+[(name,roles.get(l['layer_id'])) for l in item['layers'] for name in asset_names(l)]:
                p=local(project,name)
                if not p.is_file(): errors.append('Missing asset '+name); continue
                try:
                    with Image.open(p) as im:
                        if im.size!=(width,height): errors.append('Canvas size mismatch '+name)
                        alpha=im.convert('RGBA').getchannel('A').getextrema()
                        if role in ('background','panel_base','master') and alpha!=(255,255): errors.append('Opaque image required '+name)
                        patch=any(l.get('region') and name in asset_names(l) for l in item['layers'])
                        if role in ('character','foreground','effects') and not patch and (alpha[0]==255 or alpha[1]==0): errors.append('Nonempty transparent layer required '+name)
                except Exception as e: errors.append('Invalid image '+name+': '+str(e))
                if role=='character':
                    digest=hashlib.sha256(p.read_bytes()).hexdigest()
                    if digest in hashes and hashes[digest]!=(sid,name): errors.append('Reused character cutout: '+name+' and '+hashes[digest][1])
                    hashes[digest]=(sid,name)
                if role=='background' and motion['version']=='0.3':
                    digest=hashlib.sha256(p.read_bytes()).hexdigest()
                    if digest in backgrounds: errors.append('Mechanically reused background asset: '+sid+' and '+backgrounds[digest])
                    backgrounds[digest]=sid
        validate_camera_plan(item,motion['version'],errors,width,height)
    if cursor!=brief['format']['duration_frames']: errors.append('Total duration mismatch')
    if brief['format']['width']%2 or brief['format']['height']%2: errors.append('H264 dimensions must be even')
    if assets and motion['asset_mode']=='production':
        for char in chars['characters']:
            if shot_id and char['id'] not in {c['character_id'] for s in board['shots'] if s['id']==shot_id for c in s['characters']}: continue
            if char['reference']['status']!='ready' or not local(project,char['reference']['image']).is_file(): errors.append('Character reference not ready: '+char['id'])
    if sids==mids:
        errors.extend(check_dialogue(project,data,local,assets,shot_id))
    if director_plan is not None and shot_id:
        errors.append('--shot cannot select a source panel from an authoritative director_plan timeline')
    return data,errors,warnings

def compile_prompts(project,data,shot_id=None):
    brief,chars,board=(data[n] for n in NAMES[:3]); lookup={c['id']:c for c in chars['characters']}
    paper_style = brief.get('style_preset') == 'paper-collage'
    simple_comic_style = brief.get('style_preset') == 'simple-comic'
    economy_profile = brief.get('render_profile', 'comic-economy') == 'comic-economy'
    economy_addition = ('Economy comic production: clear readable line art, simplified background shapes, limited texture, '
                        'compact visual detail, expressive faces and hands, strong silhouette readability, and efficient '
                        'repeatable assets. Prioritize identity and acting over cinematic background detail. '
                        'Do not imitate any named living or copyrighted comic artist or copy distinctive characters.') if economy_profile else ''
    style_addition = ('Layered paper collage illustration, tactile cut-paper edges, subtle paper fibers and print grain, '
                      'controlled registration offsets, soft contact shadows between layers, limited palette derived from '
                      'the production brief, handmade but precise silhouettes, clear readable faces and objects. Treat every '
                      'layer as a physical paper cutout; preserve a clean master composition before separation.') if paper_style else ''
    simple_comic_addition = ('Simple 2D humorous comic illustration: bold clean black ink outlines, flat color blocks, '
                             'limited shading, highly readable facial expressions, clear hand gestures, compact comic timing, '
                             'simple background shapes with two to four location-defining objects, and a clean lower subtitle-safe area. '
                             'Use the reference only for high-level visual language; do not reproduce any named comic, character, panel, dialogue or layout.') if simple_comic_style else ''
    style_addition = ' '.join(part for part in (economy_addition, simple_comic_addition, style_addition) if part)
    style_avoid = (['No glossy 3D plastic','no photorealistic surface','no random torn edges over faces or text',
                    'no independent lighting per layer','no unrelated scrapbook stickers','no theme or culture substitution']
                   if paper_style else [])
    if simple_comic_style:
        style_avoid.extend(['No speech bubbles, comic lettering or generated text','no copied named-comic style or characters',
                            'no busy background detail behind faces or subtitle area','no gradients that reduce subtitle contrast'])
    for char in chars['characters']:
        if shot_id: continue
        save(project/'prompts'/('reference_'+char['id']+'.json'),{
            'prompt_version':'0.1','project_id':brief['project_id'],'prompt_role':'character_reference',
            'task':'character_reference','identity':char['identity'],'prompt':char['reference']['prompt'],
            'output':char['reference']['image'],'lock':'identity_only','reference_images':[],
            'do_not_copy_from_reference':['pose','expression','shot_size','camera','composition'],
            'model':None,'seed':None,'size':{'width':brief['format']['width'],'height':brief['format']['height']},
            'visual_language':brief['visual_language'],'style_preset':brief.get('style_preset','custom'),
            'style_addition':style_addition,'setting':brief['setting'],
            'negative_constraints':['no baked-in dialogue, captions, speech bubbles, logos or watermark','no identity drift','no extra fingers','no unrelated standing pose']
        })
    panels=[]
    for s in board['shots']:
        d=s.get('direction',{}); fps=brief['format']['fps']
        acting='；'.join(f"{c['character_id']}：{c['action']}" for c in s['characters']) or '无人；按场景叙事'
        expression='；'.join(f"{c['character_id']}：{c['expression']}，看向{c['gaze']}" for c in s['characters']) or '无'
        dialogue='；'.join(f"{c['speaker']}：{c['text']}" for c in s.get('dialogue',[])) or '无对白'
        timing='；'.join(f"{c['speaker']}：{c['start_frame']/fps:.3f}—{c['end_frame']/fps:.3f}秒（结束不含）" for c in s.get('dialogue',[])) or '无字幕'
        listening='；'.join(f"{r['character_id']}倾听反应：{r['response']}" for r in d.get('listening_reactions',[]))
        rows=[('镜头编号',s['id']),('来源漫画格',s.get('source_panel','未指定')),('持续时间',f"{s['duration_frames']/fps:.3f}秒 / {s['duration_frames']}帧"),('景别',s['shot_size']),('机位/构图',d.get('camera_position',s['angle'])+'；'+s['composition']),('场景背景',s['setting']+'；'+d.get('background_view','旧版未记录背景视图')),('出场人物','、'.join(c['character_id'] for c in s['characters']) or '无人'),('当前说话者','、'.join(c['speaker'] for c in s.get('dialogue',[])) or '无'),('人物动作',acting+('；'+listening if listening else '')),('人物表情/视线',expression),('台词',dialogue),('字幕出现时机',timing),('微动态',d.get('micro_actions','旧版未记录')),('音效','、'.join(s.get('sound_effects',[])) or '无'),('切镜原因',d.get('cut_reason',s['purpose'])),('下一镜头衔接',str(d.get('next_shot_id') or '结束')+'；'+d.get('handoff',s['continuity']))]
        panels.append('\n\n'.join(f'{label}：{value}' for label,value in rows)+'\n')
    (project/'storyboard_review.md').write_text('\n'.join(panels),encoding='utf-8')
    for shot in board['shots']:
        if shot_id and shot['id']!=shot_id: continue
        plan=next(s for s in data['motion_plan']['shots'] if s['shot_id']==shot['id'])
        space=next((s for s in board.get('scenes',[]) if s['id']==shot.get('direction',{}).get('scene_id')),None)
        index=board['shots'].index(shot)
        neighbors=[{'id':b['id'],'direction':b.get('direction'),'characters':b['characters']} for j,b in enumerate(board['shots']) if abs(j-index)==1]
        shot={**shot,'scene_space':space,'adjacent_shot_context':neighbors,
            'director_rules':'Keep location geometry, lighting, time and major objects consistent while independently composing each panel from its motivated camera position. Do not reuse the same background image or zoom/crop a previous panel. Preserve character identity and accessories. Default every body part to a stable hold. Trigger one primary action only from speech, information, pause, emotion or explicit action; structure it as prepare → action → settle/hold, then return to stable state. Never use perpetual sin/cos breathing, bobbing, swaying, scaling or repeated blinking; do not animate all parts together. Design both speaking and listening reactions causally; follow incoming/outgoing state, gaze, cut reason and handoff. Hold briefly for a motivated reaction after dialogue. Comic exaggeration only at emotional peaks. '+('Use the explicit 0.4 camera plan and depth layers for scene framing; keep individual artwork on shared world coordinates.' if data['motion_plan']['version']=='0.4' and (plan.get('camera') or {}).get('type','static')!='static' else 'The camera remains fixed inside each panel.')}
        save(project/'prompts'/(shot['id']+'_acting.json'),{
            'prompt_version':'0.1','project_id':brief['project_id'],'shot_id':shot['id'],'prompt_role':'acting_layers',
            'task':'prepare_aligned_acting_assets','master':shot['master'],
            'reference_images':[{'path':lookup[c['character_id']]['reference']['image'],'use':'identity_only'} for c in shot['characters']],
            'do_not_copy_from_reference':['pose','expression','shot_size','camera','composition'],
            'model':None,'seed':None,
            'performers':shot['characters'],'performance':plan.get('performance'),
            'layers':plan['layers'],
            'dialogue':shot.get('dialogue',[]),
            'scene_space':space,
            'direction':shot.get('direction'),
            'sequential_comic_constraints':('One panel expresses one line, action or reaction. Fixed camera and composition. Animate character mouths, eyes, expressions, head, hands or simple limbs; use a new hard-cut panel for complex actions and new angles. Comic exaggeration, symbols and text effects are allowed for punchlines. Preserve character identity across panels. Subtitles follow supplied dialogue intervals. No camera motion or whole-image stretch as acting.' if (plan.get('performance') or {}).get('mode')=='sequential-comic' else None),
            'micro_performance_constraints':({'primary':'Exactly one complete blink per original comic shot; small mouth opening only during timed speech; extremely slight head turn; almost imperceptible chest/shoulder breathing; minimal hair movement. Preserve original pose and expression design.','secondary':'Remain still except optional occasional blinking. No secondary head, breathing or sway tracks.','stability':'No camera movement, whole-image stretch, large limb action, position changes, facial drift, deformed hands/feet or twisted bodies. Preserve original 2D linework.','review':'Visually count one primary blink and verify secondary stillness and anatomical stability; these are not automatically pixel-validated.'} if (plan.get('performance') or {}).get('mode')=='fixed-camera-micro' else None),
            'instructions':('Preserve the original master composition and pose. Fixed camera: no zoom, pan, rotation, scale or parallax. Animate only subtle local blinking, speech-timed mouth shapes, breathing and small head/hair/clothing motion. Keep background, identity and linework stable; no stretching or deformation. Mouth motion requires supplied dialogue timings and aligned local assets; automatic lip sync is not implemented.' if (plan.get('performance') or {}).get('mode')=='fixed-camera-micro' else 'Design anticipation, action, reaction and hold. Generate fresh pose drawings or separate joints from this shot master; fill exposed areas. Keep identity and contact points consistent. Never substitute a lineup crop or camera zoom for acting.')})
        save(project/'prompts'/(shot['id']+'.json'),{
            'prompt_version':'0.1','project_id':brief['project_id'],'shot_id':shot['id'],'prompt_role':'master',
            'task':'fresh_master_composition','output':shot['master'],'canvas':brief['format'],
            'model':None,'seed':None,
            'reference_images':[{'path':lookup[c['character_id']]['reference']['image'],'use':'identity_only'} for c in shot['characters']],
            'do_not_copy_from_reference':['pose','expression','shot_size','camera','composition'],
            'original_content':brief['original_content'],'preserve':brief['content_preservation'],
            'setting':brief['setting'],'visual_language':brief['visual_language'],'style_preset':brief.get('style_preset','custom'),
            'style_addition':style_addition,'beat':next(b for b in board['beats'] if b['id']==shot['beat_id']),
            'shot':shot,'identity_references':[{'image':lookup[c['character_id']]['reference']['image'],'identity':lookup[c['character_id']]['identity'],'reference_scope':'identity_only: face/hair/clothes/proportions/distinctive_features; do not copy pose, expression, shot_size, camera or composition'} for c in shot['characters']],
            'negative_constraints':['Do not change cultural setting or topic','Do not paste or recycle a reference standing pose','No baked-in dialogue, captions or speech bubbles','No extra characters, fingers or broken contact points','No camera zoom, pan, rotation, parallax or whole-image stretch']+style_avoid,
            'layer_instruction':'Generate and review the complete master FIRST. Extract/reconstruct aligned layers from this exact master; fill all occluded background. Never independently invent unrelated layers.'
        })

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['validate','compile','prepare','report'])
    parser.add_argument('project',type=Path)
    parser.add_argument('--renderer',type=Path)
    parser.add_argument('--assets',action='store_true')
    parser.add_argument('--shot',help='Compile or prepare only this shot; preparation rebases its timeline to zero')
    args=parser.parse_args(); project=args.project.resolve()
    data,errors,warnings=validate(project,args.assets or args.command=='prepare',args.shot)
    save(project/'qc_report.json',{'errors':errors,'repetition_warnings':warnings,'visual_review_required':True})
    if errors:
        print('\n'.join(errors)); return 1
    save(project/'asset_report.json',inventory(project,data,local))
    if args.command=='compile': compile_prompts(project,data,args.shot)
    if args.command=='prepare':
        if not args.renderer: parser.error('--renderer is required for prepare')
        renderer=args.renderer.resolve()
        if renderer==project or renderer.is_relative_to(project): parser.error('Renderer must be outside the source project')
        shutil.copytree(ROOT/'assets/remotion',renderer,dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('node_modules','out','.env*'))
        for shot in data['motion_plan']['shots']:
            if args.shot and shot['shot_id']!=args.shot: continue
            for layer in shot['layers']:
                for name in asset_names(layer):
                    dest=local(renderer/'public',name); dest.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copy2(local(project,name),dest)
        director_path = project/'director_plan.json'
        render_source = compile_director_plan(read(director_path), data, project) if director_path.is_file() else data
        render_data=render_payload(project,render_source,local,args.shot)
        for shot in render_data['shots']:
            for cue in shot['dialogue']:
                if cue.get('audio'):
                    dest=local(renderer/'public',cue['audio']); dest.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copy2(local(project,cue['audio']),dest)
        save(renderer/'src/render-data.json',render_data)
    print(f'PASS: {args.command}; {len(warnings)} repetition warning(s). See qc_report.json; semantic/visual QC remains human or agent reviewed.')
    return 0

if __name__=='__main__':
    try: sys.exit(main())
    except (ValueError,OSError) as e: print(str(e),file=sys.stderr); sys.exit(1)
