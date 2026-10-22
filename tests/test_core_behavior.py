"""Portable behavior checks; never use the caller's runtime or skill directories."""
import contextlib
import io
import multiprocessing
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import doctor
import local_state
from platform_fs import create_dir_link, is_linkish, points_to, remove_linkish
from sync_skills import sync_central_dir, sync_per_skill


def increment_worker(directory, count):
    local_state.LOCAL = Path(directory)
    local_state.FILES = {kind: Path(directory) / f"{kind}.json" for kind in ("runtime", "state")}
    for _ in range(count):
        def increment(data):
            data["count"] = data.get("count", 0) + 1
        local_state.update_kind("state", increment)


class CoreBehaviorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="prompt behavior ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.central = self.root / "central skills"
        self.central.mkdir()
        self.target = self.root / "runtime skills"
        self.entry = {"enabled": True, "executable": sys.executable,
                      "auto_sync_skills": True, "skills_sync_mode": "per-skill-link",
                      "skills_path": str(self.target)}
        self.output = io.StringIO()
        self.redirect = contextlib.redirect_stdout(self.output)
        self.redirect.__enter__()
        self.addCleanup(self.redirect.__exit__, None, None, None)
        doctor.fail = False

    def skill(self, name):
        directory = self.central / name
        directory.mkdir()
        (directory / "SKILL.md").write_text("test", encoding="utf-8")
        return directory

    def test_sync_lifecycle_and_private_data(self):
        first = self.skill("first")
        second = self.skill("second")
        self.skill("private")
        self.target.mkdir()
        private = self.target / "private"
        private.mkdir()
        sentinel = private / "keep.txt"
        sentinel.write_text("user data", encoding="utf-8")
        changed, _, record = sync_per_skill("sample", self.entry, self.central, self.target, {})
        self.assertTrue(changed)
        self.assertEqual(record["conflicts"], ["private"])
        self.assertTrue(points_to(self.target / "first", first))
        changed, _, record = sync_per_skill("sample", self.entry, self.central, self.target, record)
        self.assertFalse(changed)
        # A user-repointed link must survive even after its source skill disappears.
        external = self.root / "user source"
        external.mkdir()
        remove_linkish(self.target / "second")
        create_dir_link(external, self.target / "second")
        (first / "SKILL.md").unlink()
        (second / "SKILL.md").unlink()
        changed, _, record = sync_per_skill("sample", self.entry, self.central, self.target, record)
        self.assertTrue(changed)
        self.assertFalse((self.target / "first").exists())
        self.assertTrue(points_to(self.target / "second", external))
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "user data")
        self.assertTrue(external.is_dir())

    def test_symlinked_skill_links_through_stable_path(self):
        # A machine-local skill: central/<name> -> stable alias -> versioned install.
        versions = self.root / "app"
        for version in ("1.0", "2.0"):
            (versions / version / "local").mkdir(parents=True)
            (versions / version / "local" / "SKILL.md").write_text(version, encoding="utf-8")
        alias = self.root / "active"
        alias.symlink_to(versions / "1.0" / "local", target_is_directory=True)
        (self.central / "local").symlink_to(alias, target_is_directory=True)
        self.target.mkdir()
        # Legacy state: the runtime link was created against the resolved versioned path.
        legacy = versions / "1.0" / "local"
        create_dir_link(legacy, self.target / "local")
        previous = {"central": str(self.central.resolve()), "target": str(self.target.resolve()),
                    "mode": "per-skill-link", "managed": {"local": str(legacy.resolve())}}
        changed, _, record = sync_per_skill("sample", self.entry, self.central, self.target, previous)
        self.assertTrue(changed)
        stable = self.central.resolve() / "local"
        self.assertEqual(Path(os.readlink(self.target / "local")), stable)
        alias.unlink()
        alias.symlink_to(versions / "2.0" / "local", target_is_directory=True)
        changed, _, record = sync_per_skill("sample", self.entry, self.central, self.target, record)
        self.assertFalse(changed)
        self.assertEqual((self.target / "local" / "SKILL.md").read_text(encoding="utf-8"), "2.0")
        (self.central / "local").unlink()
        changed, _, _ = sync_per_skill("sample", self.entry, self.central, self.target, record)
        self.assertTrue(changed)
        self.assertFalse(is_linkish(self.target / "local"))

    def test_central_link_and_conflict(self):
        changed, _, _ = sync_central_dir("sample", self.entry, self.central, self.target)
        self.assertTrue(changed)
        self.assertFalse(sync_central_dir("sample", self.entry, self.central, self.target)[0])
        entry = dict(self.entry, skills_sync_mode="central-dir-link")
        doctor.check_runtime_skills("sample", entry, self.central, set())
        self.assertFalse(doctor.fail)
        remove_linkish(self.target)
        self.target.mkdir()
        with self.assertRaises(RuntimeError):
            sync_central_dir("sample", self.entry, self.central, self.target)
        self.assertTrue(self.target.is_dir())
        doctor.check_runtime_skills("sample", entry, self.central, set())
        self.assertTrue(doctor.fail)

    def test_doctor_deployment_modes(self):
        self.skill("one")
        for mode in ("per-skill-link", "central-dir-link"):
            for auto, executable, enabled, expected in (
                (True, sys.executable, True, True),
                (False, sys.executable, True, False),
                (True, str(self.root / "absent"), True, False),
                (True, sys.executable, False, False),
            ):
                with self.subTest(mode=mode, auto=auto, executable=executable, enabled=enabled):
                    doctor.fail = False
                    entry = dict(self.entry, skills_sync_mode=mode, auto_sync_skills=auto,
                                 executable=executable, enabled=enabled)
                    doctor.check_runtime_skills("sample", entry, self.central, {"one"})
                    self.assertEqual(doctor.fail, expected)
        sync_per_skill("sample", self.entry, self.central, self.target, {})
        doctor.fail = False
        doctor.check_runtime_skills("sample", self.entry, self.central, {"one"})
        self.assertFalse(doctor.fail)
        remove_linkish(self.target / "one")
        create_dir_link(self.root, self.target / "one")
        doctor.check_runtime_skills("sample", self.entry, self.central, {"one"})
        self.assertTrue(doctor.fail)
        remove_linkish(self.target / "one")

    def test_doctor_credentials_and_review_args(self):
        doctor.check_local_credentials(self.root)
        self.assertFalse(doctor.fail)
        directory = self.root / "credentials"
        directory.mkdir()
        (directory / "sample.key").write_text("synthetic-test-value", encoding="utf-8")
        doctor.check_local_credentials(self.root)
        self.assertTrue(doctor.fail)
        self.assertNotIn("synthetic-test-value", self.output.getvalue())
        entry = dict(self.entry, capabilities=["review"], runtime_identity="sample", review={"args": []})
        with patch.object(doctor, "warn") as warning:
            doctor.check_runtime_entry("sample", entry, self.root / "router.md")
            warning.assert_not_called()
        entry.pop("runtime_identity")
        entry["review"] = {}
        with patch.object(doctor, "warn") as warning:
            doctor.check_runtime_entry("sample", entry, self.root / "router.md")
            self.assertEqual(warning.call_count, 2)

    def test_unset_null_and_missing(self):
        data = {"nested": {"value": None}}
        self.assertTrue(local_state.unset_value(data, "nested.value"))
        self.assertEqual(data, {"nested": {}})
        self.assertFalse(local_state.unset_value(data, "nested.value"))

    def test_migrate_moves_legacy_user_prefs_out_of_state(self):
        directory = self.root / "local"
        files = {kind: directory / f"{kind}.json" for kind in ("runtime", "state", "prefs")}
        with patch.object(local_state, "LOCAL", directory), patch.object(local_state, "FILES", files):
            local_state.ensure_files()
            local_state.update_kind("state", lambda data: data.update(user_prefs={"response_profile": "p.md"}))
            local_state.migrate_local_files()
            self.assertEqual(local_state.read_kind("prefs"), {"response_profile": "p.md"})
            self.assertNotIn("user_prefs", local_state.read_kind("state"))
            local_state.migrate_local_files()
            self.assertEqual(local_state.read_kind("prefs"), {"response_profile": "p.md"})

    def test_contended_empty_lock_file_waits_instead_of_writing(self):
        target = self.root / "state.json"
        lock = self.root / "state.json.lock"
        lock.touch()
        with open(lock, "a+b") as holder:
            self.assertTrue(local_state._try_lock(holder))
            try:
                with patch.object(local_state, "LOCK_TIMEOUT", 0.2):
                    with self.assertRaises(TimeoutError):
                        with local_state._file_lock(target):
                            pass
            finally:
                local_state._unlock(holder)
        with local_state._file_lock(target):
            pass

    def test_cross_process_updates(self):
        directory = self.root / "local state"
        ctx = multiprocessing.get_context("spawn")
        processes = [ctx.Process(target=increment_worker, args=(str(directory), 30)) for _ in range(4)]
        try:
            for process in processes:
                process.start()
            for process in processes:
                process.join(timeout=30)
                self.assertEqual(process.exitcode, 0)
            data = local_state._read_path(directory / "state.json")
            self.assertEqual(data["count"], 120)
            self.assertEqual(list(directory.glob("*.tmp")), [])
        finally:
            for process in processes:
                if process.pid is not None:
                    if process.is_alive():
                        process.terminate()
                    process.join(timeout=5)
                    if process.is_alive():
                        process.kill()
                        process.join(timeout=5)
                    process.close()


if __name__ == "__main__":
    unittest.main()
