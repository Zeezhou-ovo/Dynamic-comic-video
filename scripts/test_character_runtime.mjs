import test from 'node:test';
import assert from 'node:assert/strict';
import { createShotContext } from '../assets/remotion/src/runtime/shot-context.mjs';
import { evaluateCamera } from '../assets/remotion/src/runtime/camera-controller.mjs';
import { evaluateLayerTransform } from '../assets/remotion/src/runtime/parallax-controller.mjs';
import {
  createCharacterPerformanceContext,
  evaluateCharacterPerformance,
  evaluateCharacterPart,
  resolveCharacterLayerAsset,
} from '../assets/remotion/src/runtime/character-controller.mjs';

const capabilities = { parts: ['body', 'head', 'eyes', 'mouth', 'right_arm'], poses: ['point'], expressions: ['happy'] };
const performer = {
  character_id: 'lin', role: 'idle', root_pivot: [0.3, 0.5], root_easing: 'easeInOut',
  root_keys: [
    { frame: 0, x: 0, y: 0, scale: 1, rotation: 0, opacity: 1 },
    { frame: 20, x: 10, y: -4, scale: 1.2, rotation: 8, opacity: 0.5 },
  ],
  events: [], capabilities,
};

function contextAt(frame, override = {}) {
  return createCharacterPerformanceContext({
    characterId: 'lin', performance: { ...performer, ...override }, capabilities,
    absoluteFrame: 100 + frame, localFrame: frame, startFrame: 100, durationFrames: 21, fps: 24,
  });
}

test('root transform eases from local frame keys and supports random access', () => {
  const state = evaluateCharacterPerformance(contextAt(10));
  assert.deepEqual(state.root, { x: 5, y: -2, scale: 1.1, rotation: 4, opacity: 0.75 });
  assert.deepEqual(evaluateCharacterPerformance(contextAt(0)).root, { x: 0, y: 0, scale: 1, rotation: 0, opacity: 1 });
  const expected = evaluateCharacterPerformance(contextAt(7));
  for (const frame of [18, 0, 7, 14, 2]) evaluateCharacterPerformance(contextAt(frame));
  assert.deepEqual(evaluateCharacterPerformance(contextAt(7)), expected);
});

test('local part tracks combine with generated character motion', () => {
  const state = evaluateCharacterPerformance(contextAt(8, {
    events: [{ event_id: 'nod', preset: 'nod', start_frame: 2, peak_frame: 5, settle_frame: 7, end_frame: 10, easing: 'linear' }],
  }));
  const part = evaluateCharacterPart(8, {
    part: 'head', easing: 'linear', keys: [{ frame: 0, x: 1, y: 2, rotation: 3, opacity: 1 }, { frame: 20, x: 5, y: 6, rotation: 7, opacity: 0.5 }],
  }, state);
  assert.equal(part.x, 2.6);
  assert.equal(part.y, 4.6);
  assert.equal(part.rotation, 12.6);
  assert.equal(part.opacity, 0.8);
});

test('talk uses audio-timed mouth frames and falls back deterministically when timing is absent', () => {
  const timedContext = createCharacterPerformanceContext({
    characterId: 'lin', performance: { ...performer, role: 'speaker' }, capabilities,
    absoluteFrame: 104, localFrame: 4, startFrame: 100, durationFrames: 21, fps: 24,
    dialogue: [{ speaker: 'lin', start_frame: 2, end_frame: 10, mouth_open_frames: [2, 4] }],
  });
  const open = evaluateCharacterPerformance(timedContext);
  assert.equal(open.states.mouth, 'open');
  assert.equal(resolveCharacterLayerAsset({ acting: { part: 'mouth' }, state_assets: { open: 'mouth-open.png' } }, open, 4), 'mouth-open.png');
  const closedContext = createCharacterPerformanceContext({
    characterId: 'lin', performance: { ...performer, role: 'speaker', events: [{ event_id: 'talk', preset: 'talk', start_frame: 0, peak_frame: 1, settle_frame: 19, end_frame: 20 }] }, capabilities,
    absoluteFrame: 105, localFrame: 5, startFrame: 100, durationFrames: 21, fps: 24,
  });
  assert.equal(evaluateCharacterPerformance(closedContext).states.mouth, 'closed');
  assert.equal(evaluateCharacterPerformance(contextAt(4, { role: 'speaker', events: [{ event_id: 'talk', preset: 'talk', start_frame: 0, peak_frame: 1, settle_frame: 19, end_frame: 20 }] })).states.mouth, 'open');
});

test('pose, expression, blink and point resolve through the mapped part state assets', () => {
  const state = evaluateCharacterPerformance(contextAt(5, {
    pose: 'point', expression: 'happy',
    events: [{ event_id: 'blink', preset: 'blink', start_frame: 2, peak_frame: 4, settle_frame: 5, end_frame: 7 },
      { event_id: 'point', preset: 'point', part: 'right_arm', start_frame: 2, peak_frame: 4, settle_frame: 9, end_frame: 12 }],
  }));
  assert.equal(state.states.eyes, 'blink');
  assert.equal(state.states.expression, 'expression:happy');
  assert.equal(state.states.pose, 'pose:point');
  assert.equal(state.parts.right_arm.rotation, -42);
  assert.equal(resolveCharacterLayerAsset({ acting: { part: 'eyes' }, state_assets: { blink: 'eyes-blink.png' } }, state, 5), 'eyes-blink.png');
  assert.equal(resolveCharacterLayerAsset({ acting: { part: 'mouth' }, state_assets: { 'expression:happy': 'mouth-happy.png' } }, state, 5), 'mouth-happy.png');
  assert.equal(resolveCharacterLayerAsset({ acting: { part: 'right_arm' }, state_assets: { 'pose:point': 'arm-point.png' } }, state, 5), 'arm-point.png');
});

test('secondary motion phase and absolute-frame output are stable across seek order', () => {
  const sample = () => evaluateCharacterPerformance(contextAt(17));
  const first = sample();
  for (const frame of [20, 1, 9, 17, 3]) evaluateCharacterPerformance(contextAt(frame));
  assert.deepEqual(sample(), first);
  assert.notEqual(evaluateCharacterPerformance(contextAt(1)).parts.body.scale, evaluateCharacterPerformance(contextAt(17)).parts.body.scale);
});

test('character root/part transforms execute alongside camera and parallax transforms', () => {
  const cameraShot = { shot_id: 'combo', start_frame: 48, duration_frames: 21,
    camera: { type: 'push_in', focus_target: { x: 480, y: 270 }, from: { x: 480, y: 270, zoom: 1 }, to: { x: 480, y: 270, zoom: 1.1 }, parallax_enabled: true } };
  const camera = evaluateCamera(10, createShotContext(cameraShot, 10, { width: 960, height: 540 }));
  const bg = evaluateLayerTransform(camera, 'background', { width: 960, height: 540 });
  const character = evaluateLayerTransform(camera, 'character', { width: 960, height: 540 });
  const state = evaluateCharacterPerformance(contextAt(10));
  const arm = evaluateCharacterPart(10, { part: 'right_arm', keys: [], pivot: [0.7, 0.5] }, state);
  assert.ok(camera.zoom > 1);
  assert.notEqual(bg.transform, character.transform);
  assert.equal(state.root.x, 5);
  assert.equal(arm.scale, 1);
});
