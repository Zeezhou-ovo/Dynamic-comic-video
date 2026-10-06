# Master 驱动的图层协议

## 顺序

1. 用当镜动作、表情、景别、机位、构图与 identity reference 新绘完整 master；核对原文、角色一致性、手部/纸条/视线与连续性。
2. 按该 master 调整 layer plan，只保留对运动或遮挡有意义的层。
3. 从 master 提取人物透明 PNG。保留原画布和坐标，去掉白边与背景残留，不把参考立绘代替当镜人物。
4. 从 master 去掉人物与独立前景/特效，并修补所有原遮挡区。重建纹理/线条/光照和地面接触关系。背景不能保留人物影像或空洞；独立投影可并入合理的层，避免移动后出现双重影子。
5. 提取/重建前景和 effects。雨若分为独立特效，须从背景去除对应雨层，避免重复。背景自带的静止雨可保留，不强行拆分。
6. 在零变换、原始尺度下合成 `preview.png` 并与 master 叠加比对。重建只应改变原来不可见的区域；可见区域的身份、位置、尺度和遮挡顺序应匹配。
7. 依据计划最大位移检查新露区域；不足则扩绘/修补，或减少移动幅度。不要用透明画布假充完整背景。

```text
shots/shot_001/
  master.png
  preview.png
  layers/bg.png
  layers/lin.png
  layers/fg.png           按需
  layers/rain.png         按需
```

合同 0.1 的层清单和运动元数据直接放在 storyboard.json / motion_plan.json，不另存重复的 shot.json。

## 只有 master 时：用 extract_layer.py 拆层

项目只有完整 master、又需要让其中一部分整体运动（例如道具连同骑在上面的角色一起摇动）时，可以用本地工具从 master 拆出这一层，并补全它后面的背景，不必重新生图：

```sh
python scripts/extract_layer.py extract <project> --master shots/shot_003/master.png \
    --name shot_003_capy_horse --rect 705,110,1185,680 \
    --fg-box 882,262,902,296 --fg-line "740,585 800,615 950,652 1150,585" \
    --bg-poly "700,376 752,376 736,428 812,470 786,562 700,578" \
    --line-art 800,180,858,232 --extend-down-until 345 --pivot 950,664
```

坐标是 master 画布上的像素。`--rect` 框住要拆的整体；和背景颜色接近、容易被漏掉的部分（白衬衫贴白墙、细长的弧形底座）用 `--fg-box` / `--fg-line` 标出来；从缝隙里看到的家具等后方物体用 `--bg-poly` 在分割后剔除；胡须、发丝这类细线用 `--line-art` 框住找回。`--extend-down-until Y` 让 Y 以上的墙面按列向下延伸，柱子和墙边保持笔直；其余区域用图像修补。

工具输出四个文件：透明全画布图层 `<name>.png`、补全后的背景板 `<name>_plate.png`、检查图 `<name>_review.png` 和记录参数与文件指纹的 `<name>.extract.json`。检查图有四格：抠图边缘叠在压暗的 master 上、补好的背景板、以及图层绕 `--pivot` 左右倾斜 `--max-angle`（默认 3°）后的合成，对应上面第 6、7 步的零变换比对和最大位移检查。

打开检查图确认边缘没有漏掉或多带背景、倾斜时露出的背景可以接受，再记录批准：

```sh
python scripts/extract_layer.py approve <project> layers/shot_003_capy_horse.extract.json --note "边缘与±3°露底已检查"
```

正式素材（`asset_mode: production`）下，`validate --assets` 会拒绝未批准的拆层结果；批准后图层、背景板或 master 只要有改动，批准就失效，需要重新运行 extract（可以用 `--hints <旧的 .extract.json>` 沿用原参数）再看一次检查图。工具不保证分割正确，检查图必须真的有人看过。复杂毛发、半透明物体或大面积遮挡仍需回到生图或手工修图。

## 必须检查

- reference 锁 identity 不锁 pose；master 的表演由这一个 shot 决定。
- 透明层 alpha 真透明且非全透明；背景全不透明；所有层同尺寸。
- 静态合成应与 master 对齐；首/中/末帧均无边缘露底、残影、穿插、人物脚底漂移或前景遮脸事故。
- 远背景通常比人物慢、近前景通常更快，但服务于机位和深度，不把“速度越快越好”写死。
- 图像模型对提取/重建失败时，最多两次有针对性的重试；仍失败则交付失败镜号与已保存 master，说明所缺修图能力。不得无限花费或生成不相关图层替代。

`make_fixture.py` 是本地几何测试数据生成器，直接由已知几何合成 master；它不模拟也不证明真实 master 分割流程。仅用于验证时间轴、图层坐标、透明通道和 MP4 管线。
