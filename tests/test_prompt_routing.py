"""Contract checks for progressive prompt loading and route boundaries."""
from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AI_DOC_GLOBS = (
    "router.md",
    "common.md",
    "models/*.md",
    "capabilities/*.md",
    "skills/*/SKILL.md",
)
REF_RE = re.compile(
    r"`(?P<path>(?:router|common)\.md|(?:models|capabilities)/[A-Za-z0-9._/-]+\.md|"
    r"skills/[A-Za-z0-9._/-]+/SKILL\.md)(?:#(?P<anchor>[a-z0-9-]+))?`"
)


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def docs():
    seen = set()
    for pattern in AI_DOC_GLOBS:
        for path in ROOT.glob(pattern):
            if path.is_file() and path not in seen:
                seen.add(path)
                yield path


def heading_anchors(text: str) -> set[str]:
    anchors = set()
    for line in text.splitlines():
        match = re.match(r"^#{1,6}\s+(.+?)\s*$", line)
        if not match:
            continue
        heading = re.sub(r"[`*_]", "", match.group(1)).strip().lower()
        heading = re.sub(r"[^a-z0-9\s-]", "", heading)
        heading = re.sub(r"[\s-]+", "-", heading).strip("-")
        if heading:
            anchors.add(heading)
    return anchors


def subsection(text: str, heading: str) -> str:
    match = re.search(
        rf"^### {re.escape(heading)}\s*$\n(?P<body>.*?)(?=^### |^## |\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if not match:
        raise AssertionError(f"missing subsection: {heading}")
    return match.group("body")


def section(text: str, heading: str) -> str:
    match = re.search(
        rf"^## {re.escape(heading)}\s*$\n(?P<body>.*?)(?=^## |\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if not match:
        raise AssertionError(f"missing section: {heading}")
    return match.group("body")


class PromptRoutingTests(unittest.TestCase):
    def test_route_scenarios_have_explicit_contracts(self):
        router = read("router.md")
        expected = {
            "Direct": ("ordinary Q&A", "simple code/API/syntax", "Do **not** load `models/high.md`"),
            "Skill-first": ("names a Skill", "Skill metadata", "does not by itself require `models/high.md`"),
            "Engineering": ("implementation", "code/config changes", "project debugging", "code review", "capabilities/skills.md"),
            "Scout": ("delegated", "context collection", "models/scout.md"),
        }
        for route, terms in expected.items():
            body = subsection(router, route)
            for term in terms:
                with self.subTest(route=route, term=term):
                    self.assertIn(term, body)

    def test_route_changes_are_bidirectional_and_current_intent_scoped(self):
        body = section(read("router.md"), "Route Changes")
        self.assertIn("Direct -> Skill-first", body)
        self.assertIn("Direct or Skill-first -> Engineering", body)
        self.assertIn("Engineering or Skill-first -> Direct", body)
        self.assertIn("current intent", body)
        high = read("models/high.md")
        self.assertIn("current request no longer qualifies as Engineering", high)

    def test_on_demand_capability_triggers_cover_authoritative_policies(self):
        router = read("router.md")
        body = section(router, "On-demand Capabilities")
        for path in (
            "capabilities/skills.md",
            "capabilities/skill-maintenance.md",
            "capabilities/runtime.md",
            "capabilities/mcp.md",
            "capabilities/search.md",
            "capabilities/cross-review.md",
            "capabilities/cleanup.md",
        ):
            with self.subTest(path=path):
                self.assertIn(path, body)
                self.assertTrue((ROOT / path).is_file())

        cleanup_line = next(line for line in body.splitlines() if "capabilities/cleanup.md" in line)
        self.assertIn("any route", cleanup_line.lower())
        self.assertNotIn("via `models/high.md`", cleanup_line)
        self.assertIn("capabilities/search-runtime-suppression.md", read("capabilities/search.md"))

    def test_literal_ai_doc_references_and_anchors_resolve(self):
        for source in docs():
            text = source.read_text(encoding="utf-8")
            for match in REF_RE.finditer(text):
                target = ROOT / match.group("path")
                with self.subTest(source=source.relative_to(ROOT), target=match.group("path")):
                    self.assertTrue(target.is_file(), f"missing referenced file: {match.group('path')}")
                    anchor = match.group("anchor")
                    if anchor:
                        self.assertIn(anchor, heading_anchors(target.read_text(encoding="utf-8")))

    def test_fact_priority_references_point_to_runtime_policy(self):
        self.assertIn("capabilities/runtime.md#fact-priority", read("capabilities/mcp.md"))
        self.assertIn("capabilities/runtime.md#fact-priority", read("skills/anysearch/SKILL.md"))
        for source in docs():
            self.assertNotIn("`router.md` Fact Priority", source.read_text(encoding="utf-8"))

    def test_common_keeps_only_route_independent_guards(self):
        common = read("common.md")
        for engineering_policy in (
            "models/high.md",
            "capabilities/cross-review.md",
            "capabilities/cleanup.md",
            "Requirement Coverage Gate",
        ):
            self.assertNotIn(engineering_policy, common)
        self.assertIn("expanded persistent permission", common)

    def test_base_route_prompt_budgets(self):
        chains = {
            "direct": (("router.md", "common.md"), 6000),
            "scout": (("router.md", "common.md", "models/scout.md"), 8000),
            "engineering": (("router.md", "common.md", "models/high.md"), 15000),
            "skill-discovery": (("router.md", "common.md", "capabilities/skills.md"), 15000),
        }
        self.assertNotIn("models/high.md", chains["direct"][0])
        for name, (paths, limit) in chains.items():
            total = sum(len(read(path).encode("utf-8")) for path in paths)
            with self.subTest(route=name, total=total, limit=limit):
                self.assertLess(total, limit, f"{name} base prompt chain exceeded its budget")


if __name__ == "__main__":
    unittest.main()
