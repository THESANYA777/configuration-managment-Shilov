import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from practice1.emulator import VirtualFileSystem, VFSError


class VirtualFileSystemTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "vfs.json"
        self.path.write_text(json.dumps({
            "root": {"type": "dir", "children": {
                "a": {"type": "dir", "children": {
                    "b": {"type": "dir", "children": {
                        "hello.txt": {"type": "file", "content": "hello"}
                    }}
                }},
                "file.txt": {"type": "file", "content": "root file"}
            }}
        }), encoding="utf-8")
        self.vfs = VirtualFileSystem(str(self.path))

    def tearDown(self):
        self.temp.cleanup()

    def test_ls_root(self):
        self.assertIn("a/", self.vfs.ls("/"))
        self.assertIn("file.txt", self.vfs.ls("/"))

    def test_cd_and_relative_cat(self):
        self.vfs.cd("/a/b")
        self.assertEqual(self.vfs.pwd(), "/a/b")
        self.assertEqual(self.vfs.cat("hello.txt"), "hello")

    def test_parent_navigation(self):
        self.vfs.cd("/a/b")
        self.vfs.cd("..")
        self.assertEqual(self.vfs.pwd(), "/a")

    def test_tree_nested(self):
        self.assertIn("hello.txt", self.vfs.tree("/a"))

    def test_missing_path_raises(self):
        with self.assertRaises(VFSError):
            self.vfs.ls("/missing")

    def test_json_is_not_modified(self):
        before = self.path.read_bytes()
        self.vfs.cd("/a")
        self.vfs.ls("/")
        self.assertEqual(before, self.path.read_bytes())


if __name__ == "__main__":
    unittest.main()
