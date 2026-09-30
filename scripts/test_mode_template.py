"""Phase 5 policy execution, compatibility and Phase 1–4 integration regressions."""
from copy import deepcopy
import tempfile
import unittest
from pathlib import Path
from mode_system import resolve_mode,direct_with_mode,plan_metrics,validate_schema
from template_system import load_template,check_compatibility,instantiate_template,resolve_project_mode
from make_phase5_fixture import build
from pipeline import read,validate,NAMES,validate_camera_plan
from director import compile_director_plan
from production import render_payload


def content():
    return {'version':'0.1','project_id':'fixture','beats':[
        {'beat_id':'b1','speaker':'lin','text':'为什么冰放在桌上会变成水？','intent':'ask','emphasis':'normal'},
        {'beat_id':'b2','speaker':'bo','text':'因为它吸收了周围环境的热量。','intent':'explain','emphasis':'normal','reaction':'interested','reaction_target':'lin'},
        {'beat_id':'b3','speaker':'lin','text':'所以不是桌子把它弄湿了？','intent':'ask','emphasis':'normal'},
        {'beat_id':'b4','speaker':'bo','text':'……不是。','intent':'confirm','emphasis':'punchline','reaction':'speechless','reaction_target':'bo'}]}


class ModeTemplateTests(unittest.TestCase):
    def test_four_mode_manifests_parse(self):
        for m in ('dialogue-comedy','knowledge-explainer','motion-comic','story-animation'):
            resolved=resolve_mode(m);self.assertEqual(resolved['mode_id'],m)

    def test_both_templates_parse(self):
        for t in ('generic-room','generic-outdoor'):
            b=load_template(t);self.assertEqual(b['scene']['scene_id'],t)
            self.assertTrue(b['character_assets']['characters'][0]['parts']['head']['asset'])

    def plan(self,m,overrides=None):
        return direct_with_mode(content(),resolve_mode(m,overrides),['shot_001'],['lin','bo'])

    def test_relative_direction(self):
        c=plan_metrics(self.plan('dialogue-comedy'));e=plan_metrics(self.plan('knowledge-explainer'))
        for k in ('reaction_shots','punchline_hold_frames','camera_emphasis'):
            self.assertGreaterEqual(c[k],e[k])
        self.assertGreaterEqual(e['average_shot_frames'],c['average_shot_frames'])
        self.assertNotEqual(self.plan('dialogue-comedy')['shots'],self.plan('knowledge-explainer')['shots'])

    def test_same_content_preserved(self):
        original=[(b['speaker'],b['text']) for b in content()['beats']]
        for m in ('dialogue-comedy','knowledge-explainer','motion-comic','story-animation'):
            actual=[(b['speaker'],b['text']) for s in self.plan(m)['shots'] for b in s['beats'] if b['kind']=='dialogue']
            self.assertEqual(actual,original)

    def test_resolver_deterministic(self):
        self.assertEqual(self.plan('dialogue-comedy'),self.plan('dialogue-comedy'))

    def test_override_used_and_base_immutable(self):
        p=self.plan('dialogue-comedy',{'reaction':{'every_n_beats':0},'timing':{'emphasis_pause_after':40}})
        self.assertEqual(plan_metrics(p)['reaction_shots'],0)
        self.assertEqual(resolve_mode('dialogue-comedy')['policy']['reaction']['every_n_beats'],2)
        self.assertEqual(p['runtime_policy']['timing']['emphasis_pause_after'],40)

    def test_invalid_override_keys_and_ranges(self):
        for v in ([],{'assets':{}},{'camera':{'x':600}},{'camera':{'strength':-1}},{'timing':{'line_pause_frames':1.5}},{'subtitle':{'hold_frames':100}}):
            with self.assertRaises(ValueError):resolve_mode('dialogue-comedy',v)

    def test_unknown_ids_and_scene(self):
        for f,args in ((resolve_mode,('missing',)),(load_template,('missing',)),(load_template,('generic-room','missing')),(load_template,('../generic-room',))):
            with self.assertRaises(ValueError):f(*args)

    def test_illegal_camera_parallax_combination(self):
        with self.assertRaises(ValueError):resolve_mode('dialogue-comedy',{'parallax':{'enabled':False}})
        self.assertFalse(resolve_mode('motion-comic')['policy']['parallax']['enabled'])

    def profile(self):
        return {'version':'0.1','mode_id':'dialogue-comedy','template_id':'generic-room','scene_id':'generic-room'}

    def test_invalid_slot_binding(self):
        b=load_template('generic-room');b['scene']['character_instances'][0]['slot_id']='missing'
        with self.assertRaisesRegex(ValueError,'slot'):check_compatibility(self.profile(),content(),template=b)

    def test_missing_character(self):
        b=load_template('generic-room');b['character_assets']['characters']=b['character_assets']['characters'][1:]
        with self.assertRaisesRegex(ValueError,'Character'):check_compatibility(self.profile(),content(),template=b)

    def test_missing_prop(self):
        s=content();s['required_props']=['ice']
        with self.assertRaisesRegex(ValueError,'prop'):check_compatibility(self.profile(),s)

    def test_inadequate_scene_capabilities(self):
        b=load_template('generic-room');b['scene']['layers']=[l for l in b['scene']['layers'] if l['depth']=='background']
        with self.assertRaisesRegex(ValueError,'depth'):check_compatibility(self.profile(),content(),template=b)
        b=load_template('generic-room');b['capabilities']['characters'][0]['capabilities']['parts'].remove('mouth')
        with self.assertRaisesRegex(ValueError,'required parts'):check_compatibility(self.profile(),content(),template=b)

    def test_missing_visible_speaker(self):
        b=load_template('generic-room');b['scene']['character_instances'][0]['visible']=False
        with self.assertRaises(ValueError):check_compatibility(self.profile(),content(),template=b)

    def test_duplicate_content_id(self):
        s=content();s['beats'][1]['beat_id']='b1'
        with self.assertRaisesRegex(ValueError,'Duplicate'):direct_with_mode(s,resolve_mode('dialogue-comedy'),['shot_001'],['lin','bo'])

    def test_second_template_changes_space_not_only_image(self):
        a=load_template('generic-room')['scene'];b=load_template('generic-outdoor')['scene']
        self.assertNotEqual(a['character_slots'],b['character_slots'])
        self.assertNotEqual(a['composition_anchors'],b['composition_anchors'])
        self.assertNotEqual(a['objects'],b['objects'])

    def test_runtime_matrix_and_authoritative_rebuild(self):
        for mode,template in [('dialogue-comedy','generic-room'),('knowledge-explainer','generic-room'),('dialogue-comedy','generic-outdoor'),('motion-comic','generic-room'),('story-animation','generic-outdoor')]:
            with self.subTest(mode=mode,template=template),tempfile.TemporaryDirectory() as tmp:
                project=Path(tmp)/'matrix'
                build(project,mode,template)
                data,errors,_=validate(project,assets=True);self.assertEqual(errors,[])
                plan=resolve_project_mode(project,data)
                compiled=compile_director_plan(plan,data,project)
                # Semantic plans never contain manual world coordinates.
                self.assertTrue(all('camera' not in s for s in plan['shots']))
                errors=[]
                for shot in compiled['motion_plan']['shots']:
                    validate_camera_plan(shot,'0.4',errors,960,540)
                    self.assertIn('scene_instances',shot)
                    self.assertTrue(shot['character_performance'])
                self.assertEqual(errors,[])
                payload=render_payload(project,compiled,lambda root,name:root/name)
                self.assertEqual(payload['presentation']['subtitle'],resolve_mode(mode)['policy']['subtitle'])
                if mode=='motion-comic':
                    self.assertTrue(all(s['camera']['type']=='static' for s in payload['shots']))
                if mode=='knowledge-explainer':
                    events=[e for s in payload['shots'] for p in s['character_performance'] for e in p['events']]
                    self.assertTrue(any(e['preset']=='point' for e in events))
                # Stored plan can be stale: current profile/script remain authoritative.
                old=read(project/'production_profile.json');old['overrides']={'timing':{'emphasis_pause_after':60}}
                from pipeline import save
                save(project/'production_profile.json',old)
                rebuilt=resolve_project_mode(project,data)
                self.assertEqual(rebuilt['runtime_policy']['timing']['emphasis_pause_after'],60)

    def test_template_assets_are_self_contained(self):
        with tempfile.TemporaryDirectory() as tmp:
            project=Path(tmp)/'loaded';instantiate_template('generic-outdoor',project,'dialogue-comedy')
            scene=read(project/'scene_manifest.json')
            for item in [*scene['layers'],*scene['objects']]:
                if item.get('asset'):self.assertTrue((project/item['asset']).is_file())

    def test_camera_cadence_produces_static_holds(self):
        p=self.plan('dialogue-comedy')
        self.assertTrue(any(s['camera_intent']=='static' for s in p['shots']))
        self.assertTrue(any(s['camera_intent']!='static' for s in p['shots']))

    def test_modes_share_identical_loaded_art(self):
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            a=Path(tmp)/'a';b=Path(tmp)/'b'
            build(a,'dialogue-comedy');build(b,'knowledge-explainer')
            aa=read(a/'character_assets.json');bb=read(b/'character_assets.json')
            aa.pop('project_id');bb.pop('project_id');self.assertEqual(aa,bb)
            for path in a.rglob('*.png'):
                self.assertEqual(hashlib.sha256(path.read_bytes()).digest(),hashlib.sha256((b/path.relative_to(a)).read_bytes()).digest())

    def test_invalid_mode_does_not_create_partial_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'bad'
            with self.assertRaises(ValueError):instantiate_template('generic-room',p,'missing')
            self.assertFalse(p.exists())

    def test_pipeline_rejects_bad_profile_before_render(self):
        with tempfile.TemporaryDirectory() as tmp:
            project=Path(tmp)/'bad';build(project)
            from pipeline import save
            p=read(project/'production_profile.json');p['overrides']={'camera':{'strength':99}}
            save(project/'production_profile.json',p)
            _,errors,_=validate(project,assets=True)
            self.assertTrue(any('Mode/Template' in e for e in errors))


if __name__=='__main__':unittest.main()
