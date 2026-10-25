import os
import socket
import unittest
from unittest.mock import Mock

from emulator import ShellEmulatorGUI, VirtualFileSystem, VFSError


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.shell = ShellEmulatorGUI.__new__(ShellEmulatorGUI)
        self.shell.root = Mock()
        self.shell.vfs = VirtualFileSystem(os.path.join(os.path.dirname(__file__),
                                                        '../../../чат гпт/shell_emulator_stage3', 'vfs', 'multi.json'))

    def test_echo_empty_and_text(self):
        self.assertEqual(self.shell.execute_command('echo', []), '')
        self.assertEqual(self.shell.execute_command('echo', ['hello', 'world']), 'hello world')

    def test_who_reports_user_and_host(self):
        result = self.shell.execute_command('who', [])
        self.assertIn(socket.gethostname(), result)
        self.assertTrue(result.split()[0])

    def test_who_rejects_arguments(self):
        with self.assertRaisesRegex(ValueError, 'Использование: who'):
            self.shell.execute_command('who', ['extra'])

    def test_ls_and_cd_work_with_vfs(self):
        self.assertIn('docs/', self.shell.execute_command('ls', ['/']))
        self.assertEqual(self.shell.execute_command('cd', ['/docs']), '')
        self.assertEqual(self.shell.execute_command('pwd', []), '/docs')
        self.assertIn('guide.txt', self.shell.execute_command('ls', []))

    def test_cd_rejects_file_and_missing_path(self):
        with self.assertRaises(VFSError):
            self.shell.execute_command('cd', ['/README.txt'])
        with self.assertRaises(VFSError):
            self.shell.execute_command('cd', ['/missing'])

    def test_command_argument_validation(self):
        with self.assertRaisesRegex(ValueError, 'Использование: ls'):
            self.shell.execute_command('ls', ['/', '/docs'])
        with self.assertRaisesRegex(ValueError, 'Использование: cd'):
            self.shell.execute_command('cd', ['/', '/docs'])


if __name__ == '__main__':
    unittest.main()
