// config.js: project settings.
//   duration: the video's length in seconds.
//   bpm:      the rhythm that bounces, dances and pulse() follow. Clawd always moves to some beat; if the video has music,
//             set this to the song's tempo, and set offset to the time in seconds of its first downbeat.
const PROJECT = { duration: SHOT_PLAN.duration_frames / SHOT_PLAN.fps, bpm: 120, offset: 0 };
