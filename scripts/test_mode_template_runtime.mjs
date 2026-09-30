import test from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createShotContext, findActiveShot } from '../assets/remotion/src/runtime/shot-context.mjs';
import { evaluateCamera } from '../assets/remotion/src/runtime/camera-controller.mjs';
import { evaluateLayerTransform } from '../assets/remotion/src/runtime/parallax-controller.mjs';
import { createCharacterPerformanceContext, evaluateCharacterPerformance } from '../assets/remotion/src/runtime/character-controller.mjs';
import { buildSceneGraph } from '../assets/remotion/src/runtime/scene-graph.mjs';

const root = fileURLToPath(new URL('..', import.meta.url));
const folder = mkdtempSync(join(tmpdir(), 'mode-runtime-'));
const python = `import json,sys
from pathlib import Path
from make_phase5_fixture import build
from pipeline import validate,local
from template_system import resolve_project_mode
from director import compile_director_plan
from production import render_payload
p=Path(sys.argv[1]);build(p,sys.argv[2],sys.argv[3])
data,errors,_=validate(p,assets=True)
assert not errors,errors
compiled=compile_director_plan(resolve_project_mode(p,data),data,p)
print(json.dumps(render_payload(p,compiled,local)))`;
const payloads = {};
try {
  for (const [mode, template] of [['dialogue-comedy','generic-room'],['knowledge-explainer','generic-room'],['dialogue-comedy','generic-outdoor'],['motion-comic','generic-room']]) {
    const key = `${mode}/${template}`;
    payloads[key] = JSON.parse(execFileSync('python3', ['-c', python, join(folder, key.replace('/', '-')), mode, template], {
      cwd: root, env: { ...process.env, PYTHONPATH: `${root}/scripts:${process.env.PYTHONPATH ?? ''}` }, encoding: 'utf8',
    }));
  }
} finally { rmSync(folder, { recursive: true, force: true }); }

function at(data, absoluteFrame) {
  const shot = findActiveShot(data.shots, absoluteFrame);
  const frame = absoluteFrame - shot.start_frame;
  const camera = evaluateCamera(frame, createShotContext(shot, frame, data.format));
  const transforms = Object.fromEntries(['background','midground','character','foreground'].map(d => [d,evaluateLayerTransform(camera,d,data.format)]));
  const characters = shot.character_performance.map(p => evaluateCharacterPerformance(createCharacterPerformanceContext({
    characterId: p.character_id, performance: p, capabilities: p.capabilities, absoluteFrame,
    localFrame: frame, startFrame: shot.start_frame, durationFrames: shot.duration_frames,
    fps: data.format.fps, dialogue: shot.dialogue,
  })));
  const graph = buildSceneGraph({ sceneManifest: data.scene_manifest, characterAssetManifest: data.character_assets,
    sceneInstances: shot.scene_instances, visibleObjects: shot.visible_objects, viewport: data.format });
  return { camera, transforms, characters, graph };
}

test('mode output executes camera, scene and performance deterministically in every frame', () => {
  for (const data of Object.values(payloads)) {
    const sequential = Array.from({length:data.format.duration_frames}, (_,f)=>at(data,f));
    // Scrambled jumps, end-first access, and sparse frames match sequential sampling.
    for (const f of [data.format.duration_frames-1,0,17,80,4,42,80]) assert.deepEqual(at(data,f), sequential[f]);
    for (let f=data.format.duration_frames-1; f>=0; f-=7) assert.deepEqual(at(data,f),sequential[f]);
    for (const state of sequential) {
      const bg=state.transforms.background;
      assert.ok(bg.translateX<=1 && bg.translateY<=1);
      assert.ok(bg.translateX+960*bg.zoom>=959 && bg.translateY+540*bg.zoom>=539);
      assert.ok(state.graph.nodes.some(n=>n.nodeType==='character'));
    }
  }
});

test('mode camera and parallax strength reach runtime rather than only schema', () => {
  const c=payloads['dialogue-comedy/generic-room'],e=payloads['knowledge-explainer/generic-room'];
  const movement=d=>d.shots.reduce((sum,s)=>sum+Math.abs(at(d,s.start_frame+s.duration_frames-1).camera.zoom-at(d,s.start_frame).camera.zoom),0);
  assert.ok(movement(c)>movement(e));
  const cs=c.shots.find(s=>s.camera.parallax_enabled),es=e.shots.find(s=>s.camera.parallax_enabled);
  assert.notEqual(at(c,cs.start_frame).transforms.background.factor,at(e,es.start_frame).transforms.background.factor);
  assert.ok(payloads['motion-comic/generic-room'].shots.every(s=>s.camera.type==='static'));
});

test('explainer point intensity and speech mouth actually execute with loaded assets', () => {
  const d=payloads['knowledge-explainer/generic-room'];
  const s=d.shots.find(s=>s.character_performance.some(p=>p.events.some(e=>e.preset==='point')));
  const p=s.character_performance.find(p=>p.events.some(e=>e.preset==='point'));
  const event=p.events.find(e=>e.preset==='point');
  const state=at(d,s.start_frame+event.peak_frame).characters[s.character_performance.indexOf(p)];
  assert.equal(state.parts.right_arm.rotation,-42*event.amplitude);
  const mouthStates=new Set();
  for(let f=s.dialogue[0].start_frame;f<s.dialogue[0].end_frame;f++) mouthStates.add(at(d,s.start_frame+f).characters[0].states.mouth);
  assert.deepEqual([...mouthStates].sort(),['closed','open']);
});

test('same mode on a second scene resolves new character world and camera coordinates', () => {
  const room=payloads['dialogue-comedy/generic-room'],out=payloads['dialogue-comedy/generic-outdoor'];
  assert.notDeepEqual(room.shots[0].camera.focus_target,out.shots[0].camera.focus_target);
  assert.notDeepEqual(at(room,0).graph,at(out,0).graph);
  assert.equal(room.shots[0].camera.type,out.shots[0].camera.type);
});
