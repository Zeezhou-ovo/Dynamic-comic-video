import json
import tempfile
import unittest
from pathlib import Path
from make_dialogue_fixture import build_dialogue
from retime_project import convert, retime

class RetimeTests(unittest.TestCase):
    def test_only_frame_fields_change(self):
        source={'frame':12,'duration_frames':48,'x':240,'fps':24,'volume':.5,'speaker':'cat'}
        self.assertEqual(retime(source,1.25),{**source,'frame':15,'duration_frames':60})
    def test_source_preserved_and_cut_starts_contiguous(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=build_dialogue(root/'source');before=(source/'motion_plan.json').read_bytes()
            convert(source,root/'result',30)
            self.assertEqual((source/'motion_plan.json').read_bytes(),before)
            motion=json.loads((root/'result/motion_plan.json').read_text());start=0
            for shot in motion['shots']:
                self.assertEqual(shot['start_frame'],start);self.assertFalse(shot['performance']['reviewed']);start+=shot['duration_frames']
            self.assertEqual(start,json.loads((root/'result/production_brief.json').read_text())['format']['duration_frames'])
            with self.assertRaises(FileExistsError):convert(source,root/'result',30)
    def test_director_timeline_rejected_before_copy(self):
        with tempfile.TemporaryDirectory() as temp:
            source=build_dialogue(Path(temp)/'source');destination=Path(temp)/'result'
            (source/'director_plan.json').write_text('{}')
            with self.assertRaises(ValueError):convert(source,destination,30)
            self.assertFalse(destination.exists())
    def test_destination_cannot_be_inside_source(self):
        with tempfile.TemporaryDirectory() as temp:
            source=build_dialogue(Path(temp)/'source')
            with self.assertRaises(ValueError):convert(source,source/'nested',30)

if __name__=='__main__':unittest.main()
