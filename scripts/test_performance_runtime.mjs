import test from 'node:test';
import assert from 'node:assert/strict';
import {
  captionRuns,
  drivingPropMotion,
  effectOpacity,
  expressionAsset,
  mouthAsset,
  propAngle,
  propTransform,
  shakeOffset,
} from '../assets/remotion/src/runtime/performance-controller.mjs';

const speech = { speaker: 'capy', closed_asset: 'closed.png', open_asset: 'open.png', shape_assets: { small: 'small.png' } };
const cue = { speaker: 'capy', start_frame: 10, end_frame: 14, mouth_shape_frames: ['small', 'open', 'wide', 'closed'], mouth_open_frames: [1] };

test('mouth uses measured shapes, falls back to open for missing shape assets, closes outside speech', () => {
  assert.equal(mouthAsset(9, speech, [cue]), 'closed.png');
  assert.equal(mouthAsset(10, speech, [cue]), 'small.png');
  assert.equal(mouthAsset(11, speech, [cue]), 'open.png');
  assert.equal(mouthAsset(12, speech, [cue]), 'open.png'); // no wide asset
  assert.equal(mouthAsset(13, speech, [cue]), 'closed.png');
  assert.equal(mouthAsset(14, speech, [cue]), 'closed.png');
});

test('authored mouth events override measured shapes; legacy open frames still work', () => {
  const events = [{ speaker: 'capy', shape: 'closed', start_frame: 10, end_frame: 12 }];
  assert.equal(mouthAsset(11, speech, [cue], events), 'closed.png');
  const legacy = { speaker: 'capy', closed_asset: 'c.png', open_asset: 'o.png' };
  assert.equal(mouthAsset(11, legacy, [cue]), 'o.png');
  assert.equal(mouthAsset(10, legacy, [cue]), 'c.png');
});

test('expression pose is active only inside its window and only for its layer', () => {
  const events = [{ layer_id: 'eyes', pose_asset: 'surprised.png', start_frame: 3, end_frame: 9 }];
  assert.equal(expressionAsset(2, 'eyes', events), undefined);
  assert.equal(expressionAsset(3, 'eyes', events), 'surprised.png');
  assert.equal(expressionAsset(5, 'mouth', events), undefined);
  assert.equal(expressionAsset(9, 'eyes', events), undefined);
});

const rock = { pivot: [0.74, 0.92], roll_radius: 160, events: [
  { event_id: 'r', kind: 'rock', start_frame: 0, end_frame: 64, amplitude_deg: 3, period_frames: 22, decay_frames: 24 },
  { event_id: 'l', kind: 'lean', start_frame: 78, end_frame: 107, amplitude_deg: 1.8 },
] };

test('rock starts at full tilt, alternates, decays and comes to rest before its end', () => {
  assert.equal(propAngle(0, rock), 3);
  assert.ok(propAngle(11, rock) < 0, 'half a period later it leans the other way');
  assert.ok(Math.abs(propAngle(33, rock)) < Math.abs(propAngle(11, rock)));
  assert.ok(Math.abs(propAngle(63, rock)) < 0.01);
  assert.equal(propAngle(70, rock), 0);
});

test('lean tips once and returns to rest', () => {
  assert.equal(propAngle(78, rock), 0);
  assert.ok(propAngle(90, rock) > 1.2);
  assert.ok(Math.abs(propAngle(106, rock)) < 0.05);
});

test('prop transform rolls opposite to the tilt and uses CSS clockwise rotation', () => {
  const t = propTransform(0, rock);
  assert.equal(t.origin, '74% 92%');
  assert.ok(t.dx < 0, 'tilting towards screen-left rolls left');
  assert.match(t.transform, /rotate\(-3\.0000deg\)/);
  assert.equal(propTransform(0, null), null);
});

test('attached layers follow their prop, others do not', () => {
  const layers = [{ layer_id: 'horse', prop_motion: rock }, { layer_id: 'mouth', attach_to: 'horse' }, { layer_id: 'bg' }];
  assert.equal(drivingPropMotion(layers[1], layers), rock);
  assert.equal(drivingPropMotion(layers[2], layers), null);
});

test('caption highlight needs an active subtitle_emphasis whose keyword is in the line', () => {
  const events = [{ effect_type: 'subtitle_emphasis', keyword: '马上', start_frame: 0, end_frame: 10 }];
  assert.deepEqual(captionRuns('我要马上！', 3, events).map(run => [run.text, run.highlight]), [['我要', false], ['马上', true], ['！', false]]);
  assert.deepEqual(captionRuns('我要马上！', 12, events), [{ text: '我要马上！', highlight: false }]);
  assert.deepEqual(captionRuns('报告', 3, events), [{ text: '报告', highlight: false }]);
});

test('shake is damped to zero and effects fade in and out', () => {
  const shake = [{ effect_type: 'screen_shake', start_frame: 50, end_frame: 58 }];
  assert.equal(shakeOffset(49, shake), 0);
  assert.ok(Math.abs(shakeOffset(51, shake)) > 0);
  assert.equal(shakeOffset(57, shake), 0);
  const effect = { start_frame: 10, end_frame: 20 };
  assert.ok(effectOpacity(10, effect) < 1);
  assert.equal(effectOpacity(15, effect), 1);
  assert.ok(effectOpacity(19, effect) < 1);
});
