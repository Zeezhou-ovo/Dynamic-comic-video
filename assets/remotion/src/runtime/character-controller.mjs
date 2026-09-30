import { EASING } from './camera-controller.mjs';

const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
const lerp = (a, b, t) => a + (b - a) * t;

const identityRoot = () => ({ x: 0, y: 0, scale: 1, rotation: 0, opacity: 1 });

function sampleTrack(frame, keys, fallback, easingName = 'linear') {
  if (!keys?.length) return { ...fallback };
  const keyValues = key => Object.fromEntries(Object.keys(fallback).map(name => [name, key[name] ?? fallback[name]]));
  if (frame <= keys[0].frame) return { ...fallback, ...keyValues(keys[0]) };
  for (let index = 1; index < keys.length; index += 1) {
    const left = keys[index - 1];
    const right = keys[index];
    if (frame <= right.frame) {
      const progress = clamp((frame - left.frame) / Math.max(1, right.frame - left.frame), 0, 1);
      const ease = EASING[easingName] ?? EASING.linear;
      const amount = ease(progress);
      const result = { ...fallback };
      for (const key of Object.keys(fallback)) result[key] = lerp(left[key] ?? fallback[key], right[key] ?? fallback[key], amount);
      return result;
    }
  }
  return { ...fallback, ...keyValues(keys.at(-1)) };
}

