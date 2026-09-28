# 参与贡献

感谢参与 `Dynamic-comic-video`。这个仓库维护的是通用 Agent Skill、数据契约、校验脚本和无用户内容的测试夹具。

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

涉及分镜字段、动作约束或 Schema 的修改，应同步更新 `SKILL.md`、相关 `references/`、Schema、测试和 `CHANGELOG.md`。分层路线保持“人物由事件触发动作、镜头不替人物运动”的约束；逐帧路线允许有叙事原因的镜头运动，但仍须让角色自身完成表演。
