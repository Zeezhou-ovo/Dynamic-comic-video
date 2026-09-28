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

`plan.json` 至少包含 `fps`、`duration`、`width`、`height` 和 `shots`。每个 shot 写明 `start`、`end`、`action`、`camera` 与可选的 `beatEvents`。音乐节拍可以来自人工标记；没有可靠节拍时，必须标记为草拟时间轴。

## 绘制规则

- `renderAt(t)` 必须能在任意顺序调用，并由 `t` 决定整张画面。
- 背景、角色、道具、阴影和光效在同一坐标系中绘制，共享脚底、手部和接触点。
- 动作按准备、加速、峰值、回落、停顿拆成函数；镜头移动和角色位移使用连续 easing。
- 只让笔触 boil 使用离散随机种子，例如 `floor(t * boilFps)`；不要累积上一帧状态。
- 音乐事件只触发可见变化：步伐、转身、抬手、灯光闪动或镜头切换，不要每一拍都抖动全画面。

## 推荐命令

```bash
python3 scripts/procedural.py validate production/plan.json
node assets/painted-frame-starter/render.mjs --stills=0,1,2
node assets/painted-frame-starter/render.mjs --frames --workers=2
node assets/painted-frame-starter/render.mjs --encode --audio=assets/song.wav --out=out/video.mp4
```

截帧前至少检查动作准备、接触、峰值、回稳和每个切点两侧；交付前检查实际时长、帧数、音轨和代表性中间帧。
