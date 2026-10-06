"""Regression checks for the canonical workflow/version documentation."""
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(name):
    return (ROOT / name).read_text(encoding="utf-8")


class DocumentationTests(unittest.TestCase):
    def test_current_contract_versions_are_consistent(self):
        skill = read("SKILL.md")
        contracts = read("references/contracts.md")
        comic = read("references/sequential-comic.md")
        limited = read("references/limited-animation.md")
        self.assertIn('motion_plan.version: "0.4"', skill)
        self.assertIn('motion_plan.json` 使用 `version: "0.4"', contracts)
        self.assertIn("motion_plan 使用版本0.4", comic)
        self.assertIn('motion_plan.version="0.4"', limited)
        self.assertIn("`0.2` 和 `0.3` 是可读取的旧有限动画合同", limited)
        self.assertIn("Camera 与 Parallax 运行时", contracts)

    def test_legacy_entry_points_delegate_to_current_rules(self):
        intake = read("references/project-intake.md")
        director = read("references/storyboard-director.md")
        self.assertIn("动态漫画制作向导", intake)
        self.assertIn("总控复用边界", director)
        self.assertNotIn("基础 Motion Director/Parallax", intake)
        self.assertNotIn("用户确认角色身份 →", intake)

    def test_release_version_has_one_public_story(self):
        skill = read("SKILL.md")
        readme = read("README.md")
        closure = read("references/v04-production.md")
        self.assertIn("当前对外版本是 V1.0", skill)
        self.assertIn("当前工作流版本是 V1.0", readme)
        self.assertIn("不是当前对外版本", closure)
        self.assertNotIn("V1.0 candidate / V0.4 stable engine", readme)

    def test_preview_docs_expose_local_review_outputs(self):
        skill = read("SKILL.md")
        contracts = read("references/contracts.md")
        runbook = read("references/runbook.md")
        quality = read("references/quality-gate.md")
        state = read("references/project-state.md")
        self.assertIn("--shot <shot_id>", skill)
        self.assertIn("visual_review.json", skill)
        self.assertIn("--shot shot_002", runbook)
        self.assertIn("visual-review/", quality)
        self.assertIn("review <project> --approve", state)
        self.assertIn("--incremental", skill)
        self.assertIn("doctor.py", runbook)
        self.assertIn("revision add", state)
        self.assertIn("deliver.py", skill)
        self.assertIn("delivery_report.json", runbook)
        self.assertIn("content-strategy.md", skill)
        self.assertIn("content_strategy", contracts)
        self.assertIn("image-generation-spec.md", skill)
        self.assertIn("simple-comic-style.md", skill)


if __name__ == "__main__":
    unittest.main()
