# 本地运行

需要 Python 3.10+、Node.js 18+。下列命令在技能项目根目录执行。建议新建本地虚拟环境；命令中的 python 应指向该环境。

```powershell
python -m pip install -r requirements.txt
python scripts/pipeline.py validate examples/library
python scripts/pipeline.py compile examples/library
python scripts/make_fixture.py examples/library
python scripts/pipeline.py validate examples/library --assets
python scripts/pipeline.py prepare examples/library --renderer ../../work/manga-renderer
```

进入上述 renderer 目录后：

```powershell
npm ci
npm run render
npm run still -- --frame=24
```

输出为 renderer 的 `out/video.mp4`。依赖安装需要网络，但内容渲染和 fixture 生成在本地执行，不需要 API Key。完整时长 144 帧 / 24 fps = 6 秒，960×540，三镜硬切。可选 `npm run studio` 进行交互预览。

## Camera / 2.5D 验证场景（motion_plan 0.4）

```powershell
python scripts/make_camera_parallax_fixture.py ../camera-fixture
python scripts/pipeline.py validate ../camera-fixture --assets
python scripts/pipeline.py prepare ../camera-fixture --renderer ../camera-renderer
cd ../camera-renderer
npm ci
npm run render
```

输出 `../camera-renderer/out/video.mp4`：前 48 帧固定广角，接着 48 帧推进，最后 48 帧右移；五个 depth 从前到后分别响应相机。该场景是合成几何测试素材，不是正式剧情。纯函数测试使用 `node --test scripts/test_camera_runtime.mjs`，Python 合同测试包含在仓库的 unittest 集中。

## 正式故事

1. 先按 [短视频内容策划层](content-strategy.md) 确定受众、平台、钩子、核心承诺和结尾收获；再把四份示例 JSON 复制到独立生产目录，按原文重写 brief、characters、beats、shots 与 motion；不要仅替换角色姓名。
2. validate 后 compile，Agent 使用生成的提示词完成 reference 和 master。按分层协议准备实际图层和 preview。正式项目不运行 make_fixture。
3. reference 设 ready；motion asset_mode 设 production；记录实际 review 结果。
4. validate --assets，审阅 repetition_warnings 和图像接触表，针对性修正。
5. 预览前运行 `python scripts/quality_gate.py <project> --autofix`，检查 `quality_report.json`；Critical/Major 问题修复后才继续。
6. prepare 指向独立 renderer，执行 npm ci 与 npm run render；复制最终视频到该任务的交付目录。

要验证眼睛和嘴巴以外的局部表演，可先生成固定相机回归夹具：

```powershell
python scripts/make_extended_acting_fixture.py ..\extended-acting-fixture
python scripts/pipeline.py validate ..\extended-acting-fixture --assets
python scripts/preview.py ..\extended-acting-fixture --renderer ..\extended-acting-renderer
```

该夹具只包含合成几何图形，用于检查头部、手部和道具的准备—动作—回稳节奏，不代表正式美术质量。

也可以用一条命令执行第 4—6 步：

```powershell
python scripts/preview.py <project> --renderer <project-outside-renderer>
```

脚本会先重新校验素材、运行质量闸门，再编译、prepare、渲染，并把 `renderer/out/video.mp4` 复制为 `<project>/preview.mp4`，同时把首/中/末帧复制到 `<project>/visual-review/` 并写入带指纹的 `visual_review.json`。打开这些帧完成检查后，运行 `python scripts/project_state.py review <project> --approve`；发现问题运行 `--reject --note "..."`。只预览单镜头时追加 `--shot shot_002`；首次使用该 renderer 时增加 `--npm-install`。它不会上传项目文件，也不会读取或写入 API Key。

如果只需要更新改过的镜头，可以运行：

```powershell
python scripts/preview.py <project> --renderer <project-outside-renderer> --incremental
```

它会把每个镜头的 MP4 和首/中/末帧放入 `<project>/incremental-preview/`，并写入 `incremental_preview.json`。未变化镜头按素材指纹复用缓存；该模式生成的是逐镜缓存，不替代完整全片 MP4，交付前仍需运行普通预览命令。

新环境先运行：

```powershell
python scripts/doctor.py
python scripts/doctor.py <project> --renderer <project-outside-renderer>
```

视觉复核批准、返工台账清空后运行交付闸门：

```powershell
python scripts/deliver.py <project>
```

它把合同校验、质量报告、视觉复核指纹、未关闭返工项与 `ffprobe` 媒体检查合并为 `<project>/delivery_report.json`。报告为 `PASS` 才算机器检查通过；`FAIL` 时按 `blocking_issues` 修复。`ffprobe` 必须可在本机 PATH 找到，闸门不会联网、安装依赖或读取云端凭据。

不要把 private 配置放入 renderer/public。prepare 不拷贝 `.env`、原文或 reference 到 public，仅拷贝渲染层和必要的运动元数据。

## 排错

- 结构错误：查看 qc_report.json；修改对应数据而非绕过校验。
- 缺图、大小不一致、透明通道不合格：返回 master/layer 阶段处理。
- Timeline gap/overlap：重新累加 start_frame，保持整数帧与总长一致。
- Motion can reveal canvas edge：减小位移或适度放大；放大仍须检查脸部和构图裁切。
- 浏览器首次下载/渲染失败：保存明确错误，检查本地浏览器和网络条件；不得把仅成功的 JSON 校验报告成 MP4 成功。

模板使用镜头内帧驱动确定性插值。实现依据：[Remotion Sequence](https://www.remotion.dev/docs/sequence)、[CLI render](https://www.remotion.dev/docs/cli/render)。
