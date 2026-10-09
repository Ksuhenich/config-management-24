"""Stage 1 tests."""
import unittest
from src.shell import Shell, ShellError


class ShellTests(unittest.TestCase):
    def test_quotes(self):
        self.assertIn('two words', Shell().execute('ls "two words"'))

    def test_unknown(self):
        with self.assertRaises(ShellError):
            Shell().execute('unknown')

    def test_exit(self):
        shell = Shell()
        shell.execute('exit')
        self.assertFalse(shell.running)
