const CAMERA_TYPES = new Set(['static', 'push_in', 'pull_out', 'pan_left', 'pan_right', 'follow']);
const EASINGS = new Set(['linear', 'easeIn', 'easeOut', 'easeInOut']);

const clamp = (value, low, high) => Math.max(low, Math.min(high, value));
const finite = (value, fallback) => Number.isFinite(value) ? value : fallback;

/** Resolve one shot's local frame into immutable, frame-addressable runtime data. */
export function createShotContext(shot, localFrame, format) {
  if (!shot || !Number.isInteger(shot.duration_frames) || shot.duration_frames < 1) {
    throw new TypeError('A shot context needs a positive integer duration_frames');
  }
  if (!Number.isInteger(localFrame) || localFrame < 0 || localFrame >= shot.duration_frames) {
    throw new RangeError(`Local frame ${localFrame} is outside shot ${shot.shot_id}`);
  }

  const camera = shot.camera ?? { type: 'static', parallax_enabled: false };
  const type = camera.type ?? 'static';
  if (!CAMERA_TYPES.has(type)) throw new TypeError(`Unsupported camera type: ${type}`);
  const easing = EASINGS.has(camera.easing) ? camera.easing : 'easeInOut';
  const defaultCenter = { x: format.width / 2, y: format.height / 2 };
  const focusTarget = {
    id: camera.focus_target?.id ?? null,
    x: finite(camera.focus_target?.x, defaultCenter.x),
    y: finite(camera.focus_target?.y, defaultCenter.y),
  };
  const from = camera.from ?? { ...focusTarget, zoom: 1 };
  const to = camera.to ?? from;
  const screenTarget = {
    x: clamp(finite(camera.screen_target?.x, 0.5), 0, 1),
    y: clamp(finite(camera.screen_target?.y, 0.5), 0, 1),
  };
  const progress = shot.duration_frames <= 1 ? 1 : localFrame / (shot.duration_frames - 1);

  return Object.freeze({
    shotId: shot.shot_id,
    startFrame: shot.start_frame,
    durationFrames: shot.duration_frames,
    endFrame: shot.start_frame + shot.duration_frames,
    localFrame,
    absoluteFrame: shot.start_frame + localFrame,
    progress,
    viewport: Object.freeze({ width: format.width, height: format.height }),
    camera: Object.freeze({
      type,
      focusTarget: Object.freeze(focusTarget),
      from: Object.freeze({ x: finite(from.x, focusTarget.x), y: finite(from.y, focusTarget.y), zoom: finite(from.zoom, 1) }),
      to: Object.freeze({ x: finite(to.x, focusTarget.x), y: finite(to.y, focusTarget.y), zoom: finite(to.zoom, 1) }),
      followPath: Object.freeze((camera.follow_path ?? []).map(point => Object.freeze({
        frame: point.frame, x: point.x, y: point.y,
      }))),
      easing,
      screenTarget: Object.freeze(screenTarget),
      parallaxEnabled: camera.parallax_enabled === true,
      parallaxStrengths: Object.freeze({ ...(camera.parallax_strengths ?? {}) }),
    }),
  });
}

/** Locate an absolute frame using half-open shot intervals. */
export function findActiveShot(shots, absoluteFrame) {
  if (!Number.isInteger(absoluteFrame) || absoluteFrame < 0) {
    throw new RangeError(`Invalid absolute frame: ${absoluteFrame}`);
  }
  const shot = shots.find(item => absoluteFrame >= item.start_frame && absoluteFrame < item.start_frame + item.duration_frames);
  if (!shot) throw new RangeError(`No active shot at frame ${absoluteFrame}`);
  return shot;
}
