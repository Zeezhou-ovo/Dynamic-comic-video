# 漫画表演运行时（嘴型、表情、道具运动、音效、特效）

本文件说明 `motion_plan`（0.3 与 0.4 均可）中与固定机位表演相关的可选字段，以及 Remotion 渲染器如何执行它们。字段全部可选，旧项目不受影响。三档嘴型、表情替换、音效文件和漫画符号移植自此前本地升级版的字段定义，原样兼容；道具运动、`attach_to` 和 `audio_bed` 为新增字段。

## 默认原则

漫画符号（汗滴、无语竖线、问号等）、关键词彩色字幕和屏幕震动**默认不加**。只有用户明确要求，或项目 brief 里写明要这种效果时，才写入 `visual_events`。加了之后要确认效果按时出现、按时消失，并且不和人物表演抢同一个视觉重点（见 [漫画演出](comic-performance.md)）。字幕默认白字黑描边。

## 嘴型

`acting.speech.shape_assets` 可提供 `small`、`round`、`wide` 三种额外嘴型，图片与 master 同画布、同坐标。prepare 用实际 WAV 计算每帧音量，写入 `mouth_shape_frames`（`closed / small / open / wide`）；渲染器按帧选图，缺少的形状退回 `open_asset`。这是音量驱动，不是音素口型。需要手工指定时，在 `timeline.mouth_events` 写 `{speaker, shape, start_frame, end_frame, source: "authored"}`，它覆盖自动结果。

## 表情替换

`timeline.expression_events` 中带 `layer_id` 与 `pose_asset` 的事件，会在 `[start_frame, end_frame)` 内把该层换成指定姿态图（例如惊讶眉眼）。目标层不能是背景或嘴部层。

## 道具运动与附着层

适用于刚体道具连同骑在上面的人，例如摇木马、转椅、晃动的门。要求：

- 道具层是从当镜 master 抠出的**透明全画布图层**，与 master 同坐标；
- 它下面必须有一张不带 `region` 的全画布底图，并且道具后方的背景已经补全（摇动时会露出）；
- 人物在道具上的嘴、眼等局部补丁写 `attach_to: "<道具层 id>"`，z 值高于道具层，这样会跟着一起动。

```json
{
  "layer_id": "capy_horse", "asset": "layers/shot_003_capy_horse.png", "z": 20,
  "from": {"x": 0, "y": 0, "scale": 1}, "to": {"x": 0, "y": 0, "scale": 1},
  "prop_motion": {
    "pivot": [0.742, 0.922], "roll_radius": 160,
    "events": [
      {"event_id": "reveal_rock", "trigger": "information", "kind": "rock", "start_frame": 0, "end_frame": 64,
       "amplitude_deg": 3, "period_frames": 22, "decay_frames": 24, "description": "切入时正在摇，逐渐停下"},
      {"event_id": "dismount_lean", "trigger": "speech", "kind": "lean", "start_frame": 78, "end_frame": 107,
       "amplitude_deg": 1.8, "description": "说下马时前倾再回落"}
    ]
  }
}
```

`pivot` 是道具与地面的接触点（画布归一化坐标）。`amplitude_deg` 为正表示道具顶部往画面左侧倾（逆时针），范围 ±8°。`rock` 从满幅开始、按 `period_frames` 来回、按 `decay_frames` 衰减，并在事件结束前平滑回到 0；必须同时给出两个参数，避免变成无限循环。`lean` 是一次倾斜再回正。`roll_radius`（像素）让道具随角度在地面上滚动，0 表示原地绕点转。道具运动不能替代人物表演，也不能用来给整张图做摇晃。

## 音效与环境声

`timeline.sound_events` 中带 `asset`（16-bit PCM WAV）的事件会在 `start_frame` 播放，`volume` 为 0–1，`source_start_frame` 可从素材中间开始。顶层 `audio_bed: {asset, volume}` 在全片底下循环播放一层底噪或音乐，建议 0.1–0.2。`python scripts/make_sfx.py <project>` 会在 `audio/sfx/` 生成原创的木头吱呀声、室内底噪和轻弹音，没有版权问题。

`preview.py` 渲染后默认把整体响度用固定增益调到约 −14 LUFS（带峰值限制），不改变对白、底噪和音效之间的比例；`--keep-loudness` 可跳过。`deliver.py` 会在报告里给出实测响度。

## 漫画符号、震动与关键词

`visual_events` 可用 `position`（归一化中心点）、`size`（占画面高度的比例，默认 0.13）、`intensity`（0–1，影响透明度）和 `color`。已绘制的类型：`sweat_drop`、`black_line`、`vein`、`sparkle`、`question`、`exclamation`、`ellipsis`、`shock_lines`、`speed_lines`、`focus_lines`、`flash`、`background_tint`。`screen_shake` 让画面短暂水平震动后归零；`subtitle_emphasis` 配合 `keyword`，在事件时间内把当前字幕里的该词换成 `color`（默认暖黄）。其余类型在合同中保留，但渲染器暂不绘制。

## 验收

`scripts/make_performance_fixture.py` 生成一个覆盖以上全部字段的合成项目，CI 会把它真实渲染成 MP4。正式项目仍需查看道具摇到两端时露出的背景、附着层有没有错位、符号是否按时消失。
