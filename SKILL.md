---
name: dynamic-comic-video
description: Create or revise hand-drawn dynamic-comic videos by drawing characters, scenes, props, and effects from code at each frame, then capturing frames in a headless browser and encoding an MP4. Use for 动态漫画、漫剧、code-painted animation, or requests referencing p5.js/p5.brush-style videos. Not for generic slideshows or phoneme-accurate lip sync.
---

# Dynamic Comic Video — code-painted workflow

本 Skill 的默认产物是**代码逐帧绘制的动态漫画视频**。角色、场景、道具与效果由同一绘制程序随时间生成；无头浏览器截帧，FFmpeg 合成成片。角色参考图只提供身份特征，不能用整张人物图平移、背景图切换或镜头推拉冒充角色与场景的绘制。原有 Remotion、master／对齐图层、四份 JSON 合同保留在仓库中作为旧项目资料，**不再作为新项目的默认流程**。

## 接单与创作

1. 读取用户故事、角色、参考和已有项目。保留原文的题材、关系、事实边界与情绪；信息足以制作时自行补齐普通创作选择。用户只请求分镜、角色设计或代码修改时，到该交付物完成为止。
2. 从故事提取 Narrative Beats，再确定镜头、时长、动作原因和声音。逐镜明确叙事目的、视觉焦点、主要动作、角色反应、镜头、空间、光源、停顿和转场；按 [镜头导演与表演](references/shot-direction.md) 取舍运动。参考图锁定发型、服装、比例、配色等辨识锚点，不锁姿势、表情或构图。参考视频用于学习笔触、节奏和运动规律，不挪用独有剧情、人物或素材。
3. 将角色设计转成可绘制的形状与运动参数。复杂照片或精细二次元角色可按目标画风简化，但需在预览和交付时说明简化程度；不能把风格化简笔角色说成高精度肖像复刻。
4. 在仓库外创建独立项目。可复制 `assets/painted-frame-starter/`，按 [代码逐帧绘制](references/painted-frame.md) 和 [逐帧生产合同](references/procedural-frame.md) 完成节拍时间轴、绘制、截帧、编码与复核。项目内保存源代码、角色参考、授权音频、关键帧和 MP4；私有内容不提交到 Skill 仓库。

## 绘制与动画约束

- 每镜实现 `drawWorld(t)` 或等价函数；角色与环境共用画布坐标、透视、调色板、线粗、纸纹和光向。绘制顺序应处理人物与前景的真实遮挡。
- 时间 `t` 是画面的唯一动画输入。人物位置、身体部件、道具和转场从绝对时间求值；同一个 `t` 可重复得到同一帧。手绘笔触可用离散随机种子产生轻微 boil，但不要让形体无因地抖动或全身循环漂浮。
- 每镜明确一个承担叙事的主要运动，次要运动通常不超过两项；环境运动保持低强度。动作须有准备、执行、接触或释放、停顿／回稳。对走路、拿取、抬手、视线、表情等动作检查中间帧；不能只检查首尾静帧。
- 人物脚底、手持物、投影、反光、光照和景深必须与场景关系一致。发现“贴上去”的图层感，先修共同坐标、透视与遮挡，再调整色彩或纹理。
- 音频决定最终字幕、嘴部动作与 CUT 的时间。没有对白不强加配音或嘴型；不要声称实现精确音素口型。

## 预览、渲染与交付

先渲染各动作的准备、峰值、接触／释放、回稳及切镜两侧，再查看实际连续播放。逐镜检查焦点、角色局部表演、运动主次、视差、光照反馈和跨镜方向；具体问题见 [镜头导演与表演](references/shot-direction.md)。修改绘制代码后，重渲受影响帧；完成全片时核对帧数、尺寸、fps、音轨和播放时长。交付可播放 MP4、项目源码、运行命令以及实际观看后仍存在的视觉问题。详细制作检查点见 [代码逐帧绘制](references/painted-frame.md)。

新项目不调用旧的 `pipeline.py prepare`、`preview.py` 或 Remotion 模板，也不把旧 `motion_plan` Schema 当作逐帧绘制合同。维护旧项目时才按其原有文档和数据版本处理；不要自动迁移或覆盖旧项目。

## 工具与保留

使用当前环境已获授权的图像、音频和浏览器工具；本 Skill 不内置云端生成 API。源图、故事、声音、帧文件及成片保存在仓库外，保留恢复所需文件；用户未要求时不删除。机器专属 Chrome 或 FFmpeg 路径通过项目参数或环境配置传入，不写进通用 Skill 模板。
