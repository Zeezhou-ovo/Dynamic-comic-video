"""Manifest-driven Template loading and Mode/Template compatibility, without directing."""
from copy import deepcopy
from pathlib import Path
import shutil
from manifest_validation import ROOT, read_json, validate_schema, registry_path
from mode_system import resolve_mode


def repository_asset(path):
    resolved = (ROOT / path).resolve()
    if not resolved.is_relative_to(ROOT.resolve()) or not resolved.is_file():
        raise ValueError('Missing or illegal Template reference ' + path)
    return resolved


def load_template(template_id, scene_id=None):
    manifest = read_json(registry_path('templates', template_id, 'template.json'))
    validate_schema('template_manifest', manifest)
    if manifest['template_id'] != template_id:
        raise ValueError('Template registry ID mismatch')
    if manifest['default_scene'] not in manifest['scenes']:
        raise ValueError('Template default_scene is not declared')
    scene_id = scene_id or manifest['default_scene']
    if scene_id not in manifest['scenes']:
        raise ValueError('Unknown Template scene ' + scene_id)
    entry = manifest['scenes'][scene_id]
    scene = read_json(repository_asset(entry['scene_manifest']))
    assets = read_json(repository_asset(entry['character_assets']))
    capabilities = read_json(repository_asset(entry['character_capabilities']))
    validate_schema('scene_manifest', scene)
    validate_schema('character_assets', assets)
    validate_schema('characters', capabilities)
    if scene['scene_id'] != scene_id:
        raise ValueError('Template scene ID mismatch')
    base = (ROOT / manifest['base_project']).resolve()
    if not base.is_relative_to(ROOT.resolve()) or not base.is_dir():
        raise ValueError('Missing/illegal Template base_project')
    ids = {c['character_id'] for c in assets['characters']}
    caps = {c['id'] for c in capabilities['characters']}
    for cid, slot in entry['default_bindings'].items():
        if cid not in ids or cid not in caps:
            raise ValueError('Missing default Character ' + cid)
        if slot not in scene['character_slots']:
            raise ValueError('Invalid Template slot ' + slot)
    declared_props = {o['id'] for o in scene['objects']}
    if not set(entry['available_props']) <= declared_props:
        raise ValueError('Template available_props refers to missing scene objects')
    scene['character_instances'] = [{'character_id':c,'slot_id':s,'visible':True} for c,s in entry['default_bindings'].items()]
    from composition_resolver import validate_scene_manifests
    def local_asset(folder, name):
        asset = (folder/name).resolve()
        if not asset.is_relative_to(folder.resolve()):
            raise ValueError('Template asset escapes base_project: '+name)
        return asset
    errors = validate_scene_manifests(scene, assets, capabilities['characters'], base, local_asset, scene['reference_size'])
    if errors:
        raise ValueError('Template assets: '+'; '.join(errors))
    return {'manifest': manifest, 'entry': entry, 'base': base, 'scene': scene,
            'character_assets': assets, 'capabilities': capabilities}


def check_compatibility(profile, script, template=None, scene=None, assets=None, capabilities=None):
    validate_schema('production_profile', profile)
    validate_schema('dialogue_script', script)
    mode = resolve_mode(profile['mode_id'], profile.get('overrides'))
    bundle = template or load_template(profile['template_id'], profile['scene_id'])
    scene = scene or bundle['scene']
    assets = assets or bundle['character_assets']
    capabilities = capabilities or bundle['capabilities']
    if scene['scene_id'] != profile['scene_id']:
        raise ValueError('Profile scene_id does not match loaded Scene')
    ids = {c['character_id'] for c in assets['characters']}
    caps = {c['id']: c.get('capabilities', {}) for c in capabilities['characters']}
    visible = [c['character_id'] for c in scene['character_instances'] if c['visible']]
    if len(set(visible)) != len(visible):
        raise ValueError('Duplicate Character binding')
    for instance in scene['character_instances']:
        if instance['slot_id'] not in scene['character_slots']:
            raise ValueError('Invalid Character slot ' + instance['slot_id'])
        if instance['character_id'] not in ids or instance['character_id'] not in caps:
            raise ValueError('Missing bound Character ' + instance['character_id'])
    req = mode['requirements']
    if len(visible) < req['min_characters']:
        raise ValueError('Mode requires more visible characters')
    depths = {l['depth'] for l in scene['layers'] if l['kind']=='render_layer' and l['visible']}
    if len(depths) < req['min_depth_layers']:
        raise ValueError('Scene lacks Mode required depth layers')
    for cid in visible:
        missing = set(req['required_parts']) - set(caps[cid].get('parts', []))
        if missing:
            raise ValueError('Character '+cid+' lacks Mode required parts '+str(sorted(missing)))
        if mode['policy']['performance']['explain_gesture'] and not {'arm','left_arm','right_arm'} & set(caps[cid].get('parts', [])):
            raise ValueError('Mode explain gesture requires Character arm ' + cid)
    if not set(script.get('required_props', [])) <= {o['id'] for o in scene['objects']}:
        raise ValueError('Missing content required prop')
    for beat in script['beats']:
        if beat['speaker'] not in visible or (beat.get('reaction_target') and beat['reaction_target'] not in visible):
            raise ValueError('Content references missing/non-visible Character')
    return mode


