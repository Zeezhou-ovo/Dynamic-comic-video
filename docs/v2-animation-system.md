# V2 Animation System

V2 的目标不是传统逐帧动画，而是把 V1 的动态漫画能力升级为可复用的 **limited animation engine**。

## 设计原则

V2 继续复用 V1 已有的 Camera、Character、Performance、Scene Graph 与音频时间轴，不破坏现有 motion_plan 0.4 项目。

新增四个明确层次：

1. **Character System**：沿用 `character-controller.mjs`，负责角色根节点、局部部件、嘴型、表情和角色能力。
2. **Pose System**：新增 `pose-controller.mjs`，负责少量关键姿势组成的 anticipation → action → hold → settle 动作。
3. **Camera System**：沿用 `camera-controller.mjs`，负责 push/pull/pan/follow 和 2.5D parallax。
4. **Effect System**：新增 `effect-controller.mjs`，统一 screen shake、flash、speed/focus/shock lines、radial burst 等夸张演出。

## 为什么使用有限动画

目标是获得“像逐帧动画”的观看体验，而不是逐帧生产成本。

一个跑动动作可以只需要：

- base pose
- anticipation pose
- action pose
- smear / motion blur
- settle

程序负责时间、位移、squash/stretch、镜头和效果；角色资产负责真正的姿势差异。

## 第一阶段数据

新增可选 `animation_system.json`，合同版本 0.1。它只描述 V2 的 pose clips 与 effects，暂不替代 `motion_plan.json`。

示例：

```json
{
  "version": "0.1",
  "project_id": "demo",
  "shots": [
    {
      "shot_id": "shot_001",
      "characters": [
        {
          "character_id": "zhouye",
          "pose_clips": [
            {
              "clip_id": "dash",
              "start_frame": 10,
              "anticipation_end_frame": 13,
              "action_end_frame": 18,
              "hold_end_frame": 24,
              "end_frame": 30,
              "base_pose": "idle",
              "action_pose": "dash",
              "smear": true,
              "translate": {"x": -160, "y": 0},
              "squash_stretch": {"x": 0.18, "y": -0.12}
            }
          ]
        }
      ],
      "effects": [
        {
          "event_id": "dash_lines",
          "effect_type": "speed_lines",
          "start_frame": 13,
          "end_frame": 20,
          "intensity": 0.9
        }
      ]
    }
  ]
}
```

## V2 里程碑

### M1 — Runtime foundation

