# 剪纸喜剧 / 沙雕动画模式

适用于对白驱动、反应驱动和包袱驱动的数字剪纸式有限动画。目标不是模拟连续自然运动，而是在较少姿态和局部素材下，通过姿势切换、表情替换、短促位移、停顿、硬切和镜头强调完成清楚的喜剧表演。

本模式可用于熊猫人式沙雕动画、简化角色喜剧、对话短剧和低帧夸张反应视频。它不是逐帧动画、骨骼动画或精确音素口型方案。

## 接入

使用 motion_plan 0.4，在逐镜 performance 中设置：

```json
{"mode":"cutout-comedy","intent":"对白驱动的剪纸喜剧表演；静止优先，动作只在信息和 reaction 节点发生。","reviewed":false}
```

剧情、Narrative Beats 和 Shots 仍由分镜规则负责；对白、listener reaction、pause 和镜头意图仍由 director_plan 负责。本模式不建立第二套动作时间轴。

## 核心规则

- 默认完全静止。没有显式动作时，不加呼吸、漂浮、随机摆动或说话时 body bob。
- 姿势切换优先于连续补间；明显大动作优先新 pose asset。
- 大多数强调动作短促进入主要姿态，然后保持或回稳，不循环。
- 说话人和听者分开设计；包袱后的 reaction 与 pause 是正式表演，不是空白。
- 默认固定机位；推近、screen shake 和漫画符号只在明确强调时使用。
- 同一瞬间尽量只有一个主要视觉强调，避免 body shake、screen shake、强推近和漫画符号全部叠加。
- 静止是有效表演。speechless、awkward、stunned 等反应可以只换表情然后保持。

## 第一版动作

Character Performance Runtime 增加：

```text
head_forward
lean_back
body_shake
double_take
```

继续复用已有：

```text
nod
shake_head
point
raise_hand
blink
small_bounce
talk
```

表情继续使用 expression/state assets；整个人物进出场继续使用 root_keys；screen shake 继续使用 visual_events；pause 继续使用 director_plan；镜头强调继续使用现有 Camera Runtime。

## Director 映射

cutout-comedy 使用 mode-aware reaction 映射：

- speechless：表情替换 + 静止 hold，不自动 blink。
- awkward：表情替换 + 静止 hold。
- surprised：优先 lean_back。
- confused：优先 double_take。
- annoyed：可 shake_head。
- laugh：可 small_bounce。

如果角色素材不具备动作所需 body/head part，resolver 必须安全降级为表情或静止，不虚构能力。

## 负面约束

禁止：

- 全程周期性上下漂浮；
- 每句话都 punch zoom；
- 所有人同时 reaction；
- 用 screen shake 代替人物反应；
- 用整图拉伸制造大幅新姿势；
- 包袱结束后立即进入下一句；
- renderer 根据台词字符串自己判断笑点。

本模式追求的不是“动得多”，而是动作、静止、反应和切镜发生在正确的叙事时刻。
