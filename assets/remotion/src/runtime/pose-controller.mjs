const clamp01 = (value) => Math.max(0, Math.min(1, value));

export const POSE_PHASES = Object.freeze(['anticipation', 'action', 'hold', 'settle']);

function easeInOut(t) {
  const x = clamp01(t);
  return x < 0.5 ? 2 * x * x : 1 - ((-2 * x + 2) ** 2) / 2;
}

function phaseProgress(frame, start, end) {
  if (end <= start) return frame >= end ? 1 : 0;
  return clamp01((frame - start) / (end - start));
}

/**
 * Evaluate a limited-animation pose clip from a random-access local frame.
 *
 * A clip intentionally uses a small number of authored states instead of
 * synthesizing full frame-by-frame motion:
 * anticipation -> action -> hold -> settle.
 */
export function evaluatePoseClip(frame, clip) {
  if (!clip) return null;
  const start = clip.start_frame ?? 0;
  const anticipationEnd = clip.anticipation_end_frame ?? start;
  const actionEnd = clip.action_end_frame ?? anticipationEnd;
  const holdEnd = clip.hold_end_frame ?? actionEnd;
  const end = clip.end_frame ?? holdEnd;

  if (frame < start || frame >= end) return null;

  let phase = 'settle';
  let progress = 1;
  if (frame < anticipationEnd) {
    phase = 'anticipation';
    progress = easeInOut(phaseProgress(frame, start, anticipationEnd));
  } else if (frame < actionEnd) {
    phase = 'action';
    progress = easeInOut(phaseProgress(frame, anticipationEnd, actionEnd));
  } else if (frame < holdEnd) {
    phase = 'hold';
    progress = 1;
  } else {
    phase = 'settle';
    progress = 1 - easeInOut(phaseProgress(frame, holdEnd, end));
  }

  const useActionPose = phase === 'action' || phase === 'hold';
  const pose = useActionPose
    ? (clip.action_pose ?? clip.base_pose)
    : (clip.base_pose ?? clip.action_pose);

  const squash = clip.squash_stretch ?? {};
  const amount = phase === 'action' ? progress : phase === 'settle' ? progress : 0;

  return Object.freeze({
    clipId: clip.clip_id ?? null,
    phase,
    progress,
    pose,
    smear: Boolean(clip.smear && phase === 'action'),
    root: Object.freeze({
      scaleX: 1 + (squash.x ?? 0) * amount,
      scaleY: 1 + (squash.y ?? 0) * amount,
      rotation: (clip.rotation_deg ?? 0) * amount,
      x: (clip.translate?.x ?? 0) * amount,
      y: (clip.translate?.y ?? 0) * amount,
    }),
  });
}

/** Resolve the highest-priority active pose clip. Later clips win. */
export function evaluatePoseTrack(frame, clips = []) {
  let state = null;
  for (const clip of clips) {
    const current = evaluatePoseClip(frame, clip);
    if (current) state = current;
  }
  return state;
}
