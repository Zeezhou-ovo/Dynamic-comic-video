# Painted frame starter

Copy this directory **outside** the Skill repository for each new video. Replace the sample `drawWorld(t)` in `scene.js` with the project’s characters, setting, props, and time based actions. Keep the drawing reproducible from absolute time.

Use `plan.example.json` as a director-card example and adapt it to the story before implementing shots. The plan documents intent and can be checked with `python3 <skill-directory>/scripts/procedural.py validate plan.example.json`; this minimal renderer does not automatically read the plan, so the scene code must implement its timing and direction.

```sh
npm install
npx playwright install chromium
npm run stills
npm run frames
npm run encode
```

`node render.mjs --encode --audio=assets/audio.wav` adds an authorized soundtrack. Pass `--chrome=/path/to/chrome` or set `CHROME_PATH` when using an existing Chrome installation. Frames are PNG files; the output MP4 uses H.264 and optional AAC audio.

The starter draws a simple moving light only. It is an executable scaffold, not a finished animation or a quality reference. See `references/painted-frame.md` in the Skill for the creative and visual review requirements.