- [x] Character System（复用 V1）
- [x] Camera System（复用 V1）
- [x] Pose System 基础运行时
- [x] Effect System 基础运行时
- [x] animation_system 0.1 Schema
- [x] Python contract/render-payload tests and Node deterministic runtime tests pass in [Run #105](https://github.com/Zeezhou-ovo/Dynamic-comic-video/actions/runs/38039148329)
- [x] renderer integration (Scene Graph + legacy Layer renderer)

### M1.5 — V2 technical fixture

The synthetic V2 action fixture from `scripts/make_v2_animation_fixture.py` exercises anticipation, dash pose, translation, squash/stretch, rotation, speed lines, radial burst, screen shake, flash, camera push-in, four mouth shapes, and three eye states.

- [x] CI validates the fixture with `validate --assets` and prepares the V2 renderer.
- [x] Remotion renders the V2 fixture and uploads `v2-limited-animation-video-fixture`.
- [x] [Run #105](https://github.com/Zeezhou-ovo/Dynamic-comic-video/actions/runs/38039148329) passed the initial end-to-end pipeline.
- [x] [Run #106](https://github.com/Zeezhou-ovo/Dynamic-comic-video/actions/runs/38039480954) passed after the status documentation update; its V2 artifact was 691,422 bytes.
- [x] [Run #108](https://github.com/Zeezhou-ovo/Dynamic-comic-video/actions/runs/38040285417) passed validation, Python/Node checks, prepare, all fixture renders, and artifact uploads. The V2 artifact is ID `11665144790` (651,600 bytes).
- [x] [Run #112](https://github.com/Zeezhou-ovo/Dynamic-comic-video/actions/runs/38041893306) passed Python/Node checks, fixture validation, renderer preparation, the V2 Remotion render, and all other fixture jobs. The V2 artifact is ID `11665369145` (654,973 bytes); its fixture exercises the authored mouth/eye states.
- [x] [Run #113](https://github.com/Zeezhou-ovo/Dynamic-comic-video/actions/runs/38042291297) passed `validate`, Python/Node checks, renderer preparation, all fixture renders, and artifact uploads. The V2 artifact is ID `11665379592` (655,906 bytes).
- [x] Visual review of Run #108 checked anticipation, dash, effect timing, camera framing, and canvas coverage. The radial burst is now masked to its authored local size; the character action remains readable.

Run #103 exposed an animation-test fixture mismatch: the camera-only fixture contained no characters. Run #104 exposed a camera framing issue that could reveal the background edge. Both were fixed. Visual review of the earlier artifact also found that radial burst filled the whole frame; the effect is now bounded around its authored center.

These assets are synthetic and labeled as a pipeline fixture. The visual review confirms runtime/effect behavior only; it does not approve production character art or identity consistency.

### M2 — Character Asset Standard (in progress)

The user-uploaded seven-character reference set is stored in the private [media asset library](https://github.com/Zeezhou-ovo/media-asset-library/tree/main/characters/journalism-communication-main-cast). Each character now has a neutral four-pose reference sheet: standing, walking, pointing, and arms crossed. The sheets use the uploaded manga style and keep the same neutral face across poses. Expression variants are intentionally deferred. These are pose references, not separated, transparent rig parts.

**Pilot:** 唐可可 / `character-cardigan-girl-001` from the user-provided cast. Use her uploaded reference and pose sheet to validate the actual identity and rig contract. The synthetic `lin` / 林岚 example remains a runtime fixture only and is not production character art.

**Current approved art scope**

- Poses: `idle`, `walk`, `point`, `arms_crossed`, all with a neutral face.
- Expression, mouth, eye, and smear art: deferred; do not add these variants to the current art pack.

**Identity and rig contract**

- Keep the uploaded character reference as the source of truth for front, three-quarter, and profile views. Record 3–5 stable visual anchors for face, hair, clothing, proportions, and distinctive features.
- Use the existing `characters.json` identity/capability fields and `character_assets.schema.json` manifest. Declare one `reference_size`, `root_anchor`, required root/body/face anchors, optional head/eyes/mouth/hand anchors, and normalized bounds in the `normalized-0-to-1` coordinate system.
- Start with separate `body`, `head`, `eyes`, `mouth`, `left_arm`, and `right_arm` parts. Add hair as a separate part only when a shot needs it to move independently.
- Use transparent PNG or WebP part assets. Keep each part's pixel size, anchor, pivot, and transparent padding consistent across its state variants. Do not bake in a background, ground shadow, or other character parts.
- Keep all asset references relative to the project root and use `state_assets` for named variants. Use `pose:<name>` variants on the body and affected limbs; keep future expression variants on face parts so pose and expression can combine.

**Runtime capability, future art assets**

The runtime maps `mouth_shape_frames` from WAV analysis or authored storyboard cues to `closed`, `small`, `open`, and `wide` mouth assets (`round` remains supported). Eye layers default to `open`; a blink event passes through `half` and `closed` states, with a fallback for legacy `blink` assets. Deterministic Node checks and the V2 fixture render cover these mappings. This confirms runtime support only; no mouth or eye variants are included in the current production art.

**Pilot acceptance**

1. The four neutral poses align to the same declared rig, with no visible seams, drift, or accidental cropping.
2. The identity anchors remain recognizable across the uploaded reference and four pose states.
3. The manifest validates, every referenced asset exists, and a representative Remotion render has been visually reviewed.
4. Set `characters[].reference.status` to `ready` only after the pilot rig and render are reviewed.

M2 remains in progress until the pilot character is rigged and its representative render passes this checklist.

### M3 — Animation Director

把剧本/导演意图转换为：

`dialogue beat → pose clip → camera motion → effect event → audio/subtitle timing`

Director 只生成结构化事件，Renderer 不写剧情判断。

### M4 — Reference-video complexity target

V2 第一阶段以短视频 limited animation 为上限：

- 多 pose 切换
- 快速 push-in / reaction close-up
- squash/stretch
- smear frame
- screen shake
- radial burst / speed lines
- 嘴型、眨眼、表情替换

复杂连续转身、完整骨骼动画和高帧率逐帧人体表演不作为 V2 自动化目标。
