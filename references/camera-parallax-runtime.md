# Camera 与 Parallax 运行时（motion_plan 0.4）

0.4 在原有 Storyboard → Motion Plan → Remotion → MP4 链路中加入可执行相机。旧 0.1–0.3 项目仍按原合同运行；`sequential-comic` 未显式提供 `camera` 时保持固定构图。此模块只处理 Camera、ShotContext 和 2.5D depth，不提供角色骨骼或自动表演。

## 数据

每镜仍用 `start_frame` 与 `duration_frames` 定义半开区间 `[start_frame, start_frame + duration_frames)`。0.4 每层必须写 `depth`，取 `foreground`、`character`、`midground`、`background`、`sky` 之一。整层 `from`/`to` 均为 `{"x":0,"y":0,"scale":1}`；局部部件动作继续使用原有 `acting`。

```json
{
  "shot_id": "shot_002",
  "start_frame": 48,
  "duration_frames": 48,
  "camera": {
    "type": "push_in",
    "focus_target": {"id": "subject", "x": 500, "y": 335},
    "from": {"x": 500, "y": 335, "zoom": 1},
    "to": {"x": 500, "y": 335, "zoom": 1.45},
    "screen_target": {"x": 0.5, "y": 0.62},
    "easing": "easeInOut",
    "parallax_enabled": true
  }
}
```

`from`/`to` 是世界坐标中的相机中心与倍率；`focus_target` 是相机运动及各 depth 计算的共同参考点，`screen_target` 是该参考点在画面中的归一化位置。`follow` 另需 `follow_path`，每个点写 `{frame,x,y}`，frame 为镜内帧，起点 0、终点 `duration_frames-1`，中间点严格递增。类型包括 `static`、`push_in`、`pull_out`、`pan_left`、`pan_right`、`follow`；easing 为 `linear`、`easeIn`、`easeOut`、`easeInOut`，默认 `easeInOut`。

## 执行

Remotion 的 `Sequence` 用绝对帧选中 shot，并把局部帧交给 `createShotContext`。Context 包含 `shotId`、`startFrame`、`endFrame`、`durationFrames`、`localFrame`、`absoluteFrame`、`progress`、viewport 与归一化 camera。`evaluateCamera(localFrame, context)` 从该帧直接计算位置、zoom 与 easedProgress；不使用上一帧状态。`evaluateLayerTransform(cameraState, depth, viewport)` 为每层生成同一 Camera State 的世界到屏幕矩阵。

默认 depth 强度为 foreground 1.2、character 1、midground 0.55、background 0.2、sky 0.05；镜头可用 `parallax_strengths` 覆盖。Camera 位移和倍率都按 depth 强度响应，形成近快远慢。关闭 Parallax 时全部 depth 的 Camera 响应相同。字幕、音频与测试标记在相机世界之外。

平移与拉远会暴露源图边缘；镜头设计时需要为所有可见层准备足够画面覆盖，或采用足够的起始倍率。现阶段校验检查合同和数值关系，画面边缘、图层接缝、遮挡仍需通过首/中/末帧及连续播放人工复核。

## 校验与复现

`pipeline.py validate` 检查 0.4 的 depth、镜头类型/方向、focus/from/to、follow 路径、parallax 与图层互斥；旧版本不能混入新字段。镜头随机访问与跨镜边界的纯函数测试位于 `scripts/test_camera_runtime.mjs`，跨合同测试位于 `scripts/test_camera_plan.py`。`scripts/make_camera_parallax_fixture.py <project>` 生成三个镜头、五层的合成测试项目；通过 `pipeline.py prepare` 后使用 Remotion 渲染。测试项目是技术素材，画面中的角色保持静止，以便单独观察 Camera 和 depth。
