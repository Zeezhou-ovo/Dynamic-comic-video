# 参与贡献

感谢参与 `Dynamic-comic-video`。这个仓库维护 `dynamic-comic-video`（Remotion 分层动画）与 `code-painted-video`（代码逐帧绘制）两个独立 Skill，以及各自的合同、脚本和无用户内容的测试夹具。

## 提交修改

1. 从 `main` 创建分支，例如 `feat/intake-guidance` 或 `fix/schema-validation`。
2. 只提交通用规则、脚本、Schema、文档和可公开的测试夹具。
3. 在本地运行：

   ```powershell
   python -m unittest discover -s scripts -p 'test_*.py'
   python scripts/pipeline.py compile examples\library
   python scripts/pipeline.py validate examples\library
   ```

4. 提交 Pull Request，说明行为变化、兼容性影响和验证结果。

## 内容与隐私边界

不要提交用户的故事原稿、角色设定图、参考图、配音、成片、访问令牌、API Key 或 `.env` 文件。真实制作项目应放在仓库之外的本地工作目录；`projects/`、`*.mp4`、`*.wav` 和常见凭据文件已加入忽略规则。

## 规则变更

涉及 Remotion 路线的分镜字段、动作约束或 Schema 时，更新根目录 `SKILL.md` 和对应资源。涉及逐帧路线时，更新 `skills/code-painted-video/SKILL.md` 和其目录内的资源。两条路线的行为变更都记录到 `CHANGELOG.md`，避免用另一条路线的合同或渲染命令解释当前项目。
