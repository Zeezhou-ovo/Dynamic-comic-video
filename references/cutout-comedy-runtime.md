# Cutout Comedy Runtime

本文件说明 `cutout-comedy` 如何复用 motion_plan 0.4、Character Performance Runtime、Dialogue & Performance Director、Camera 和漫画表演运行时。

## 数据边界

不新增通用 `comedy_action`。能力映射如下：

| 需求 | 现有合同 |
| --- | --- |
| 人物短动作 | `character_performance.events` |
| 整体进出场 / pop | `root_keys` |
| pose 切换 | `pose` / `acting.poses` |
| 表情替换 | `expression` / `expression_events` |
| reaction hold / pause | `director_plan` |
| screen shake | `visual_events` |
| 音效 | `sound_events` |
| 推近 | Camera Runtime |

## 静止优先

Character Performance Runtime 接收 shot 的 `performance.mode`。当值为 `cutout-comedy` 时：

- 关闭 idle/listener 默认 procedural breathing；
- 关闭对白和 talk preset 的默认 body bob；
- 保留嘴型；
- 保留显式 event；
- 保留 root_keys、acting.keys、pose 和 expression。

因此 cutout-comedy 的默认状态是完全静止，只有数据明确声明时才动。

## 新 preset

### head_forward

短促前探，用于质问、吐槽和强调。优先作用 head；无 head 时退到 body。小幅 transform 足够时不用新 pose，大幅动作仍应新绘 pose。

### lean_back

短促后仰，用于震惊、躲避或信息冲击。作用 body/root，并围绕已有 root pivot 回稳。动作结束必须回到 identity。

### body_shake

只震人物，不等于 screen shake。使用短时衰减震动并回零，不允许无限正弦循环。

### double_take

表示延迟理解后猛然回看。至少包含偏开、快速回看、回稳三个阶段；不能退化成普通 shake_head。

## Director

director_plan schema 保持 0.1 不变。resolver 根据 source motion shot 的 `performance.mode` 选择 reaction rules；旧 sequential-comic 继续使用原映射。

## 验收

至少验证：

1. cutout listener 无显式动作时完全静止；
2. cutout speaker 可动嘴但 body 不自动 bob；
3. 四个新 preset 在事件期间可见并在结束后归零；
4. sequential-comic 原 procedural idle 行为不变；
5. speechless 在 cutout mode 下不自动 blink；
6. surprised/confused 分别可映射到 lean_back/double_take；
7. 同一输入随机 seek 时结果确定。
