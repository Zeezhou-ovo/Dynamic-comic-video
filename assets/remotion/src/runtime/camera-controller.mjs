const clamp = (value, low = 0, high = 1) => Math.max(low, Math.min(high, value));
const lerp = (start, end, amount) => start + (end - start) * amount;

export const EASING = Object.freeze({
  linear: value => value,
  easeIn: value => value * value,
  easeOut: value => 1 - (1 - value) * (1 - value),
  easeInOut: value => value < 0.5 ? 2 * value * value : 1 - ((-2 * value + 2) ** 2) / 2,
});

function samplePath(path, frame, easing) {
  if (!path.length) return null;
  if (frame <= path[0].frame) return { x: path[0].x, y: path[0].y };
  for (let index = 1; index < path.length; index += 1) {
    const from = path[index - 1];
    const to = path[index];
    if (frame <= to.frame) {
      const span = to.frame - from.frame;
      const progress = span <= 0 ? 1 : clamp((frame - from.frame) / span);
      const eased = easing(progress);
      return { x: lerp(from.x, to.x, eased), y: lerp(from.y, to.y, eased) };
    }
  }
  const last = path[path.length - 1];
  return { x: last.x, y: last.y };
}

/** Pure camera evaluation: every output is derived from the shot and requested frame. */
export function evaluateCamera(frame, shotContext) {
  const camera = shotContext.camera;
  const easing = EASING[camera.easing] ?? EASING.easeInOut;
  const progress = shotContext.durationFrames <= 1
    ? 1
    : clamp(frame / (shotContext.durationFrames - 1));
  const easedProgress = easing(progress);
  let x = lerp(camera.from.x, camera.to.x, easedProgress);
  let y = lerp(camera.from.y, camera.to.y, easedProgress);
  const zoom = lerp(camera.from.zoom, camera.to.zoom, easedProgress);

  if (camera.type === 'static') {
    x = camera.from.x;
    y = camera.from.y;
  } else if (camera.type === 'follow') {
    const focus = samplePath(camera.followPath, frame, easing);
    if (focus) ({ x, y } = focus);
  }

  return Object.freeze({
    shotId: shotContext.shotId,
    type: camera.type,
    x,
    y,
    zoom,
    focusX: camera.focusTarget.x,
    focusY: camera.focusTarget.y,
    screenX: camera.screenTarget.x,
    screenY: camera.screenTarget.y,
    progress,
    easedProgress,
    parallaxEnabled: camera.parallaxEnabled,
    parallaxStrengths: camera.parallaxStrengths,
  });
}
