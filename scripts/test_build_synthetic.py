import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile

from build_synthetic import archive, snapshot


class PackagingTests(unittest.TestCase):
    def test_archive_reproducible_and_relative(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            dataset = root / "default"
            dataset.mkdir()
            (dataset / "manifest.json").write_text("{}")
            first, second = root / "a.zip", root / "b.zip"
            archive(dataset, first)
            archive(dataset, second)
            self.assertEqual(hashlib.sha256(first.read_bytes()).digest(), hashlib.sha256(second.read_bytes()).digest())
            with zipfile.ZipFile(first) as bundle:
                self.assertEqual(bundle.namelist(), ["default/manifest.json"])

    def test_snapshot_uses_commit_not_worktree_and_rejects_cache(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            repo.mkdir()
            def git(*args):
                return subprocess.check_output(["git", "-C", str(repo), *args], stderr=subprocess.DEVNULL)
            git("init")
            fixture = repo / "default_dataset"
            fixture.mkdir()
            (fixture / "manifest.json").write_text("{}")
            git("add", ".")
            git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-m", "fixture")
            (fixture / "manifest.json").write_text("uncommitted")
            (fixture / "secret.env").write_text("not packaged")
            snapshot(repo, "HEAD", "default", root / "export")
            self.assertEqual((root / "export/manifest.json").read_text(), "{}")
            self.assertFalse((root / "export/secret.env").exists())
            snapshot(repo, "HEAD", "default", root / "working", worktree=True)
            self.assertEqual((root / "working/manifest.json").read_text(), "uncommitted")
            self.assertFalse((root / "working/secret.env").exists())
            (fixture / "manifest.json").unlink()
            (fixture / "manifest.json").symlink_to(root / "export/manifest.json")
            with self.assertRaises(ValueError):
                snapshot(repo, "HEAD", "default", root / "symlink", worktree=True)
            (fixture / "cache.duckdb").touch()
            git("add", "default_dataset/cache.duckdb")
            git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-m", "unexpected cache")
            with self.assertRaises(ValueError):
                snapshot(repo, "HEAD", "default", root / "reject")


if __name__ == "__main__":
    unittest.main()
