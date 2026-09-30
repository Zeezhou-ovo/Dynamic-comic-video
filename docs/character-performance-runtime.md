# Character Performance Runtime (motion plan 0.4)

Character performance is evaluated from a shot's local frame on every render. It does not depend on the previous frame, playback order, or random state.

## Capability manifest

Each character may declare the rendered parts and state assets available to its art:

```json
{
  "capabilities": {
    "parts": ["body", "head", "eyes", "mouth", "left_arm", "right_arm"],
    "poses": ["point"],
    "expressions": ["happy", "surprised"]
  }
}
```

Parts are the intersection of this manifest and the storyboard/rendered layers. Pose and expression names must also resolve to a layer's `state_assets` entry.

## Shot plan

`character_performance` is optional on a motion plan 0.4 shot. One record describes one visible character:

```json
{
  "character_id": "lin",
  "role": "speaker",
  "root_pivot": [0.32, 0.5],
  "root_easing": "easeInOut",
  "root_keys": [
    {"frame": 0, "x": 0, "y": 0, "scale": 1, "rotation": 0, "opacity": 1},
    {"frame": 47, "x": 12, "y": -2, "scale": 1.02, "rotation": 0, "opacity": 1}
  ],
  "events": [
    {"event_id": "notice", "preset": "nod", "start_frame": 10, "peak_frame": 16, "settle_frame": 24, "end_frame": 32}
  ]
}
```

Event frames are local to the shot. Supported presets: `idle`, `talk`, `nod`, `shake_head`, `point`, `raise_hand`, `blink`, and `small_bounce`. Events use a prepare-to-peak hold-to-settle envelope. Character-level `pose` and `expression` names map to `pose:<name>` and `expression:<name>` keys on the appropriate part layer.

Layer-level `acting.keys` remain supported for 0.3/0.4 plans. They interpolate a part's local `x`, `y`, `rotation`, `scale`, and `opacity`, then combine with the matching generated performance motion.

## Runtime order

For each absolute render frame, Remotion locates the active shot and supplies its local frame. The runtime evaluates, in order:

1. Character root keyframes and deterministic procedural motion.
2. Part keyframes plus event motion in the character-local coordinate space.
3. Mapped expression, pose, eye, and mouth assets.
4. Root transform around `root_pivot`.
5. The shot Camera transform and the layer's Parallax depth transform.

The rendered transform chain is `part-local → character-root → camera/depth → viewport`. Camera and parallax remain active when character performance is present.

## Mouth behavior

Existing `dialogue[].mouth_open_frames` timing selects `open` or `closed` state assets. This preserves the current amplitude-timed mouth animation and is intentionally not phoneme lip sync. If no measured mouth frames exist, the `talk` preset uses a stable frame-based open/closed cycle.

## Determinism

Idle phase is derived from a stable hash of the character ID. All action envelopes, body sway, blink windows, and talk timing are functions of the local frame and declared shot data. Random seek and sequential rendering therefore produce identical output for the same frame.

## Current scope

This runtime is a 2D part-transform and mapped-state layer. It does not implement skeletons, IK, authored walk/run cycles, phoneme lip sync, or automatic reaction direction.
