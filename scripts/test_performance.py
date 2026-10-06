"""Behavioral coverage for sound timing, shape assets, expression and silence."""
import math
import struct
import tempfile
import unittest
import wave
from pathlib import Path
from make_dialogue_fixture import build_dialogue
from pipeline import read,save,validate,local
from production import inventory,render_payload
from performance import wav_shapes


class PerformanceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=build_dialogue(Path(self.temp.name)/'project')
        (self.root/'audio').mkdir(exist_ok=True)
        samples=[]
        for i in range(24000):
            amplitude=0 if i<6000 else 1200 if i<12000 else 4000 if i<18000 else 8000
            samples.append(int(amplitude*math.sin(i*.1)))
        with wave.open(str(self.root/'audio/test.wav'),'wb') as stream:
            stream.setparams((1,2,24000,0,'NONE','not compressed'))
            stream.writeframes(struct.pack('<'+'h'*len(samples),*samples))
        self.board=read(self.root/'storyboard.json')
        self.motion=read(self.root/'motion_plan.json')
        self.motion['version']='0.3'
        for shot in self.board['shots']:
            shot['dialogue']=[{'speaker':'lin','text':'test','start_frame':6,'end_frame':30,'audio':'audio/test.wav','timing_source':'audio'}]
            shot['direction']['reaction_hold_frames']=18
        for shot in self.motion['shots']:
            shot.setdefault('timeline', {'scene_id':'office', 'duration_frames':48,'subtitle_events':[], 'speech_intervals':[], 'action_events':[], 'expression_events':[], 'blink_events':[], 'sound_events':[], 'cut_at_frame':48})
        self.flush()

    def tearDown(self): self.temp.cleanup()

    def flush(self):
        save(self.root/'storyboard.json',self.board)
        save(self.root/'motion_plan.json',self.motion)

    def event(self,asset='audio/test.wav',start=6,end=30):
        return {'event_id':'sound','trigger':'information','start_frame':start,'peak_frame':start,
                'settle_frame':start,'end_frame':end,'description':'reaction sound','asset':asset,'volume':.2}

    def test_audio_shapes_close_on_silence_and_follow_energy(self):
        shapes=wav_shapes(self.root/'audio/test.wav',24)
        self.assertEqual(shapes[:6],['closed']*6)
        self.assertEqual(set(shapes[6:12]),{'small'})
        self.assertEqual(set(shapes[12:18]),{'open'})
        self.assertEqual(set(shapes[18:24]),{'wide'})

    def test_sound_asset_is_fingerprinted_and_missing_rejected(self):
        self.motion['shots'][0]['timeline']['sound_events']=[self.event()];self.flush()
        data,errors,_=validate(self.root,True);self.assertEqual(errors,[])
        report=inventory(self.root,data,local)
        self.assertIn('audio/test.wav',[item['path'] for item in report['shots'][0]['files']])
        self.motion['shots'][0]['timeline']['sound_events'][0]['asset']='audio/missing.wav';self.flush()
        self.assertTrue(any('Invalid sound event audio' in e for e in validate(self.root,True)[1]))

    def test_sound_cannot_outlast_source_or_cross_cut(self):
        self.motion['shots'][0]['timeline']['sound_events']=[self.event(end=40)];self.flush()
        self.assertTrue(any('exceeds source WAV' in e for e in validate(self.root,True)[1]))
        self.motion['shots'][0]['timeline']['sound_events'][0]['end_frame']=49;self.flush()
        self.assertTrue(any('Sound event outside shot' in e for e in validate(self.root)[1]))

    def test_authored_shape_needs_asset_and_stays_inside_dialogue(self):
        timeline=self.motion['shots'][0]['timeline']
        timeline['mouth_events']=[{'speaker':'lin','shape':'round','start_frame':9,'end_frame':12,'source':'authored'}];self.flush()
        self.assertTrue(any('no matching asset' in e for e in validate(self.root)[1]))
        timeline['mouth_events'][0].update(shape='open',end_frame=35);self.flush()
        self.assertTrue(any('leaves speaker dialogue' in e for e in validate(self.root)[1]))

    def test_expression_requires_real_target_layer(self):
        self.motion['shots'][0]['timeline']['expression_events']=[{**self.event(), 'layer_id':'missing','pose_asset':'shots/shot_001/layers/blink.png'}]
        self.motion['shots'][0]['timeline']['expression_events'][0].pop('asset')
        self.motion['shots'][0]['timeline']['expression_events'][0].pop('volume');self.flush()
        self.assertTrue(any('non-mouth character part' in e for e in validate(self.root)[1]))

    def test_payload_preserves_cue_energy_and_layer_roles(self):
        data,errors,_=validate(self.root,True);self.assertEqual(errors,[])
        payload=render_payload(self.root,data,local,'shot_002')
        self.assertEqual(payload['shots'][0]['dialogue'][0]['mouth_shape_frames'][:6],['closed']*6)
        self.assertEqual(payload['shots'][0]['layers'][0]['role'],'background')

if __name__=='__main__': unittest.main()
