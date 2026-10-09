# 共享素材库

本规范描述如何从跨项目素材库选择素材，并安全地用于单个动态漫画项目。素材库是复用与管理入口；渲染项目仍保存本次实际使用的文件副本。

## 清单格式

素材库根目录的 `manifests/assets.json` 使用 `version: "0.1"` 和 `assets` 数组。新条目至少包含唯一 `id`、`type` 和相对库根目录的 `path`；建议同时填写 `name`。当前新仓库的 `assets` 数组为空。

```json
{
  "version": "0.1",
  "assets": [
    {
      "id": "bg_classroom_night_001",
      "type": "background",
      "name": "夜间教室",
      "path": "backgrounds/classroom/night.png"
    }
  ]
}
```

`path` 必须指向素材库中的实际文件，不能是绝对路径、URL，不能包含 `..` 越出素材库。角色的参考图、表情、姿势等可分别登记为条目，并用稳定、唯一的 ID 区分。

## 使用素材

- 使用用户提供的本地素材库检出目录。没有本地目录时询问其路径；不自动克隆或拉取私有仓库，不索取凭据，也不上传项目素材。

- 从 `manifests/assets.json` 按精确 `id` 查找。ID 缺失、重复、路径无效或目标不存在时停止并询问，不猜测替代项。若清单字段和示例不同，先检查实际结构再映射，不擅自改写清单。

- 使用 Git LFS 管理的文件必须已在本地展开。若目标文件以 `version https://git-lfs.github.com/spec/v1` 开头，它是 LFS 指针而不是媒体文件；请用户先在有权限的本地检出中取回文件。

## 放入项目

只复制当前项目需要的素材，建议放在 `<project>/assets/library/<asset_id>/<filename>`。将项目内相对路径写入现有 JSON 合同的 `asset` 或 `reference` 字段。不要把素材库绝对路径、URL 或 `asset_id` 填进路径字段，也不要向严格 schema 添加未声明字段。这样现有校验和 renderer 可以继续工作，项目离开素材库也能复现。

为追溯来源，在 `<project>/asset_sources.json` 保存所用资产的 ID、库内相对路径、项目内相对路径和副本的 SHA-256。例如：

```json
{
  "version": "0.1",
  "assets": [
    {
      "asset_id": "bg_classroom_night_001",
      "library_path": "backgrounds/classroom/night.png",
      "project_path": "assets/library/bg_classroom_night_001/night.png",
      "sha256": "<sha256>"
    }
  ]
}
```

`asset_sources.json` 是来源记录，不属于现有渲染合同，不传给 `pipeline.py`。不修改素材库里的原件。

## 当前支持边界

`asset_id` 用于清单查询与来源追踪；现有 schema 和 renderer 仍使用项目内文件路径。若项目需要在渲染时直接按 ID 读取，必须另行实现并验证 schema、解析器和 renderer，不能仅靠在 JSON 中填入 ID。
