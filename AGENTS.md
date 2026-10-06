# 给 AI 助手的说明

这个仓库是一个通用的动态漫画制作 skill，不依赖任何特定的 AI 产品。

用户请求制作动态漫画、漫剧、motion comic，或修改已有的动态漫画项目时：

1. 先完整读取本仓库根目录的 [SKILL.md](SKILL.md)，按其中的“入口与按需加载”表格只读当前阶段需要的 `references/` 文档。
2. 脚本都在 `scripts/` 下，用本机 Python（3.10+）运行；渲染用 `assets/remotion` 里的 Remotion 模板（Node 18+）。路径一律相对本仓库根目录解析。
3. 用户的视频项目放在本仓库之外的独立文件夹，不要把用户素材、配音或成片写进本仓库。
4. 生图、配音使用当前环境里已有且已获授权的工具；本仓库不内置任何云端生成服务，也不保存密钥。
5. 只读不能运行命令时：照常完成分镜、JSON 和提示词，把需要执行的命令列给用户，不要声称已经渲染或校验。

修改本仓库代码时，提交前运行：

```sh
python -m unittest discover -s scripts -p 'test_*.py'
node --test scripts/test_camera_runtime.mjs scripts/test_character_runtime.mjs scripts/test_performance_runtime.mjs
```