function hashSeed(text) {
  let hash = 2166136261;
  for (let index = 0; index < text.length; index += 1) {
    hash ^= text.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function eventEnvelope(frame, event, easingName) {
  if (frame < event.start_frame || frame > event.end_frame) return 0;
  const easing = EASING[event.easing ?? easingName] ?? EASING.easeInOut;
  if (frame <= event.peak_frame) {
    const duration = Math.max(1, event.peak_frame - event.start_frame);
    return easing(clamp((frame - event.start_frame) / duration, 0, 1));
  }
  if (frame <= event.settle_frame) return 1;
  const duration = Math.max(1, event.end_frame - event.settle_frame);
  return 1 - easing(clamp((frame - event.settle_frame) / duration, 0, 1));
}

function blankPart() {
  return { x: 0, y: 0, rotation: 0, scale: 1, opacity: 1 };
}

function addPart(parts, part, delta) {
  if (!part) return;
  const value = parts[part] ?? blankPart();
  value.x += delta.x ?? 0;
  value.y += delta.y ?? 0;
  value.rotation += delta.rotation ?? 0;
  value.scale *= delta.scale ?? 1;
  value.opacity *= delta.opacity ?? 1;
  parts[part] = value;
}

function chooseArm(capabilities, requested) {
  if (['arm', 'left_arm', 'right_arm'].includes(requested)) return requested;
  if (capabilities.parts.includes('right_arm')) return 'right_arm';
  if (capabilities.parts.includes('left_arm')) return 'left_arm';
  return 'arm';
}

/** Build an immutable character context directly from the requested absolute frame. */
export function createCharacterPerformanceContext({
  characterId,
  performance,
  capabilities,
  absoluteFrame,
  localFrame,
  startFrame,
  durationFrames,
  fps,
  dialogue = [],
}) {
  if (!performance || !Number.isInteger(localFrame) || localFrame < 0 || localFrame >= durationFrames) {
    throw new RangeError(`Invalid performance context for ${characterId} at local frame ${localFrame}`);
  }
  return Object.freeze({
    characterId,
    absoluteFrame,
    localFrame,
    startFrame,
    endFrame: startFrame + durationFrames,
    durationFrames,
    progress: durationFrames <= 1 ? 1 : localFrame / (durationFrames - 1),
    fps,
    role: performance.role,
    pose: performance.pose ?? null,
    expression: performance.expression ?? null,
    rootPivot: Object.freeze(performance.root_pivot ?? [0.5, 0.5]),
    rootKeys: performance.root_keys ?? [],
    rootEasing: performance.root_easing ?? 'easeInOut',
    events: performance.events ?? [],
    capabilities: Object.freeze({
      parts: Object.freeze([...(capabilities?.parts ?? [])]),
      poses: Object.freeze([...(capabilities?.poses ?? [])]),
      expressions: Object.freeze([...(capabilities?.expressions ?? [])]),
    }),
    dialogue: Object.freeze(dialogue.map(cue => Object.freeze({ ...cue }))),
  });
}

/** Evaluate root, part, pose/expression, and mouth outputs without frame history. */
export function evaluateCharacterPerformance(context) {
  const frame = context.localFrame;
  const root = sampleTrack(frame, context.rootKeys, identityRoot(), context.rootEasing);
  const parts = {};
  const states = {};
  const phase = (hashSeed(context.characterId) / 0xffffffff) * Math.PI * 2;
  let mouthState = 'closed';
  let activeTalk = false;

  if (context.role === 'idle' || context.role === 'listener') {
    addPart(parts, 'body', { scale: 1 + 0.004 * Math.sin((Math.PI * 2 * frame) / (context.fps * 4) + phase) });
  }

  const activeCue = context.dialogue.find(cue => cue.speaker === context.characterId && frame >= cue.start_frame && frame < cue.end_frame);
  if (activeCue) {
    const openFrames = activeCue.mouth_open_frames ?? [];
    mouthState = openFrames.length
      ? (openFrames.includes(frame - activeCue.start_frame) ? 'open' : 'closed')
      : ((frame - activeCue.start_frame) % 9 < 5 ? 'open' : 'closed');
    activeTalk = true;
    addPart(parts, 'body', { y: Math.sin((Math.PI * 2 * frame) / 12 + phase) * 0.5 });
  }

  for (const event of context.events) {
    const envelope = eventEnvelope(frame, event, context.rootEasing);
    if (envelope <= 0) continue;
    const amount = event.amplitude ?? 1;
    switch (event.preset) {
      case 'idle':
        if (context.role !== 'idle' && context.role !== 'listener') {
          addPart(parts, 'body', { scale: 1 + 0.004 * Math.sin((Math.PI * 2 * frame) / (context.fps * 4) + phase) });
        }
        break;
      case 'talk': {
        activeTalk = true;
        const localTalkFrame = frame - event.start_frame;
        if (!activeCue) mouthState = localTalkFrame % 9 < 5 ? 'open' : 'closed';
        addPart(parts, 'body', { y: Math.sin((Math.PI * 2 * frame) / 12 + phase) * 0.65 * envelope });
        break;
      }
      case 'nod':
        addPart(parts, 'head', { rotation: amount * 12 * envelope, y: amount * 1.5 * envelope });
        break;
      case 'shake_head': {
        const progress = (frame - event.start_frame) / Math.max(1, event.end_frame - event.start_frame);
        addPart(parts, 'head', { rotation: amount * 9 * Math.sin(progress * Math.PI * 4) * envelope });
        break;
      }
      case 'point':
      case 'raise_hand': {
        const arm = chooseArm(context.capabilities, event.part);
        const angle = event.preset === 'point' ? 42 : 58;
        addPart(parts, arm, { rotation: (arm === 'left_arm' ? angle : -angle) * amount * envelope });
        break;
      }
      case 'blink':
        if (frame >= event.peak_frame && frame <= event.settle_frame) states.eyes = 'blink';
        break;
      case 'small_bounce':
        root.y -= (event.amplitude ?? 8) * envelope;
        root.scale *= 1 + 0.012 * envelope;
        break;
      default:
        break;
    }
  }

  if (activeTalk && context.capabilities.parts.includes('mouth')) {
    states.mouth = mouthState;
  }
  if (context.pose) states.pose = `pose:${context.pose}`;
  if (context.expression) states.expression = `expression:${context.expression}`;

  return Object.freeze({
    characterId: context.characterId,
    absoluteFrame: context.absoluteFrame,
    localFrame: frame,
    progress: context.progress,
    role: context.role,
    root: Object.freeze(root),
    rootPivot: context.rootPivot,
    parts: Object.freeze(Object.fromEntries(Object.entries(parts).map(([key, value]) => [key, Object.freeze(value)]))),
    states: Object.freeze(states),
    mouth: Object.freeze({ state: mouthState, openness: mouthState === 'open' ? 1 : 0 }),
    activeTalk,
  });
}

/** Interpolate a legacy acting part track, then layer event motion in the same local space. */
export function evaluateCharacterPart(frame, acting, performanceState) {
  const base = sampleTrack(frame, acting?.keys ?? [], blankPart(), acting?.easing ?? 'linear');
  const part = acting?.part;
  const aliases = { arm: ['right_arm', 'left_arm'], right_arm: ['arm'], left_arm: ['arm'] };
  const extra = performanceState?.parts?.[part]
    ?? aliases[part]?.map(alias => performanceState?.parts?.[alias]).find(Boolean)
    ?? blankPart();
  return Object.freeze({
    x: base.x + extra.x,
    y: base.y + extra.y,
    rotation: base.rotation + extra.rotation,
    scale: (base.scale ?? 1) * extra.scale,
    opacity: base.opacity * extra.opacity,
  });
}

export function resolveCharacterLayerAsset(layer, performanceState, localFrame) {
  const stateAssets = layer.state_assets ?? {};
  const part = layer.acting?.part;
  const states = performanceState?.states ?? {};
  for (const state of [
    part === 'mouth' && states.mouth,
    part === 'eyes' && states.eyes,
    states.expression,
    states.pose,
  ]) {
    if (state && stateAssets[state]) return stateAssets[state];
  }
  const pose = layer.acting?.poses?.filter(item => item.frame <= localFrame).at(-1)?.asset;
  return pose ?? layer.asset;
}
