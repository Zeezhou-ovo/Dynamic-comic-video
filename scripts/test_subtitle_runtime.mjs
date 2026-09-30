import test from 'node:test';
import assert from 'node:assert/strict';
import { selectSubtitleCue } from '../assets/remotion/src/runtime/subtitle-controller.mjs';
const cues=[{text:'first',start_frame:0,end_frame:10},{text:'second',start_frame:12,end_frame:20}];
test('mode subtitle hold never shadows the next active dialogue',()=>{
  assert.equal(selectSubtitleCue(cues,11,5).text,'first');
  assert.equal(selectSubtitleCue(cues,12,5).text,'second');
  assert.equal(selectSubtitleCue(cues,20,5).text,'second');
  assert.equal(selectSubtitleCue(cues,25,5),null);
});
test('legacy zero hold retains half-open dialogue bounds and random-access output',()=>{
  assert.equal(selectSubtitleCue(cues,10),null);
  const first=selectSubtitleCue(cues,5,5);
  [24,11,12,0,5].forEach(f=>selectSubtitleCue(cues,f,5));
  assert.deepEqual(selectSubtitleCue(cues,5,5),first);
});
