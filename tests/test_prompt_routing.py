"""Regression checks for progressive prompt loading and route boundaries."""
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class PromptRoutingTests(unittest.TestCase):
    def test_router_starts_light_and_supports_escalation(self):
        router = read("router.md")
        self.assertIn("Always begin with the lightest sufficient route", router)
        self.assertIn("Routes are per current intent, not permanent conversation labels", router)
        self.assertIn("Direct -> Skill-first", router)
        self.assertIn("Direct or Skill-first -> Engineering", router)

    def test_direct_and_skill_first_do_not_require_high(self):
        router = read("router.md")
        self.assertIn("Do **not** load `models/high.md` for Direct requests", router)
        self.assertIn("A matching Skill does not by itself require `models/high.md`", router)
        self.assertIn("Code-related subject matter alone is not enough to select this route", router)

    def test_high_is_engineering_only(self):
        high = read("models/high.md")
        self.assertIn("Load only after `router.md` selects the Engineering route", high)
        self.assertIn("**Engineering analyst:**", high)
        self.assertNotIn("**Problem solver:**", high)

    def test_common_stays_free_of_engineering_delivery_policy(self):
        common = read("common.md")
        for engineering_only_text in (
            "make the smallest necessary change",
            "Perform task-appropriate validation",
            "Final reports:",
            "cleanup/intentional retention",
        ):
            self.assertNotIn(engineering_only_text, common)

    def test_on_demand_policies_exist(self):
        router = read("router.md")
        for path in (
            "capabilities/runtime.md",
            "capabilities/skill-maintenance.md",
        ):
            self.assertIn(path, router)
            self.assertTrue((ROOT / path).is_file())

    def test_always_loaded_prompt_budget(self):
        router = read("router.md").encode("utf-8")
        common = read("common.md").encode("utf-8")
        self.assertLess(len(router), 4200, "router.md should remain a lightweight dispatcher")
        self.assertLess(len(common), 1200, "common.md should contain only globally useful rules")


if __name__ == "__main__":
    unittest.main()
