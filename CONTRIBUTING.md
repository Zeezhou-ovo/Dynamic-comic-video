# 参与贡献

感谢参与 `Dynamic-comic-video`。这个仓库只维护 Remotion 分层动态漫画 Skill、相关合同、脚本和无用户内容的测试夹具。代码逐帧绘制路线已移至独立仓库 [code-painted-video](https://github.com/zeezhouovo-creator/code-painted-video)。

## 提交修改

1. 从 `main` 创建分支，例如 `feat/intake-guidance` 或 `fix/schema-validation`。
2. 只提交通用规则、脚本、Schema、文档和可公开的测试夹具。
3. 在本地运行：

   ```powershell
   python -m unittest discover -s scripts -p 'test_*.py'
   node --test scripts/test_camera_runtime.mjs scripts/test_character_runtime.mjs scripts/test_performance_runtime.mjs
   python scripts/pipeline.py compile examples\library
   python scripts/pipeline.py validate examples\library
   ```

4. 提交 Pull Request，说明行为变化、兼容性影响和验证结果。

## 内容与隐私边界

不要提交用户的故事原稿、角色设定图、参考图、配音、成片、访问令牌、API Key 或 `.env` 文件。真实制作项目应放在仓库之外的本地工作目录；`projects/`、`*.mp4`、`*.wav` 和常见凭据文件已加入忽略规则。

## 规则变更

涉及分镜字段、动作约束或 Schema 的修改，应同步更新根目录 `SKILL.md`、相关 `references/`、Schema、测试和 `CHANGELOG.md`。逐帧代码绘制路线的贡献请转到独立仓库维护。
