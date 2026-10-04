# 简化搞笑条漫画风

这是根据用户参考图提炼的高层视觉语言，不复制参考漫画的角色、台词、分镜格、商标或独特造型。使用时在 `production_brief.json` 设置：

```json
{
  "style_preset": "simple-comic",
  "render_profile": "comic-economy"
}
```

## 画面特征

- 粗而干净的深色线稿，轮廓优先于纹理。
- 平涂色块和少量阴影，颜色明快但控制在有限调色板内。
- 眼睛、嘴型、眉毛和手势清晰，允许夸张表情服务笑点或反应。
- 背景使用简化平面和 2–4 个地点识别物：例如校园树、公告牌、长椅或建筑轮廓；不堆复杂人群、纹理和无关道具。
- 画面保留完整画布和下方约 18–22% 的字幕安全区，人物脸部和关键动作不要压到字幕区。
- 动作线、汗滴、感叹号等漫画符号只在情绪峰值出现，不能每镜都加。

## 文字处理

生图阶段不生成对白气泡、旁白框、漫画字、标题、水印或 Logo。对白、旁白和重点文字统一由视频后期字幕层完成；master 只保留人物表情、手势和足够的留白。若参考图带气泡，只分析其版面节奏，不复制气泡形状和文字。

字幕区要求：

```text
lower 18–22% of the frame kept visually simple and high-contrast;
no faces, hands, props or high-frequency background detail behind subtitles;
do not render any text, speech balloons, captions, logos or watermark in the image.
```

## 连续镜头规则

角色参考锁定脸型、发型、服装、体型和辨识锚点；每个镜头只改变剧情所需的姿势、表情、视线、景别或机位。背景可以简化，但不能改变地点事实。每个镜头先生成完整 master，再从同一 master 拆出人物、背景和必要前景层。

## 局部表演

简单画风不能退化成逐镜静帧。每个有对白的镜头至少规划一个可复核的嘴部开合区间；较长镜头可增加一次短眨眼。眼睛和嘴部必须使用与同一 master 对齐的局部变体，不能用整图缩放、随机漂移或循环摆动冒充表演。正式配音项目在 motion_plan 的局部 acting 轨记录眼/嘴区域、嘴部资产与事件；生成后用首帧、说话帧和眨眼帧检查接缝。旧 simple-comic 无声速览路径不具备完整音频演出能力，不作为有对白成片的默认路径。generate_simple_comic_motion_assets.py 的 mouth_open 目前保留源图，不能用该脚本声称新绘了张嘴资产。

```powershell
python scripts/preview.py <project> --renderer <external-renderer>
```

没有实际配音时，嘴部帧只能标记为估计预演；正式成片仍需用本地配音重算字幕和嘴型时间轴。

## 负面约束

```text
no speech bubbles, no comic lettering, no generated text, no watermark;
no copied named-comic characters, no copied panel layout or dialogue;
no photorealism, no glossy 3D plastic, no excessive gradients;
no busy background behind the face or subtitle-safe area;
no extra fingers, fused hands, identity drift or missing accessories;
no independent lighting between layers, no transparent holes in the background.
```

扩展嘴部、局部缓动、直接表情事件和可播放音效的字段与验收见 [对话喜剧的局部表演](comedy-acting.md)。这些是可选扩展，现有合同版本不变；旧项目不自动新增素材或改变已确认内容。
