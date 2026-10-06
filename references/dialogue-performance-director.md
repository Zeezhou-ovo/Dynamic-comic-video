# Dialogue & Performance Director 0.1

`director_plan.json` is an optional semantic directing contract for a motion plan
0.4 project. Projects without it keep their existing storyboard/motion-plan
timeline. When it is present, its ordered `shots` and `beats` are the authoritative
playback timeline; each entry points to a drawn source shot with
`source_shot_id`, so a reaction can reuse an existing character composition
without requiring dialogue in that reaction.

## Pipeline

```text
director_plan.json
  → parse dialogue/reaction/pause beats
  → resolve shot, camera, character and emphasis intents
  → compile absolute start_frame and duration_frames
  → Phase 1 Camera/Parallax + Phase 2 Character Performance
  → Remotion renderer
```

`schemas/director_plan.schema.json` defines the 0.1 contract. The plan stores
semantic information: speaker, text, listeners, emotion, emphasis, reaction,
reaction strength, performance intent, and pause lengths. `config/director_rules.json`
holds the mappings used by `scripts/director.py`. The resolver chooses framing
and builds the existing 0.4 camera plan. The renderer only evaluates the
compiled camera, character, subtitle and audio data.

## Timing

Every beat is evaluated in the authored array order. `pause_before`,
`pause_after`, reaction hold, and pause-only beats add real frames to the shot's
duration. The compiler then lays shots contiguously from absolute frame zero.
Dialogue cues occupy only their speech frames; a trailing hold remains a silent
interval inside the same directed shot. If a matching storyboard cue has local
WAV audio, measured WAV duration sets that cue's frame span; otherwise
`duration_frames` is used. The compiled director timeline is checked against
the audio and existing runtimes before renderer preparation.

## Example

```json
{
  "version": "0.1",
  "project_id": "my-dialogue-project",
  "timing_source": "director_plan",
  "shots": [{
    "instance_id": "listener-silence",
    "source_shot_id": "panel-03",
    "shot_intent": "listener_reaction",
    "camera_intent": "subtle_push",
    "focus_character": "student_b",
    "emphasis": "awkward",
    "beats": [{
      "beat_id": "reaction-01",
      "kind": "reaction",
      "reaction_target": "student_b",
      "reaction": "speechless",
      "reaction_strength": "medium",
      "reaction_hold": 18,
      "pause_before": 0,
      "pause_after": 8
    }]
  }]
}
```

## Reveal beats

A shot whose first beat is `{"kind": "reveal", "reveal_what": "..."}` pays off
the previous shot's last line with something the audience must *see*. The
compiler caps the previous shot's trailing pause at
`reveal.max_cut_delay_frames` (4) so the cut lands as the setup line ends, then
holds silently for `duration_frames` (default `reveal.default_hold_frames`, 14)
before the next beat. The compiled storyboard shot carries
`reveal: {what, hold_frames}`, so the quality gate checks the result. A reveal
must be the first beat of its shot and cannot open the first shot. For an
ending, finish with a `reaction` beat rather than a bare line.

Validate and prepare as usual:

```sh
python scripts/pipeline.py validate PROJECT
python scripts/pipeline.py prepare PROJECT --renderer RENDERER
```

Run `python scripts/make_director_fixtures.py comedy PATH` or `knowledge PATH`
to create the two small synthetic Phase 3 test projects. Their flat characters
and fixture watermark are runtime test assets, not final illustration quality.
