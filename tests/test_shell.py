"""Regression tests for variant 24."""
import base64
import json
import tempfile
import unittest
from pathlib import Path

from src.main import run_script
from src.shell import Shell, ShellError, load_vfs


def sample():
    """Build a small virtual filesystem."""
    payload = base64.b64encode(b"one\ntwo\nthree\n").decode()
    return {"type": "dir", "children": {
        "docs": {"type": "dir", "children": {
            "note.txt": {"type": "file", "content": payload}}}}}


class ShellTests(unittest.TestCase):
    """Test parsing, navigation, commands, and errors."""

    def setUp(self):
        self.shell = Shell(sample())

    def test_quoted_path(self):
        self.shell.execute('touch "my file.txt"')
        self.assertIn("my file.txt", self.shell.root["children"])

    def test_ls_cd(self):
        self.assertEqual(self.shell.execute("ls"), "docs")
        self.shell.execute("cd docs")
        self.assertEqual(self.shell.cwd, "/docs")
        self.assertEqual(self.shell.execute("ls"), "note.txt")

    def test_find(self):
        self.assertIn("/docs/note.txt", self.shell.execute("find /"))

    def test_tail(self):
        self.assertEqual(self.shell.execute("tail -n 2 docs/note.txt"),
                         "two\nthree")
        self.assertEqual(self.shell.execute("tail -n 0 docs/note.txt"), "")

    def test_cal(self):
        self.assertIn("2026", self.shell.execute("cal 10 2026"))

    def test_touch_in_memory(self):
        self.shell.execute("touch docs/new.txt")
        self.assertEqual(self.shell.execute("ls docs"),
                         "new.txt\nnote.txt")

    def test_exit(self):
        self.shell.execute("exit")
        self.assertFalse(self.shell.running)

    def test_errors(self):
        for command in ("wrong", "ls a b", "cd nowhere", "cd '",
                        "tail docs", "touch /", "cal 13 2026"):
            with self.subTest(command=command):
                with self.assertRaises(ShellError):
                    self.shell.execute(command)

    def test_vfs_invalid(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.json"
            path.write_text('{"type":"file","content":"!"}',
                            encoding="utf-8")
            with self.assertRaises(ShellError):
                load_vfs(path)

    def test_vfs_file_not_changed(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "vfs.json"
            path.write_text(json.dumps(sample()), encoding="utf-8")
            before = path.read_bytes()
            shell = Shell(load_vfs(path))
            shell.execute("touch docs/new.txt")
            self.assertEqual(path.read_bytes(), before)

    def test_script_stops_on_error(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "script.txt"
            path.write_text("touch first\nunknown\ntouch second\n",
                            encoding="utf-8")
            self.assertFalse(run_script(self.shell, path))
            self.assertIn("first", self.shell.root["children"])
            self.assertNotIn("second", self.shell.root["children"])


if __name__ == "__main__":
    unittest.main()

class LsFlagsTests(unittest.TestCase):
    """Exercise ls switches individually and in combinations."""

    def setUp(self):
        root = sample()
        root["children"][".secret"] = {
            "type": "file", "content": base64.b64encode(b"hidden").decode()
        }
        self.shell = Shell(root)

    def test_hidden_entries(self):
        self.assertEqual(self.shell.execute("ls"), "docs")
        self.assertIn(".secret", self.shell.execute("ls -a"))
        self.assertIn(".", self.shell.execute("ls -a").splitlines())

    def test_long_listing(self):
        self.assertIn("drwxr-xr-x", self.shell.execute("ls -l"))
        self.assertIn("6 .secret", self.shell.execute("ls -la"))

    def test_human_readable(self):
        self.assertIn("6B .secret", self.shell.execute("ls -lah"))
        self.assertEqual(self.shell.execute("ls -h"), "docs")

    def test_combined_flags(self):
        self.assertEqual(self.shell.execute("ls -lah"),
                         self.shell.execute("ls -l -a -h"))
        self.assertEqual(self.shell.execute("ls -alh"),
                         self.shell.execute("ls -hla"))
        self.assertIn("note.txt", self.shell.execute("ls -l docs"))

    def test_invalid_flags(self):
        for command in ("ls -z", "ls -laZ", "ls docs missing"):
            with self.subTest(command=command):
                with self.assertRaises(ShellError):
                    self.shell.execute(command)
