# 生图规范与提示词合同

这份规范约束角色参考、当镜 master 和图层提取三类图像工作。生图的目标不是单张海报好看，而是让同一角色在不同分镜中保持身份，让每张 master 都能被可靠拆层并进入动态化。

用户选择参考图中的简化搞笑条漫画面时，读取 [简化搞笑条漫画风](simple-comic-style.md)，使用 `style_preset: "simple-comic"`。只提取粗线、平涂、有限色块、夸张表情和简化背景等高层特征，不复制具体漫画的角色、台词、格子或独特造型。

## 三类任务必须分开

### 1. Character Reference

只生成身份参考，不生成正式镜头。至少包含正面、四分之三和侧面辨识信息，锁定：

- 脸型、五官比例、眼睛形状与瞳色、鼻口特征、肤色
- 发色、发型结构、刘海、长度和标志性发饰
- 体型比例、服装款式与颜色、鞋子和主要配饰

参考图只用于身份，不复制它的姿势、表情、景别、镜头角度或构图。每个主要角色记录 3–5 个不可丢失的识别锚点。

### 2. Shot Master

每个镜头重新生成一张完整 master，先确定剧情动作、机位、构图和遮挡，再考虑画面细节。一个 master 只表达一个主要信息、动作或反应；复杂姿势和新角度拆成下一镜。

提示词固定按下面顺序组织，不能把风格词堆在最前面掩盖内容：

```text
[任务与镜头 ID]
[剧情信息：这个镜头发生了什么变化]
[场景：地点、时代、文化、时间、天气、主要物件]
[机位：景别、角度、固定相机、构图和视线引导]
[人物：character_id + 身份锚点 + 当镜姿势、表情、视线、动作]
[道具与接触：手、手机、书、桌面、地面接触关系]
[连续性：上一镜进入状态、下一镜交接状态、光向和服装]
[视觉语言：线条、色块、光影、材质和细节预算]
[输出：完整画布、清晰轮廓、可拆层、无文字；下方 18–22% 留字幕安全区]
[负面约束]
```

提示词必须明确“人物为什么此刻要动”。没有台词、信息、情绪、互动或观察对象触发的动作，改为稳定姿态，不用随机摆姿势填充画面。

### 3. Layer Extraction

图层不是第三次独立生图。先确认 master，再从同一 master 提取或重建：

```text
master.png
├─ layers/bg.png       背景与被人物遮挡区域补全
├─ layers/character.png 全画布透明人物层
├─ layers/fg.png       必要前景
└─ layers/effect.png   必要漫画符号或独立特效
```

提取提示词必须写明“保持 master 的画布、坐标、比例、光向和可见边缘”，只补全原本被遮挡的区域。禁止用新的角色图、不同光照或独立背景替代 master；禁止把透明画布、裁切人物或白底图当作完成图层。

## 固定输出字段

每个提示词文件应保留以下追溯信息；未知值写 `null`，不要猜模型参数：

```json
{
  "prompt_version": "0.1",
  "project_id": "项目 ID",
  "shot_id": "shot_001",
  "prompt_role": "master",
  "reference_images": [
    {"path": "characters/hero/reference.png", "use": "identity_only"}
  ],
  "do_not_copy_from_reference": ["pose", "expression", "shot_size", "camera", "composition"],
  "model": null,
  "seed": null,
  "size": {"width": 1086, "height": 1448},
  "negative_constraints": ["no text", "no watermark", "no extra fingers"]
}
```

`compile` 生成的 master 提示词还带 `continuity_instructions`：每个角色这一镜的姿态和位置（与上一镜相同时要求保持，写了 `posture_change` 时要求把变化画出来），以及正反打时“背景必须是对面一侧、不要重复上一镜背景”的说明。生图时要把这些写进实际提示词。

同一角色跨镜优先复用身份参考和已确认的锚点；同一镜返工优先修正 prompt 或 master，不偷偷替换角色设定。保存模型、seed、尺寸和参考图路径，才能判断变化来自提示词、随机性还是模型。

## 统一负面约束

按内容增删，但以下约束默认保留：

```text
no baked-in dialogue, captions, logos or watermark;
no speech bubbles, comic lettering or generated text;
no extra characters, extra fingers, fused hands or broken contact points;
no identity drift, hairstyle drift, clothing color change or accessory loss;
no copied reference pose, no unrelated standing pose;
no camera zoom, pan, rotation, parallax or whole-image stretch;
no photorealistic surface, glossy 3D plastic or unrelated cultural elements;
no independent lighting between layers, no transparent background holes in bg;
clean full canvas, readable silhouette, stable perspective, complete occluded background.
```

## 生图验收顺序

先看内容，再看美术，再看可动性：

1. 角色身份、手部、道具接触和视线是否正确。
2. 场景是否能说明地点，机位是否真的改变了信息，而不是裁切上一张图。
3. 光向、透视、遮挡和服装是否与相邻镜头连续。
4. master 是否有完整画布，拆层后是否会露出空洞、残影、白边或双重影子。
5. 画面是否留出字幕安全区，是否没有生成文字和水印。

身份、解剖、接缝和表演自然度不能只靠提示词或 Schema 证明；失败镜头最多做两次有针对性的重试，并保留失败记录。
