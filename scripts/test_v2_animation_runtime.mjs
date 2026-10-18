import test from 'node:test';
import assert from 'node:assert/strict';
import { evaluatePoseClip, evaluatePoseTrack } from '../assets/remotion/src/runtime/pose-controller.mjs';
import { evaluateEffects } from '../assets/remotion/src/runtime/effect-controller.mjs';

const clip = {
  clip_id: 'dash',
  start_frame: 10,
  anticipation_end_frame: 13,
  action_end_frame: 18,
  hold_end_frame: 24,
  end_frame: 30,
  base_pose: 'idle',
  action_pose: 'dash',
  smear: true,
  translate: { x: -120, y: 0 },
  squash_stretch: { x: 0.2, y: -0.1 },
};

test('pose clip exposes deterministic limited-animation phases', () => {
  assert.equal(evaluatePoseClip(9, clip), null);
  assert.equal(evaluatePoseClip(10, clip).phase, 'anticipation');
  assert.equal(evaluatePoseClip(14, clip).phase, 'action');
  assert.equal(evaluatePoseClip(14, clip).pose, 'dash');
  assert.equal(evaluatePoseClip(20, clip).phase, 'hold');
  assert.equal(evaluatePoseClip(25, clip).phase, 'settle');
  assert.equal(evaluatePoseClip(30, clip), null);
});

test('action phase can request smear and squash/stretch without frame history', () => {
  const first = evaluatePoseClip(16, clip);
  for (const frame of [28, 10, 22, 16, 12]) evaluatePoseClip(frame, clip);
  const again = evaluatePoseClip(16, clip);
  assert.deepEqual(again, first);
  assert.equal(first.smear, true);
  assert.ok(first.root.scaleX > 1);
  assert.ok(first.root.scaleY < 1);
  assert.ok(first.root.x < 0);
});

test('later active pose clips win', () => {
  const second = { ...clip, clip_id: 'impact', start_frame: 14, end_frame: 20, action_pose: 'impact' };
  const state = evaluatePoseTrack(16, [clip, second]);
  assert.equal(state.clipId, 'impact');
});

test('effect runtime returns active effects and delegates screen shake', () => {
  const effects = evaluateEffects(5, [
    { event_id: 'flash', effect_type: 'flash', start_frame: 4, end_frame: 10, intensity: 0.8 },
    { event_id: 'shake', effect_type: 'screen_shake', start_frame: 4, end_frame: 10, intensity: 1 },
  ]);
  assert.equal(effects.active.length, 2);
  assert.equal(effects.active[0].type, 'flash');
  assert.ok(effects.active[0].opacity > 0);
  assert.notEqual(effects.screenShakeX, 0);
});

test('inactive effects disappear outside half-open interval', () => {
  assert.equal(evaluateEffects(3, [
    { event_id: 'lines', effect_type: 'speed_lines', start_frame: 4, end_frame: 10 },
  ]).active.length, 0);
  assert.equal(evaluateEffects(10, [
    { event_id: 'lines', effect_type: 'speed_lines', start_frame: 4, end_frame: 10 },
  ]).active.length, 0);
});
