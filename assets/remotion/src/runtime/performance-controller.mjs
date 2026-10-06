// Fixed-camera comic performance: mouth shapes, expression swaps, prop motion,
// comic-effect timing. Pure functions so they can be tested without Remotion.

const SHAPES = new Set(['closed', 'small', 'open', 'round', 'wide']);

/** Pick the mouth asset for a speech track at a shot-local frame. */
export function mouthAsset(frame, speech, cues = [], events = []) {
  const cue = cues.find(c => c.speaker === speech.speaker && frame >= c.start_frame && frame < c.end_frame);
  if (!cue) return speech.closed_asset;
  const manual = events.find(e => e.speaker === speech.speaker && frame >= e.start_frame && frame < e.end_frame);
  let shape = manual?.shape;
  if (!shape) {
    shape = speech.shape_assets && cue.mouth_shape_frames
      ? cue.mouth_shape_frames[frame - cue.start_frame] ?? 'closed'
      : cue.mouth_open_frames?.includes(frame - cue.start_frame) ? 'open' : 'closed';
  }
  if (!SHAPES.has(shape) || shape === 'closed') return speech.closed_asset;
  if (shape === 'open') return speech.open_asset;
  return speech.shape_assets?.[shape] ?? speech.open_asset;
}

/** Authored expression pose for a layer, if one is active. */
export function expressionAsset(frame, layerId, events = []) {
  return events.find(e => e.layer_id === layerId && e.pose_asset && frame >= e.start_frame && frame < e.end_frame)?.pose_asset;
}

const smoothstep = x => {
  const t = Math.min(1, Math.max(0, x));
  return t * t * (3 - 2 * t);
};

/**
 * Prop angle in degrees at a shot-local frame. Positive = counter-clockwise on
 * screen (top of the prop moves towards screen-left).
 *  - rock: caught mid-swing at start_frame, decays, eased to rest before end_frame
 *  - lean: one tip and return (sine bump), slightly asymmetric so it settles
 */
export function propAngle(frame, motion) {
  let angle = 0;
  for (const event of motion?.events ?? []) {
    if (frame < event.start_frame || frame >= event.end_frame) continue;
    const t = frame - event.start_frame;
    const length = event.end_frame - event.start_frame;
    if (event.kind === 'rock') {
      const period = event.period_frames ?? 22;
      const decay = event.decay_frames ?? 24;
      const tail = Math.min(14, Math.max(1, Math.floor(length / 4)));
      const fade = 1 - smoothstep((t - (length - tail)) / tail);
      angle += event.amplitude_deg * Math.exp(-t / decay) * Math.cos((2 * Math.PI * t) / period) * fade;
    } else if (event.kind === 'lean') {
      const u = t / Math.max(1, length - 1);
      angle += event.amplitude_deg * Math.sin(Math.PI * u) * (1 - 0.35 * u);
    }
  }
  return angle;
}

/**
 * CSS transform for a prop (or a layer attached to one). Rolling moves the
 * contact point along the floor by roll_radius × angle (radians).
 */
export function propTransform(frame, motion) {
  if (!motion) return null;
  const angle = propAngle(frame, motion);
  const dx = -(motion.roll_radius ?? 0) * (angle * Math.PI) / 180;
  return {
    angle,
    dx,
    origin: `${motion.pivot[0] * 100}% ${motion.pivot[1] * 100}%`,
    // CSS rotate() is clockwise-positive, our angle is counter-clockwise-positive.
    transform: `translate(${dx.toFixed(3)}px, 0px) rotate(${(-angle).toFixed(4)}deg)`,
  };
}

/** The prop motion that drives a layer: its own, or that of the layer it is attached to. */
export function drivingPropMotion(layer, layers) {
  if (layer.prop_motion) return layer.prop_motion;
  if (layer.attach_to) return layers.find(item => item.layer_id === layer.attach_to)?.prop_motion ?? null;
  return null;
}

/** Horizontal screen-shake offset in pixels (ported damped curve). */
export function shakeOffset(frame, events = []) {
  const event = events.find(e => e.effect_type === 'screen_shake' && frame >= e.start_frame && frame < e.end_frame);
  if (!event) return 0;
  const progress = (frame - event.start_frame) / Math.max(1, event.end_frame - event.start_frame - 1);
  const stops = [[0, 0], [0.15, 4], [0.45, -3], [0.7, 1], [1, 0]];
  for (let i = 1; i < stops.length; i++) {
    if (progress <= stops[i][0]) {
      const [x0, y0] = stops[i - 1];
      const [x1, y1] = stops[i];
      return (y0 + ((y1 - y0) * (progress - x0)) / (x1 - x0)) * (event.intensity ?? 1);
    }
  }
  return 0;
}

/** Split a caption into plain/highlighted runs for an active subtitle_emphasis event. */
export function captionRuns(text, frame, events = []) {
  const event = events.find(e => e.effect_type === 'subtitle_emphasis' && e.keyword && frame >= e.start_frame && frame < e.end_frame);
  if (!event || !text.includes(event.keyword)) return [{ text, highlight: false }];
  const runs = [];
  text.split(event.keyword).forEach((part, index) => {
    if (index > 0) runs.push({ text: event.keyword, highlight: true, color: event.color ?? '#ffd36a' });
    if (part) runs.push({ text: part, highlight: false });
  });
  return runs;
}

/** Fade-in/out opacity for a drawn comic effect. */
export function effectOpacity(frame, event) {
  const age = frame - event.start_frame;
  const length = event.end_frame - event.start_frame;
  return Math.max(0, Math.min(1, (age + 1) / 3, (length - age) / 3)) * (event.intensity ?? 1);
}
