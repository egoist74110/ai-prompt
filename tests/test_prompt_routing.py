"""Contract checks for progressive prompt loading and route boundaries."""
from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AI_DOC_GLOBS = (
    "router.md",
    "models/*.md",
    "roles/*.md",
    "capabilities/*.md",
    "skills/*/SKILL.md",
)
REF_RE = re.compile(
    r"`(?P<path>router\.md|(?:models|roles|capabilities)/[A-Za-z0-9._/-]+\.md|"
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
        routes = section(read("router.md"), "Routes")
        self.assertIn("guarantees the current intent needs", routes)
        self.assertIn("Unclear -> Direct", routes)
        self.assertIn("switch per phase", routes)
        expected = {
            "Direct": ("ordinary Q&A", "simple code/API/syntax", "one lookup", "Do **not** load `models/high.md`"),
            "Research": ("several sources", "data analysis", "capabilities/research.md"),
            "Writing": ("fiction", "roleplay", "reports", "sending is Operate", "not Engineering", "capabilities/writing.md"),
            "Engineering": ("implementation", "code/config changes", "project debugging", "code review", "models/high.md"),
            "Operate": ("publish", "delete", "deploy", "capabilities/operate.md"),
            "Media": ("images", "diagrams", "preview", "capabilities/cleanup.md"),
            "Think": ("deciding", "trade-offs", "do not just agree"),
        }
        names = re.findall(r"^- \*\*(\w+)\*\*:", routes, re.MULTILINE)
        self.assertEqual(names, list(expected))
        for route, terms in expected.items():
            body = next(line for line in routes.splitlines() if line.startswith(f"- **{route}**:"))
            for term in terms:
                with self.subTest(route=route, term=term):
                    self.assertIn(term, body)
        router = read("router.md")
        self.assertNotIn("Skill-first", router)
        self.assertNotIn("### Scout", router)
        self.assertIn("models/scout.md", section(router, "Roles"))
        self.assertIn("never selects the route by itself", section(router, "Skill Offers"))
        high = read("models/high.md")
        self.assertIn("current request no longer qualifies as Engineering", high)

    def test_external_action_floor_is_always_on(self):
        base = section(read("router.md"), "Base Rules")
        floor = next(line for line in base.splitlines() if line.startswith("- External actions"))
        for term in ("authorizes exactly the named action", "ask first", "verify the real outcome"):
            self.assertIn(term, floor)
        for role in ("lead", "build", "test", "hotfix", "review"):
            with self.subTest(role=role):
                self.assertIn("verify the real outcome", read(f"roles/{role}.md"))
        operate = read("capabilities/operate.md")
        for term in ("dry run", "undo path", "never grants permission", "Verify the real outcome in the target system"):
            with self.subTest(term=term):
                self.assertIn(term, operate)

    def test_research_contract(self):
        research = read("capabilities/research.md")
        for term in ("source link", "date or version", "present the conflict", "Separate verified facts from inference",
                     "capabilities/search.md", "capabilities/writing.md"):
            with self.subTest(term=term):
                self.assertIn(term, research)

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
            "capabilities/windows-shell.md",
        ):
            with self.subTest(path=path):
                self.assertIn(path, body)
                self.assertTrue((ROOT / path).is_file())

        cleanup_line = next(line for line in body.splitlines() if "capabilities/cleanup.md" in line)
        self.assertIn("any route", cleanup_line.lower())
        self.assertNotIn("via `models/high.md`", cleanup_line)
        self.assertIn("capabilities/search-runtime-suppression.md", read("capabilities/search.md"))

    def test_response_contract_is_separate_and_cache_driven(self):
        router = read("router.md")
        base_rules = section(router, "Base Rules")
        response_layer = section(router, "Response Layer")

        self.assertIn("`response_profile` entry in `.local/prefs.json`", response_layer)
        self.assertIn("do not read, probe", response_layer)
        self.assertIn("Do not infer or select a persona", response_layer)
        self.assertIn("user-facing", response_layer)
        self.assertIn("must not change reasoning", response_layer)
        self.assertNotIn("Simplified Chinese", router)
        self.assertIn("language of the user's current message", response_layer)
        self.assertIn("never reasoning", response_layer)
        self.assertIn("Persist lasting preferences", response_layer)
        self.assertNotIn("language", base_rules.lower())
        self.assertTrue((ROOT / "config/response-profile.example.md").is_file())

    def test_writing_work_is_exempt_from_response_profile(self):
        response_layer = section(read("router.md"), "Response Layer")
        exemption = next(line for line in response_layer.splitlines() if "Writing-route work text" in line)
        self.assertIn("not presentation", exemption)
        self.assertIn("never persist", exemption)

        creative = read("capabilities/writing.md")
        for term in (
            "never from `response_profile`",
            "Never record them in `.local/response-profile.md`",
            "`artifact` deliverables",
            "capabilities/cleanup.md",
            "do not make the task Engineering",
            "Switch to Engineering only for tooling",
            "Sending or publishing the text is Operate",
            "Skill Offers still apply",
        ):
            with self.subTest(term=term):
                self.assertIn(term, creative)
        self.assertNotIn("models/high.md", creative)

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

    def test_base_rules_keep_only_route_independent_guards(self):
        common = section(read("router.md"), "Base Rules")
        for engineering_policy in (
            "models/high.md",
            "capabilities/cross-review.md",
            "capabilities/cleanup.md",
            "Requirement Coverage Gate",
        ):
            self.assertNotIn(engineering_policy, common)
        self.assertIn("expanded persistent permission", common)
        self.assertIn("runtime_state.py get <state|runtime> <key>", common)

    def test_base_route_prompt_budgets(self):
        base = ("router.md",)
        # Hard ceilings guard the layered design; over budget -> move rules to an on-demand capability.
        chains = {
            "direct": (base, 9000),  # includes the always-on Skill Offers rule
            "scout": (base + ("models/scout.md",), 10500),
            "writing": (base + ("capabilities/writing.md",), 13000),
            "research": (base + ("capabilities/research.md",), 12000),
            "operate": (base + ("capabilities/operate.md",), 12000),
            "engineering": (base + ("models/high.md",), 17500),
            "skill-discovery": (base + ("capabilities/skills.md",), 17500),
        }
        self.assertNotIn("models/high.md", chains["direct"][0])
        # Count on-disk bytes: read_text() folds CRLF to LF and would hide real overruns.
        raw = {path: (ROOT / path).read_bytes() for paths, _ in chains.values() for path in paths}
        for path, data in raw.items():
            self.assertFalse(b"\r\n" in data, f"{path} has CRLF; re-checkout per .gitattributes (eol=lf)")
        for name, (paths, limit) in chains.items():
            total = sum(len(raw[path]) for path in paths)
            with self.subTest(route=name, total=total, limit=limit):
                self.assertLess(total, limit, f"{name} base prompt chain exceeded its budget")

    def test_role_entries_bypass_router_and_stay_small(self):
        roles_section = section(read("router.md"), "Roles")
        self.assertIn("role: <name>", roles_section)
        self.assertIn("roles/dispatch.md", roles_section)
        for role in ("lead", "build", "test", "hotfix", "review"):
            path = f"roles/{role}.md"
            text = read(path)
            with self.subTest(role=role):
                self.assertIn(f"role: {role}", text)
                self.assertIn("replaces `router.md`", text)
                self.assertIn("Report only real results", text)
                self.assertIn("cannot", text)  # untrusted-content guard
                self.assertIn("capabilities/cleanup.md", text) if role != "lead" else None
                self.assertIn("capabilities/windows-shell.md", text) if role != "lead" else None
                self.assertLess(len((ROOT / path).read_bytes()), 2500, f"{path} exceeded its budget")
        self.assertIn("MUST NOT change product code", read("roles/test.md"))
        self.assertIn("Stop and report instead of widening", read("roles/hotfix.md"))
        self.assertIn("MUST NOT dispatch another reviewer", read("roles/review.md"))
        self.assertIn("not the model", read("roles/lead.md"))
        self.assertIn("never from which model you are", read("config/entry.example.md"))
        self.assertTrue((ROOT / "config/prefs.example.json").is_file())
        # Role files must be self-sufficient: no rule may live only in the router they skip.
        for role in ("lead", "build", "test", "hotfix", "review"):
            self.assertNotIn("router.md#", read(f"roles/{role}.md"))
        lead = read("roles/lead.md")
        self.assertIn("roles/dispatch.md", lead)
        dispatch = read("roles/dispatch.md")
        for term in ("`role: <name>`", "Skills the worker must load", "`.local/prefs.json` `roles.<name>`",
                     "`domains`", "This overrides step 3", "candidate whose `runtime` is your own runtime",
                     "out of quota", "fall back to the remaining `models`"):
            with self.subTest(dispatch=term):
                self.assertIn(term, dispatch)
        self.assertLess(len((ROOT / "roles/dispatch.md").read_bytes()), 2500)
        self.assertIn("only if the user asked or approves", lead)
        self.assertNotIn("Response Layer", lead)
        self.assertIn("Load every Skill the brief lists", read("roles/build.md"))
        self.assertIn("explicitly approves a wider fix", read("roles/hotfix.md"))
        offers = section(read("router.md"), "Skill Offers")
        for mode in ("`ask`", "`auto`", "`off`", "absent = `ask`"):
            self.assertIn(mode, offers)
        # The entry file is loaded by every session; keep it tiny.
        self.assertLess(len((ROOT / "config/entry.example.md").read_bytes()), 1200)


if __name__ == "__main__":
    unittest.main()
