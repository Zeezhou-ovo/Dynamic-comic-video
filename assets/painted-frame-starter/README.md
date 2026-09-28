# Painted frame starter

Copy this directory **outside** the Skill repository for each new video. Replace the sample `drawWorld(t)` in `scene.js` with the project’s characters, setting, props, and time based actions. Keep the drawing reproducible from absolute time.

Copy `plan.example.json` to `plan.json` and adapt every scene before rendering. The renderer checks the plan before creating stills, frames or MP4; missing fields, insufficient camera motion without a stated reason, and moving cameras without required parallax stop the run. The plan must match `scene.js`'s `VIDEO` size, fps and duration. The renderer validates intent but cannot prove the drawn pixels follow it, so review moving previews and scene boundaries.

```sh
npm install
npx playwright install chromium
cp plan.example.json plan.json
npm run stills
npm run frames
npm run encode
```

`node render.mjs --encode --audio=assets/audio.wav` adds an authorized soundtrack. Pass `--chrome=/path/to/chrome` or set `CHROME_PATH` when using an existing Chrome installation. Frames are PNG files; the output MP4 uses H.264 and optional AAC audio.

The starter draws a simple moving light only. It is an executable scaffold, not a finished animation or a quality reference. See `references/painted-frame.md` in the Skill for the creative and visual review requirements.
