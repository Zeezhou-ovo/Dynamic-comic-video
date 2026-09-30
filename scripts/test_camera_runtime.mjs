import test from 'node:test';
import assert from 'node:assert/strict';
import { createShotContext, findActiveShot } from '../assets/remotion/src/runtime/shot-context.mjs';
import { evaluateCamera } from '../assets/remotion/src/runtime/camera-controller.mjs';
import { DEPTH_STRENGTHS, evaluateLayerTransform } from '../assets/remotion/src/runtime/parallax-controller.mjs';

const viewport = { width: 960, height: 540 };
const baseShot = {
  shot_id: 'camera-test', start_frame: 0, duration_frames: 9,
  camera: { type: 'static', parallax_enabled: false },
};

function stateAt(type, localFrame, overrides = {}) {
  const camera = {
    type,
    focus_target: { x: 480, y: 320 },
    from: { x: 480, y: 320, zoom: 1 },
    to: { x: 480, y: 320, zoom: 1 },
    easing: 'linear',
    screen_target: { x: 0.5, y: 0.62 },
    parallax_enabled: false,
    ...overrides,
  };
  const shot = { ...baseShot, camera };
  const context = createShotContext(shot, localFrame, viewport);
  return evaluateCamera(localFrame, context);
}

test('static camera is an identity framing at first, middle and last frame', () => {
  for (const frame of [0, 4, 8]) {
    const state = stateAt('static', frame);
    assert.deepEqual([state.x, state.y, state.zoom], [480, 320, 1]);
  }
});

test('push_in and pull_out interpolate zoom across the shot', () => {
  const push = frame => stateAt('push_in', frame, {
    from: { x: 480, y: 320, zoom: 1 }, to: { x: 480, y: 320, zoom: 1.5 },
  });
  const pull = frame => stateAt('pull_out', frame, {
    from: { x: 480, y: 320, zoom: 1.5 }, to: { x: 480, y: 320, zoom: 1 },
  });
  assert.deepEqual([push(0).zoom, push(4).zoom, push(8).zoom], [1, 1.25, 1.5]);
  assert.deepEqual([pull(0).zoom, pull(4).zoom, pull(8).zoom], [1.5, 1.25, 1]);
});

test('pan_left and pan_right move camera world x in the named direction', () => {
  const left = frame => stateAt('pan_left', frame, {
    from: { x: 600, y: 320, zoom: 1 }, to: { x: 400, y: 320, zoom: 1 },
  });
  const right = frame => stateAt('pan_right', frame, {
    from: { x: 400, y: 320, zoom: 1 }, to: { x: 600, y: 320, zoom: 1 },
  });
  assert.deepEqual([left(0).x, left(4).x, left(8).x], [600, 500, 400]);
  assert.deepEqual([right(0).x, right(4).x, right(8).x], [400, 500, 600]);
});

test('follow samples local-frame path points deterministically', () => {
  const camera = {
    focus_target: { x: 300, y: 320 },
    from: { x: 300, y: 320, zoom: 1 }, to: { x: 700, y: 320, zoom: 1 },
    follow_path: [{ frame: 0, x: 300, y: 320 }, { frame: 4, x: 500, y: 320 }, { frame: 8, x: 700, y: 320 }],
  };
  assert.deepEqual([stateAt('follow', 0, camera).x, stateAt('follow', 4, camera).x, stateAt('follow', 8, camera).x], [300, 500, 700]);
});

test('all supported easing functions have deterministic midpoint behavior', () => {
  const expected = { linear: 0.5, easeIn: 0.25, easeOut: 0.75, easeInOut: 0.5 };
  for (const [easing, midpoint] of Object.entries(expected)) {
    const state = stateAt('push_in', 4, {
      from: { x: 480, y: 320, zoom: 1 }, to: { x: 480, y: 320, zoom: 2 }, easing,
    });
    assert.equal(state.zoom, 1 + midpoint);
  }
});

test('active shot boundaries use half-open absolute frame intervals', () => {
  const shots = [
    { shot_id: 'wide', start_frame: 0, duration_frames: 48 },
    { shot_id: 'push', start_frame: 48, duration_frames: 48 },
    { shot_id: 'pan', start_frame: 96, duration_frames: 48 },
  ];
  assert.equal(findActiveShot(shots, 47).shot_id, 'wide');
  assert.equal(findActiveShot(shots, 48).shot_id, 'push');
  assert.equal(findActiveShot(shots, 95).shot_id, 'push');
  assert.equal(findActiveShot(shots, 96).shot_id, 'pan');
});

test('random access order does not change camera state at the same frame', () => {
  const shot = {
    ...baseShot, duration_frames: 241,
    camera: {
      type: 'pan_right', focus_target: { x: 480, y: 320 },
      from: { x: 400, y: 320, zoom: 1 }, to: { x: 700, y: 320, zoom: 1.1 },
      easing: 'easeInOut', parallax_enabled: true,
    },
  };
  const at = frame => evaluateCamera(frame, createShotContext(shot, frame, viewport));
  const expected = at(120);
  for (const frame of [10, 240, 120, 0, 181, 33]) at(frame);
  assert.deepEqual(at(120), expected);
});

test('five depth layers react to one camera state at distinct rates', () => {
  const camera = {
    x: 680, y: 360, zoom: 1.3, focusX: 480, focusY: 320,
    screenX: 0.5, screenY: 0.62, parallaxEnabled: true, parallaxStrengths: {},
  };
  const depths = Object.keys(DEPTH_STRENGTHS);
  const transforms = depths.map(depth => evaluateLayerTransform(camera, depth, viewport));
  assert.deepEqual(transforms.map(item => item.factor), [1.2, 1, 0.55, 0.2, 0.05]);
  assert.equal(new Set(transforms.map(item => item.transform)).size, 5);
  assert.ok(transforms[0].translateX < transforms[1].translateX);
  assert.ok(transforms[1].translateX < transforms[2].translateX);
  assert.ok(transforms[2].translateX < transforms[3].translateX);
  assert.ok(transforms[3].translateX < transforms[4].translateX);
});

test('disabled parallax applies the same camera transform to every depth', () => {
  const camera = {
    x: 620, y: 330, zoom: 1.2, focusX: 480, focusY: 320,
    screenX: 0.5, screenY: 0.5, parallaxEnabled: false, parallaxStrengths: {},
  };
  const transforms = Object.keys(DEPTH_STRENGTHS).map(depth => evaluateLayerTransform(camera, depth, viewport));
  assert.equal(new Set(transforms.map(item => item.transform)).size, 1);
});
