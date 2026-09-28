# 芽芽和星光种子：逐帧动画示例

这是 `procedural-frame` 路线的可运行示例：15 秒、1920×1080、24 fps。镜头可以移动，角色和环境在每一帧由确定性的绘图代码生成。A→B、B→C 使用角色位置和种子落点衔接的直接剪接；没有画笔擦拭或光圈转场。

## 运行

需要 Node.js、pnpm、Chrome/Chromium 和 ffmpeg。安装依赖后，在本目录执行：

```bash
pnpm install --frozen-lockfile
node scripts/production.mjs check
./scripts/render-local.sh --clip --out=out/video.mp4
```

若浏览器不在系统常见安装位置，设置 `CHROME_PATH` 为浏览器可执行文件；若 Node.js 未加入 `PATH`，设置 `NODE_BIN`。需要软件渲染时给最后一条命令追加 `--soft-gl`。

从仓库根目录调用制作入口：

```bash
python scripts/procedural.py inspect examples/procedural-yaya
python scripts/procedural.py check examples/procedural-yaya
python scripts/procedural.py sheets examples/procedural-yaya
python scripts/procedural.py render examples/procedural-yaya --shot C
```

故事、角色和镜头信息在 `production/plan.json`；角色绘制在 `src/rabbit.js`，场景与动作在 `src/scenes/rabbit_seed.js`。修改故事后运行 `node scripts/production.mjs sync`，再出图复核。这里的逐帧是代码重绘，不表示逐帧调用 AI 生图。

本示例基于 [ClaudeAnimationBase](https://github.com/JohnHeibel/ClaudeAnimationBase) 的 p5.js/p5.brush 绘图和渲染基础，遵循原项目 MIT 许可；原版权声明见本目录 `LICENSE`。芽芽角色和故事是为此路线创作的示例。
