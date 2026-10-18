import { shakeOffset } from './performance-controller.mjs';

const clamp01 = (value) => Math.max(0, Math.min(1, value));

function envelope(frame, event) {
  if (frame < event.start_frame || frame >= event.end_frame) return 0;
  const length = Math.max(1, event.end_frame - event.start_frame);
  const local = frame - event.start_frame;
  const fadeFrames = Math.max(1, Math.min(event.fade_frames ?? 3, Math.floor(length / 2)));
  const fadeIn = clamp01((local + 1) / fadeFrames);
  const fadeOut = clamp01((length - local) / fadeFrames);
  return Math.min(fadeIn, fadeOut) * (event.intensity ?? 1);
}

/**
 * Convert authored V2 effect events into renderer-friendly state.
 * The renderer decides how each visual primitive is drawn.
 */
export function evaluateEffects(frame, events = []) {
  const active = [];
  for (const event of events) {
    const opacity = envelope(frame, event);
    if (opacity <= 0) continue;
    active.push(Object.freeze({
      id: event.event_id ?? null,
      type: event.effect_type,
      opacity,
      color: event.color ?? null,
      position: event.position ?? [0.5, 0.5],
      size: event.size ?? 0.13,
      angle: event.angle ?? 0,
      strength: event.strength ?? 1,
    }));
  }
  return Object.freeze({
    active: Object.freeze(active),
    screenShakeX: shakeOffset(frame, events),
  });
}
