# 动态漫画质量闸门

质量闸门在预览生成前运行，目标是先发现并局部修正明显问题，而不是继续增加动画或特效。优先级为：角色一致性 → 分镜连续性 → 动作自然度 → 音画同步 → 字幕可读性 → 节奏 → 视觉特效 → 装饰细节。

运行：

```powershell
python scripts/quality_gate.py <project>
python scripts/quality_gate.py <project> --autofix
```

它会生成项目内的 `quality_report.json`。`--autofix` 只修复安全的时间轴元数据边界，例如把 `timeline.duration_frames` 与镜头时长对齐、把超出镜头的 `cut_at_frame` 截到镜头末尾；不会自动重画人物、背景或改变剧情。

预览脚本另外生成 `visual_review.json` 和 `visual-review/` 图片。它们记录每个选中镜头的首帧、中帧和末帧，并将 `reviewed` 初始设为 `false`；实际查看身份、接缝、接触、遮挡、字幕和节奏后，使用 `python scripts/project_state.py review <project> --approve` 记录通过，发现问题则使用 `--reject --note "..."`。清单绑定源文件、MP4 和复核图片指纹，输入变更后旧批准会失效。图片存在不代表视觉质量通过。

返工反馈使用 `python scripts/project_state.py revision add <project> --text "..." --shot <shot_id>` 记录；未解决的返工记录会阻止状态机进入可交付阶段。

视觉复核批准并关闭返工后，运行 `python scripts/deliver.py <project>` 生成 `delivery_report.json`。它再次执行合同和质量检查，验证复核清单仍绑定当前源文件，并用本机 `ffprobe` 检查 MP4 的尺寸、帧率、时长和视频流；失败时按报告中的 `blocking_issues` 处理。

## 检查层级

- **Critical**：角色明显变成另一个人、严重变形、嘴型与声音严重错位、分镜顺序错误或字幕内容错误。阻止预览。
- **Major**：动作机械、背景空间跳变、字幕严重遮挡、镜头停留异常、对白被音乐覆盖或时间轴越界。先局部修正，再预览。
- **Minor**：某次眨眼略机械、某个音效略多、停顿略短或字幕位置可优化。允许进入预览并记录。

自动检查会核对镜头和场景引用、镜头时长与统一时间轴、字幕/语音事件边界、嘴型层是否有对白、固定机位是否发生整层运动、动作事件密度、重复构图标签和角色识别锚点。

节奏相关的自动检查：

| 类别 | 级别 | 规则 |
| --- | --- | --- |
| `pacing` | Minor | 第一句台词前超过 1 秒、或最后一句台词后超过 1 秒加上 `reaction_hold_frames`，且这段时间内没有任何动作/表情/特效/音效事件开始，记为空白。报告的 `pacing.silent_ratio` 给出全片无台词帧占比。 |
| `punchline` | Major | 被标为 punchline 的台词（台词或字幕 `emphasis/priority`，或 `visual_events.priority`）结束后，到下一句台词开始（包括跨 CUT 到下一镜）不足 0.4 秒。 |
| `reverse_shot` | Minor | 相邻两镜同场景、各只有一个且不同的人物、相机位置不同，但 `background_view` 相同。 |
| `reveal` | Major / Minor | 分镜写了 `reveal` 的镜头：上一镜铺垫台词结束到切镜超过 0.5 秒，或揭示镜头开口早于 `hold_frames`（默认 0.5 秒）为 Major；停顿里没有任何动作、表情、道具运动或音效为 Minor。 |
| `ending` | Minor | 全片最后一句台词之后，到结束都没有动作、表情、道具运动或音效作为收尾反应。 |

姿态、位置和正反打背景在生图前由 `pipeline.py validate` 检查（`posture`、`placement`、`reverse_background` 提示），不必等到成片。

交付闸门另外用本机 `ffmpeg` 测量成片的综合响度、真峰值和数字静音占比，写入 `delivery_report.json` 的 `audio_loudness` 检查。目标是 −14 ± 2 LUFS、真峰值不超过 −1 dBTP、数字静音不超过 25%。这一项只给提示不阻止交付，因为不同平台的响度标准不同；没有安装 ffmpeg 时记为 `SKIPPED`。像素级脸型、五官、发根接缝、背景透视、表演自然度和字幕是否遮挡表情仍需查看接触表与关键帧。

## 最小修改

问题按模块处理：角色漂移只修该镜角色；动作机械只删减或调整动作事件；字幕问题只改字幕时间或位置；音效过密只删除多余音效；CUT 太慢只调整镜头时长。不要因局部问题重做整个项目。

用户反馈映射：

| 反馈 | 优先检查 |
| --- | --- |
| 人物很僵 / 一直晃 | 动作密度、静止阶段、事件触发 |
| 像 PPT | 分镜变化、人物表演、CUT 节奏 |
| 字幕太抢眼 | 字幕视觉层级、重点字幕数量 |
| 感觉很赶 / 很拖 | CUT 节奏、反应时间、镜头时长；查看 `pacing` 与 `punchline` 提示 |
| 笑点没炸 | 揭示画面是否早于台词结束、笑点后停顿、结尾反应按钮 |
| 声音太小 / 空 | `delivery_report.json` 中的 `audio_loudness` |
| 人物变脸 | Character Reference 与该镜身份锚点 |

如果仍存在 Critical 或 Major 问题，不直接输出最终视频；修复并重新运行质量闸门。没有 Critical/Major 后才进入预览。
