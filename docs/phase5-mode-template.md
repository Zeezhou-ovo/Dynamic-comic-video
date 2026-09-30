# Phase 5: Mode + Template

The executable boundary is:

`dialogue_script + production_profile → Mode Resolver → Director Plan → Phase 3 compiler → Phase 4 Composition Resolver → Camera / Parallax / Character Runtime → Remotion`

Templates are loaded before directing. They supply Scene and Character Asset Manifests, capability manifests, slots, default bindings, props and composition suggestions. Modes contain no asset paths. Core contains no Mode ID or Template ID branches. Renderer receives numeric camera targets, scene graph, performance contexts and generic subtitle presentation, never chooses shots.

## Inputs

- `dialogue_script.json`: version, project_id, optional required_props, authored beats (speaker, text, semantic intent, emphasis and optional reaction hint). No automatic writing or fact generation.
- `production_profile.json`: version, mode_id, template_id, scene_id, optional overrides.
- `modes/*.json`: version, mode_id, description, policy and requirements.
- `templates/*/template.json`: version, template_id, description, base_project, default_scene, scenes map and optional metadata. Each scene declares three manifests, default bindings, available props and shot suggestions.

The four JSON Schemas reject unknown properties. Override leaves use the same ranges/enums as the complete Mode policy; IDs, assets and compatibility requirements cannot be overridden.

## Policy parameters

| Section | Executable parameters |
| --- | --- |
| shot | max_dialogue_beats, normal_intents cycle, emphasis_intent |
| reaction | every_n_beats (0 disables), strength, hold_frames, closeup |
| camera | normal and emphasis camera intent, motion_every_n_shots (0 disables normal moves), strength 0–2 |
| timing | line_pause_frames, emphasis_pause_before/after, reading_frames_per_character, minimum_line_frames |
| performance | explain_gesture, event_strength 0–2 |
| parallax | enabled, strength 0.1–1 |
| subtitle | font_height_ratio, emphasis_scale, hold_frames |

Selection and beat grouping are deterministic. Reaction hints are authored semantics, then Mode selects cadence, hold, strength and framing. Multiple speakers in one group retain a two-shot. A non-normal emphasis starts its own shot. Camera strength scales the resolved zoom delta; zero makes the camera static. Explicit static-only policies suppress legacy camera promotion. Parallax strengths interpolate depth factors toward 1, preserving the Character factor at 1; the same factors are used for safe composition and runtime transforms. Moving multilayer cameras require enabled parallax.

Performance intensity scales event amplitude, including the point/raise-hand rotation. Existing mouth/audio behavior and legacy default amplitudes are preserved. Subtitle presentation is generic numeric data; font and hold behavior have no Mode-name branching. Holds are bounded by the next dialogue cue and shot boundary.

## APIs

- `resolve_mode(mode_id, overrides=None) → validated Mode Manifest`
- `direct_with_mode(script, mode, source_shot_ids, visible_characters) → Director Plan`
- `plan_metrics(plan) → comparative directing metrics`
- `load_template(template_id, scene_id=None) → manifest, selected entry, scene, character_assets, capabilities, asset base`
- `instantiate_template(template_id, project, mode_id, scene_id=None, overrides=None) → self-contained project`
- `check_compatibility(profile, script, …) → resolved Mode or early ValueError`
- `resolve_project_mode(project, data) → authoritative Director Plan`
- `compose_project(project, script, mode, template, scene=None, overrides=None) → validated project`

`pipeline validate/prepare` always resolve current profile and content when a profile exists. A stale saved Director Plan cannot override them. `prepare` saves the generated plan for inspection. Projects without a profile keep their existing Phase 1–4 behavior.

## Use

```sh
python3 scripts/compose_project.py out/my-project \
  --content my-dialogue.json --mode dialogue-comedy --template generic-room
python3 scripts/pipeline.py prepare out/my-project --renderer out/my-renderer
```

A new project directory is required. For another mode on the same loaded assets, change `production_profile.mode_id` and run prepare again. For another template, create a new project with the desired template. A Template can declare multiple scenes; selection is explicit at project creation. Per-shot scene switching is not implemented in this phase.

Reproduce comparison fixtures with `scripts/make_phase5_fixture.py` and options `--mode` / `--template`. Actual output files are local and ignored by Git.

## Modes

- dialogue-comedy: two-beat grouping, reaction hints every two beats, 22-frame reaction holds, closeups, stronger emphasis camera, 18/30-frame emphasis pause, full event strength.
- knowledge-explainer: three-beat grouping, stable shared framing, no scheduled reaction cuts, 0.25 camera strength, 0.55 gesture strength, readable subtitles, 5/10-frame emphasis pause.
- motion-comic: limited grouped acting, static camera, no parallax, 0.35 event strength, occasional authored closeups without camera motion.
- story-animation: restrained push camera, full depth separation, 0.85 event strength, emphasis push, 10/16-frame pause, no comedy reaction cadence. It is a minimal directing policy, not a walking/action system.

## Reusable test-art assets

`templates/_shared/base` contains deterministic synthetic layered PNGs and existing source-panel contracts. `generic-room` binds Lin and Bo around a reading-room table, with a book insert anchor. `generic-outdoor` changes scene art, relative slot positions, character scales, composition center and lantern prop/anchor. Their Character Asset/Capability Manifests remain shared. Test art demonstrates infrastructure; it is not finished production art.

Phase 5 previews are silent with subtitles. Existing supplied dialogue audio is carried through the Phase 3 compiler. Automatic speech generation and music selection are outside this phase.
