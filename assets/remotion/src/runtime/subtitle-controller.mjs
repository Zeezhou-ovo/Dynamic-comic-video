/** Absolute local frame selection. Active speech always wins over a held cue. */
export function selectSubtitleCue(cues = [], frame, holdFrames = 0) {
  const active = cues.find(cue => frame >= cue.start_frame && frame < cue.end_frame);
  if (active) return active;
  return [...cues].reverse().find(cue => frame >= cue.end_frame && frame < cue.end_frame + holdFrames) ?? null;
}
