"""Portable checks; no root, network, real resident data or third-party dependencies."""
import json
import os
import pwd
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
import xml.etree.ElementTree as ET

SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE))
import workshoplib as w
import workshoprender as render


class Workshop(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.me = pwd.getpwuid(os.getuid()).pw_name
        self.resident = SimpleNamespace(name=self.me, uid=os.getuid(), home=self.home)
        self.env = {**os.environ, "OUTPOST_LIB": str(SOURCE), "WORKSHOP_TEMPLATES": str(SOURCE / "templates"), "WORKSHOP_HOME": str(self.home)}

    def run_cli(self, *args, success=True):
        result = subprocess.run([sys.executable, str(SOURCE / "workshop"), *args], env=self.env, capture_output=True, text=True)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0)
        return result

    def create(self, kind="lantern", name="my-light"):
        self.run_cli("new", kind, name)
        return self.home / "workshop" / name

    def publish(self, name="my-light"):
        self.run_cli("publish", name)
        return self.home / "public_html/workshop" / name

    def test_all_starters_are_private_and_valid(self):
        for kind in ("lantern", "tide", "note", "sound", "tool"):
            self.create(kind, "my-" + kind)
            self.run_cli("check", "my-" + kind)
        self.assertFalse((self.home / "public_html").exists())
        self.assertEqual(w.collect([self.resident]), [])

    def test_publish_selected_files_page_and_attribution(self):
        path = self.create()
        (path / "secret.txt").write_text("not selected")
        (path / ".env").write_text("not selected either")
        public = self.publish()
        works = w.collect([self.resident])
        self.assertEqual(len(works), 1)
        self.assertEqual(works[0]["author"], self.me)
        self.assertTrue(works[0]["archive"])
        self.assertTrue((public / "index.html").is_file())
        with zipfile.ZipFile(public / "source.zip") as archive:
            self.assertNotIn("my-light/secret.txt", archive.namelist())
            self.assertNotIn("my-light/.env", archive.namelist())
            self.assertIn("my-light/frame1.txt", archive.namelist())
        self.assertEqual(w.collect([SimpleNamespace(name=self.me, uid=os.getuid() + 1, home=self.home)]), [])

    def test_private_and_symlinked_manifest_are_not_collected(self):
        self.create(); public = self.publish()
        manifest = public / "outpost.json"
        data = manifest.read_text()
        manifest.chmod(0o600)
        self.assertEqual(w.collect([self.resident]), [])
        manifest.unlink()
        target = self.home / "manifest.json"
        target.write_text(data); target.chmod(0o644)
        manifest.symlink_to(target)
        self.assertEqual(w.collect([self.resident]), [])

    def test_fifo_is_skipped_without_blocking(self):
        fifo = self.home / "fifo"
        os.mkfifo(fifo, 0o644)
        self.assertIsNone(w.read_owned(fifo, os.getuid()))

    def test_ascii_limits_and_color_roles(self):
        base = dict(version=1, title="hello", frames=[["hi"]], files=[])
        for update in ({"frames": [[chr(0x2605)]]}, {"frames": [["x" * 33]]},
                       {"frames": [["x"] * 11]}, {"frames": [["x\x1b[2J"]]},
                       {"colors": [["xx"]]}, {"interval_ms": 50}, {"interval_ms": True}):
            with self.assertRaises(ValueError):
                w.validate(dict(base, **update))
        good = w.validate(dict(base, frames=[["x"], ["xyz", "x"]]))
        self.assertEqual(good["frames"], [["x  ", "   "], ["xyz", "x  "]])

    def test_paths_and_active_links_rejected(self):
        base = dict(version=1, title="hello", frames=[["hi"]], files=[])
        for files in (["../secret"], [".env"], ["a/b.py"]):
            with self.assertRaises(ValueError):
                w.validate(dict(base, files=files))
        for url in ("javascript:alert(1)", "data:text/html,hi", "https://user:pass@example.org/", "https://example.org/a b"):
            with self.assertRaises(ValueError):
                w.validate(dict(base, links=[dict(title="hello", url=url)]))
        self.assertEqual(w.validate(dict(base, links=[dict(title="capsule", url="gemini://example.org/")]))["links"][0]["url"], "gemini://example.org/")

    def test_published_copy_is_explicit_snapshot(self):
        path = self.create(); public = self.publish()
        old = (public / "frame1.txt").read_text()
        (path / "frame1.txt").write_text("changed\n")
        self.assertEqual((public / "frame1.txt").read_text(), old)
        self.publish()
        self.assertEqual((public / "frame1.txt").read_text(), "changed\n")
        self.assertTrue(any((self.home / ".workshop-history").iterdir()))

    def test_withdraw_preserves_private_work_and_portable_pack(self):
        path = self.create(); self.publish()
        self.run_cli("withdraw", "my-light")
        self.assertEqual(w.collect([self.resident]), [])
        self.assertTrue((path / "outpost.json").exists())
        self.run_cli("pack", "my-light")
        self.assertEqual(len(list(self.home.glob("my-light-*.zip"))), 1)

    def test_unmanaged_public_directory_is_preserved(self):
        self.create()
        public = self.home / "public_html/workshop/my-light"
        public.mkdir(parents=True)
        (public / "mine.txt").write_text("keep")
        self.run_cli("publish", "my-light", success=False)
        self.assertEqual((public / "mine.txt").read_text(), "keep")

    def test_remix_permission_and_credit(self):
        path = self.create(); self.publish()
        self.run_cli("fork", self.me + "/my-light", "my-remix", success=False)
        data = json.loads((path / "outpost.json").read_text())
        data["license"] = "CC0-1.0"
        (path / "outpost.json").write_text(json.dumps(data))
        self.publish()
        self.run_cli("fork", self.me + "/my-light", "my-remix")
        remix = json.loads((self.home / "workshop/my-remix/outpost.json").read_text())
        self.assertIn("Remixed from", remix["note"])
        self.assertIn(self.me, remix["note"])
        self.assertEqual(remix["license"], "All rights reserved")
        self.assertFalse((self.home / "public_html/workshop/my-remix").exists())

    def test_archive_traversal_cannot_escape_private_project(self):
        path = self.create()
        data = json.loads((path / "outpost.json").read_text()); data["license"] = "MIT"
        (path / "outpost.json").write_text(json.dumps(data))
        public = self.publish()
        with zipfile.ZipFile(public / "source.zip", "w") as archive:
            archive.writestr("my-light/../../escape", "bad")
        self.run_cli("fork", self.me + "/my-light", "bad-remix", success=False)
        self.assertFalse((self.home / "escape").exists())
        self.assertFalse((self.home / "workshop/bad-remix").exists())

    def test_escaped_html_and_all_protocol_outputs(self):
        path = self.create()
        data = json.loads((path / "outpost.json").read_text())
        data.update(title="<script>no</script>", note="<img src=x onerror=alert(1)>")
        (path / "outpost.json").write_text(json.dumps(data))
        self.publish()
        works = w.collect([self.resident])
        root = self.home / "generated"
        def write(path, value):
            path.parent.mkdir(parents=True, exist_ok=True); path.write_text(value)
        def page(title, body, **kwargs):
            return body
        render.publish(works, write, root / "web", root / "gemini", root / "gopher", page)
        web = (root / "web/commons/index.html").read_text()
        self.assertNotIn("<script>no</script>", web)
        self.assertIn("&lt;script&gt;", web)
        self.assertNotIn("<img src=x", web)
        self.assertIn("```ASCII exhibit", (root / "gemini/commons.gmi").read_text())
        self.assertIn("<script>no</script>", (root / "gopher/commons.txt").read_text())
        ET.parse(root / "web/commons/feed.xml")
        catalogue = json.loads((root / "web/commons/catalogue.json").read_text())
        self.assertEqual(catalogue["works"][0]["author"], self.me)


if __name__ == "__main__":
    unittest.main()
