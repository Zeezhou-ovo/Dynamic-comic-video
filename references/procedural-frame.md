# Procedural frame route

这是参考 PDoomVideo 类视频的生产合同：故事、角色、背景、镜头和笔触都在同一个 p5.js/p5.brush 绘制程序中生成，每一帧由绝对时间重建，不用图片切换假装连续动画。

## 项目结构

```text
production/plan.json
src/studio.html
src/scene.js
scripts/procedural.py
out/frames/
out/video.mp4
```

`plan.json` 至少包含 `fps`、`duration`、`width`、`height` 和 `shots`。每个 shot 写明 `start`、`end`、`action`、`camera` 与可选的 `beatEvents`。新项目设置 `planVersion: 2`，逐镜增加 [导演卡](shot-direction.md) 的叙事目的、视觉焦点、运动主次、空间、光、停顿和转场。`scripts/procedural.py` 对 v2 检查这些字段；旧计划仍可按原有字段读取。音乐节拍可以来自人工标记；没有可靠节拍时，必须标记为草拟时间轴。

## 绘制规则

- `renderAt(t)` 必须能在任意顺序调用，并由 `t` 决定整张画面。
- 背景、角色、道具、阴影和光效在同一坐标系中绘制，共享脚底、手部和接触点。
- 动作按准备、加速、峰值、回落、停顿拆成函数；镜头移动和角色位移使用连续 easing。
- 只让笔触 boil 使用离散随机种子，例如 `floor(t * boilFps)`；不要累积上一帧状态。
- 音乐事件只触发可见变化：步伐、转身、抬手、灯光闪动或镜头切换，不要每一拍都抖动全画面。
- 将镜头位置、视差、角色姿势、环境和光照做成可随机访问的时间函数；所有层级在同一世界坐标中绘制，避免以独立图片平移代替演出。镜头移动时按深度调整位移，静止时保持空间稳定。
- 对发光道具绘制附近地面、角色和环境的光照反馈；对拾取和种下等动作明确手与物体、物体与地面的接触帧。

## 推荐命令

```bash
python3 scripts/procedural.py validate production/plan.json
node assets/painted-frame-starter/render.mjs --stills=0,1,2
node assets/painted-frame-starter/render.mjs --frames --workers=2
node assets/painted-frame-starter/render.mjs --encode --audio=assets/song.wav --out=out/video.mp4
```

截帧前至少检查动作准备、接触、峰值、回稳和每个切点两侧；交付前检查实际时长、帧数、音轨和代表性中间帧。
