# 有限动画与兼容版本

新项目使用 `motion_plan.version="0.4"`；`production_brief.json`、`characters.json` 和 `storyboard.json` 仍为 `"0.1"`。`0.2` 和 `0.3` 是可读取的旧有限动画合同，保留既有项目的固定机位语义；`0.1` 的旧视差路径不能作为正式生产合同。

每镜填写 performance.intent（谁做什么、引发什么反应）与 reviewed。安排准备、动作、反应、停顿，按对白阅读与表演分配帧数；八格不等于八秒。确需静止的建立镜头或喜剧停顿填写 static_reason。图解和产品主题同样通过物体动作或信息状态变化表达内容。

## 已实现

- 局部部件：从当镜 master 拆头、手臂、眼睛、嘴、道具等透明全画布层。底图移除对应部件并补全遮挡区，围绕 pivot 旋转/平移。每个部件在 storyboard.layers 声明，以 character_id 关联人物。
- 关键姿态：同镜同角色的新绘姿态通过 poses 按帧硬切换，可用于眨眼、笑容消失和姿态切换；不含自动补间。大幅转身需更多姿态或专门动画工具。

每层可新增 acting。旧 0.2 的 `from/to` 可以承载兼容路径的外层变换；0.3 与 0.4 的 sequential-comic 与 fixed-camera-micro 必须保持整层 `x/y/scale` 不变，局部动作只写在 acting 轨道。0.4 的显式运镜由 [Camera 与 Parallax 运行时](camera-parallax-runtime.md) 控制。pivot 是全画布归一化坐标；keys 的 x/y 是像素，rotation 是度，opacity 在 0–1 内。镜头内帧线性插值，首项必须为 0，严格递增且不超过末帧。同值关键帧形成停顿。

```json
{
  "part": "arm",
  "pivot": [0.5, 0.45],
  "keys": [
    {"frame":0,"x":0,"y":0,"rotation":0,"opacity":1},
    {"frame":12,"x":0,"y":0,"rotation":-25,"opacity":1},
    {"frame":24,"x":0,"y":0,"rotation":-25,"opacity":1},
    {"frame":47,"x":0,"y":0,"rotation":0,"opacity":1}
  ]
}
```

道具连同骑在上面的人一起摇动（如木马）用 `prop_motion`，人物在道具上的局部补丁用 `attach_to` 跟随；三档嘴型和表情替换同样见 [漫画表演运行时](performance-runtime.md)。

可附加 poses：`[{"frame":0,"asset":"shots/s1/eyes-open.png"},{"frame":12,"asset":"shots/s1/eyes-closed.png"}]`。所有姿态同画布、真透明，prepare 复制全部引用。不能只改文件名冒充新姿态。

## 验收

固定相机查看，仍须辨认人物动作、表情或信息状态变化。检查每个关键帧及中间帧的关节、道具接触、遮挡、眼口位置、文字可读性和节奏。自动检查只识别变化轨道，无法证明动作自然或部件标签真实；目视通过才设 reviewed=true。纯推拉、整个人物漂移不能自动过关。

图像工具失败时保存恢复状态并说明缺图，不自动降级为固定立绘拼贴。当前能力不包含图生视频、自动骨骼绑定、精确音素口型或逐帧补间；0.3/0.4 可在存在实际 WAV 与局部嘴部素材时使用音量驱动的闭/半开/全开嘴型。
