# 逐帧动画路线

当项目能用代码根据任意时间点重绘完整画面时，采用 `procedural-frame` 路线。此路线允许镜头移动、连续角色动作和手绘线条抖动；默认用动作与空间位置衔接的直接剪接，只有剧情需要时才设计特殊转场。固定机位是图层动态漫画路线的制作约束，在这里不适用。

当前实现使用独立的 p5.js/p5.brush 动画项目作为渲染后端；可从仓库中的 [`examples/procedural-yaya`](../examples/procedural-yaya/README.md) 开始。实际用户项目仍放在仓库之外，包含：

- `production/plan.json`：情节节拍、角色身份锚点、场景锚点、镜头帧数、事件、反应、观众阅读时间和转场。
- `scripts/production.mjs`：检查节拍覆盖、时间连续、转场衔接，生成逐镜检查图和源文件指纹。
- `scripts/render-local.sh`：以时间函数绘制每一帧，并调用 ffmpeg 输出 MP4。
- `src/`：具体人物、背景、镜头与动作的程序绘制代码。

从本仓库调用：

```bash
python scripts/procedural.py inspect /absolute/path/to/p5-project
python scripts/procedural.py check /absolute/path/to/p5-project
python scripts/procedural.py sheets /absolute/path/to/p5-project
python scripts/procedural.py approve /absolute/path/to/p5-project --shot A --note "已查看角色、动作、接触和转场"
python scripts/procedural.py render /absolute/path/to/p5-project --out out/video.mp4
python scripts/procedural.py render /absolute/path/to/p5-project --shot C
```

`render --shot C` 从计划中的帧数推导范围，输出 `out/preview_C.mp4`，用于单镜头返工。

制作顺序：内容策略与故事 → Narrative Beats → 镜头、观众阅读时间与角色身份 → 人物/场景绘制 → 逐镜图与动作逐帧图 → 实际视觉复核 → MP4。`inspect` 只读，不把文件存在当成质量通过。更改 `plan.json` 或声明的角色、场景源码后，旧检查图的指纹失效；重新运行 `sheets` 再复核。

此路线目前是 p5 项目的桥接入口，不是现有四份 JSON 合同的新版本。原来的 `pipeline.py`、`quality_gate.py` 和 `deliver.py` 仍服务于 master/PNG 图层/Remotion 路线；不要拿 p5 项目伪造图层资料去通过这些检查。若将来合并合同，应显式增加模式判别和版本迁移，逐项更新 Schema、校验器、预览、交付和文档。

逐帧在这里指**每一帧由确定性的绘图代码生成**，可以乱序渲染和局部返工；不表示逐帧调用图像模型。正式画质仍需检查角色身份、动作弧线、接触、遮挡、镜头衔接和观看节奏。对白项目以实测音频建立统一帧时间轴；当前桥接未自动生成配音、字幕或口型。