def instantiate_template(template_id, project, mode_id, scene_id=None, overrides=None):
    """Load a selected scene and its assets into a new self-contained project."""
    bundle = load_template(template_id, scene_id)
    project = Path(project).resolve()
    if project.exists():
        raise FileExistsError('Use a new project directory: ' + str(project))
    profile={'version':'0.1','mode_id':mode_id,'template_id':template_id,'scene_id':bundle['scene']['scene_id'],'overrides':{} if overrides is None else overrides}
    validate_schema('production_profile',profile);resolve_mode(mode_id,overrides)
    shutil.copytree(bundle['base'], project)
    from pipeline import save
    for name in ('production_brief','characters','storyboard','motion_plan'):
        value = read_json(project / (name+'.json'));value['project_id']=project.name
        save(project/(name+'.json'),value)
    for name, value in (('scene_manifest',bundle['scene']),('character_assets',bundle['character_assets']),('characters',bundle['capabilities'])):
        value = deepcopy(value);value['project_id']=project.name;save(project/(name+'.json'),value)
    # Scene-specific resources are relative to a shared test-art bundle. Loader
    # resolves all references; callers never enumerate image paths.
    refs = [l['asset'] for l in bundle['scene']['layers'] if l.get('asset')]
    refs += [o['asset'] for o in bundle['scene']['objects']]
    refs += [a for c in bundle['character_assets']['characters'] for p in c['parts'].values() for a in [p['asset'],*p['state_assets'].values()]]
    for ref in dict.fromkeys(refs):
        source=(bundle['base']/ref).resolve();dest=(project/ref).resolve()
        if not source.is_relative_to(bundle['base']) or not source.is_file() or not dest.is_relative_to(project):
            raise ValueError('Missing/illegal Template asset '+ref)
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
    save(project/'production_profile.json',profile)
    return project


def resolve_project_mode(project, data):
    """Called by pipeline validate/prepare, authoritatively regenerating intent."""
    project=Path(project)
    profile=read_json(project/'production_profile.json')
    script=read_json(project/'dialogue_script.json')
    if script['project_id'] != data['storyboard']['project_id']:
        raise ValueError('Dialogue Script project_id mismatch')
    bundle=load_template(profile['template_id'],profile['scene_id'])
    mode=check_compatibility(profile,script,template=bundle,scene=data.get('scene_manifest'),assets=data.get('character_assets'),capabilities=data['characters'])
    if not data.get('scene_manifest') or not data.get('character_assets'):
        raise ValueError('Mode/Template project requires loaded Scene and Character Asset Manifests')
    from mode_system import direct_with_mode
    visible=[c['character_id'] for c in data['scene_manifest']['character_instances'] if c['visible']]
    plan=direct_with_mode(script,mode,[s['id'] for s in data['storyboard']['shots']],visible)
    for shot in plan['shots']:
        if shot['shot_intent'] in ('establishing_wide','two_shot','group_shot'):
            shot['visible_objects'] = list(bundle['entry']['available_props'])
    return plan
