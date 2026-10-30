import os
import tempfile
import unittest
from pathlib import Path
from emulator import VirtualFileSystem, VFSError


class Stage5Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.json_path = Path(self.temp.name) / 'vfs.json'
        self.json_path.write_text('''{"root":{"type":"dir","children":{"empty":{"type":"dir","children":{}},"full":{"type":"dir","children":{"note.txt":{"type":"file","content":"hello"}}}}}}''', encoding='utf-8')
        self.vfs = VirtualFileSystem(str(self.json_path))

    def tearDown(self):
        self.temp.cleanup()

    def test_rmdir_empty_directory(self):
        self.vfs.rmdir('/empty')
        with self.assertRaises(VFSError):
            self.vfs._node('/empty')

    def test_rmdir_rejects_nonempty_directory(self):
        with self.assertRaisesRegex(VFSError, 'Каталог не пуст'):
            self.vfs.rmdir('/full')

    def test_rmdir_rejects_file_and_root(self):
        with self.assertRaises(VFSError):
            self.vfs.rmdir('/full/note.txt')
        with self.assertRaises(VFSError):
            self.vfs.rmdir('/')

    def test_rmdir_rejects_current_directory(self):
        self.vfs.cd('/empty')
        with self.assertRaises(VFSError):
            self.vfs.rmdir('/empty')

    def test_chown_owner_and_group(self):
        self.vfs.chown('alice:staff', '/full/note.txt')
        node = self.vfs._node('/full/note.txt')
        self.assertEqual(node['owner'], 'alice')
        self.assertEqual(node['group'], 'staff')

    def test_chown_recursive(self):
        self.vfs.chown('bob:dev', '/full', recursive=True)
        self.assertEqual(self.vfs._node('/full')['owner'], 'bob')
        self.assertEqual(self.vfs._node('/full/note.txt')['group'], 'dev')

    def test_chown_rejects_invalid_spec_and_missing_path(self):
        for spec in ('', ':staff', 'alice:', 'a:b:c'):
            with self.assertRaises(VFSError):
                self.vfs.chown(spec, '/full')
        with self.assertRaises(VFSError):
            self.vfs.chown('alice', '/missing')

    def test_changes_are_not_written_to_json(self):
        before = self.json_path.read_text(encoding='utf-8')
        self.vfs.chown('alice:staff', '/full')
        self.vfs.rmdir('/empty')
        after = self.json_path.read_text(encoding='utf-8')
        self.assertEqual(before, after)


if __name__ == '__main__':
    unittest.main()
