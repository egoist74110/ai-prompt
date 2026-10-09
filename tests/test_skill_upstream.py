"""Offline checks for vendored-Skill tracking; no network access."""
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import skill_upstream


def write(base: Path, files: dict) -> Path:
    for rel, data in files.items():
        path = base / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return base


class UpstreamSidecarTests(unittest.TestCase):
    def test_sidecars_are_valid(self):
        sidecars = sorted(ROOT.glob("skills/*/UPSTREAM.json"))
        self.assertTrue(sidecars)
        for path in sidecars:
            with self.subTest(skill=path.parent.name):
                meta = json.loads(path.read_text(encoding="utf-8"))
                self.assertRegex(meta["repo"], r"^[\w.-]+/[\w.-]+$")
                self.assertIsInstance(meta["path"], str)
                self.assertTrue(meta["ref"])
                commit = meta.get("commit")
                self.assertTrue(commit is None or re.fullmatch(r"[0-9a-f]{40}", commit))
                self.assertIn("local_changes", meta)
                self.assertNotRegex(json.dumps(meta), r"/Users/|[A-Za-z]:\\\\")

    def test_router_offers_skills_and_checks_freshness(self):
        router = (ROOT / "router.md").read_text(encoding="utf-8")
        body = router.split("## Skill Offers", 1)[1].split("\n## ", 1)[0]
        for term in ("offer", "until the user agrees", "Declined", "Headless", "UPSTREAM.json", "skill_upstream.py check"):
            self.assertIn(term, body)


class PlanUpdateTests(unittest.TestCase):
    def plan(self, local, base, new):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            actions = skill_upstream.plan_update(
                write(root / "local", local), write(root / "base", base), write(root / "new", new), [], root
            )
            return {rel: (action, payload) for rel, action, payload in actions}

    def test_untouched_local_files_follow_upstream(self):
        plan = self.plan(
            {"SKILL.md": b"a\n", "old.md": b"x\n"},
            {"SKILL.md": b"a\n", "old.md": b"x\n"},
            {"SKILL.md": b"b\n", "new.md": b"n\n"},
        )
        self.assertEqual(plan["SKILL.md"], ("update", b"b\n"))
        self.assertEqual(plan["new.md"], ("add", b"n\n"))
        self.assertEqual(plan["old.md"][0], "delete")

    def test_local_edits_merge_or_conflict(self):
        base = b"one\ntwo\nthree\nfour\nfive\n"
        clean = self.plan({"S.md": base.replace(b"one", b"ONE")}, {"S.md": base}, {"S.md": base.replace(b"five", b"FIVE")})
        self.assertEqual(clean["S.md"], ("update", b"ONE\ntwo\nthree\nfour\nFIVE\n"))
        clash = self.plan({"S.md": base.replace(b"one", b"mine")}, {"S.md": base}, {"S.md": base.replace(b"one", b"theirs")})
        self.assertEqual(clash["S.md"][0], "conflict")
        self.assertIn(b"<<<<<<< local", clash["S.md"][1])

    def test_local_only_choices_are_preserved(self):
        plan = self.plan(
            {"kept.md": b"mine\n"},
            {"kept.md": b"base\n", "dropped.md": b"base\n"},
            {"dropped.md": b"changed\n"},
        )
        self.assertEqual(plan["kept.md"][0], "keep")
        self.assertEqual(plan["dropped.md"][0], "skip")


if __name__ == "__main__":
    unittest.main()
