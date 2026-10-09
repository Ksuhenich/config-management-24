"""In-memory UNIX-like shell for practical assignment variant 24."""
import base64
import binascii
import calendar
import datetime
import getpass
import json
import os
import posixpath
import shlex
import socket


class ShellError(Exception):
    """An invalid command or virtual filesystem operation."""


def directory(children=None):
    """Create a directory node."""
    return {"type": "dir", "children": children or {}}


def validate(node):
    """Validate a JSON VFS tree and its base64 payloads."""
    if not isinstance(node, dict):
        raise ShellError("VFS: узел должен быть объектом")
    if node.get("type") == "dir":
        children = node.get("children")
        if not isinstance(children, dict):
            raise ShellError("VFS: неверный список элементов")
        for name, child in children.items():
            if (not isinstance(name, str) or not name or
                    name in (".", "..") or "/" in name):
                raise ShellError("VFS: неверное имя элемента")
            validate(child)
    elif node.get("type") == "file":
        payload = node.get("content")
        if not isinstance(payload, str):
            raise ShellError("VFS: неверное содержимое файла")
        try:
            base64.b64decode(payload, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ShellError("VFS: неверный base64") from exc
    else:
        raise ShellError("VFS: неизвестный тип узла")


def load_vfs(path):
    """Load and validate a VFS without modifying its source."""
    if path is None:
        return directory()
    try:
        with open(path, encoding="utf-8") as source:
            root = json.load(source)
    except (OSError, UnicodeError, ValueError) as exc:
        raise ShellError(f"Ошибка загрузки VFS: {exc}") from exc
    validate(root)
    if root["type"] != "dir":
        raise ShellError("VFS: корень должен быть каталогом")
    return root


class Shell:
    """Stateful shell whose mutations are confined to memory."""

    def __init__(self, root=None):
        self.root = root if root is not None else directory()
        self.cwd = "/"
        self.running = True

    @property
    def prompt(self):
        """Render the host username and hostname."""
        return f"{getpass.getuser()}@{socket.gethostname()}:{self.cwd}$ "

    def resolve(self, path):
        """Normalize an absolute or relative virtual path."""
        result = posixpath.normpath(posixpath.join(self.cwd, path))
        return result if result.startswith("/") else "/" + result

    def node(self, path):
        """Find a virtual node, raising on missing paths."""
        absolute = self.resolve(path)
        current = self.root
        for part in absolute.strip("/").split("/") if absolute != "/" else []:
            if current["type"] != "dir":
                raise ShellError(f"Не каталог: {absolute}")
            if part not in current["children"]:
                raise ShellError(f"Не найдено: {absolute}")
            current = current["children"][part]
        return current

    def execute(self, line):
        """Parse and execute one command; return its printable output."""
        try:
            args = shlex.split(line, posix=True)
        except ValueError as exc:
            raise ShellError(f"Ошибка кавычек: {exc}") from exc
        if not args:
            return ""
        name, *values = args
        commands = {
            "ls": self.ls, "cd": self.cd, "find": self.find,
            "tail": self.tail, "cal": self.cal, "touch": self.touch,
            "exit": self.exit,
        }
        if name not in commands:
            raise ShellError(f"Неизвестная команда: {name}")
        return commands[name](values)

    @staticmethod
    def count(args, minimum, maximum, name):
        """Validate the number of command arguments."""
        if not minimum <= len(args) <= maximum:
            raise ShellError(f"{name}: неверное количество аргументов")

    @staticmethod
    def human_size(size):
        """Convert a byte count into a human-readable size."""
        for unit in ("B", "K", "M", "G", "T"):
            if size < 1024 or unit == "T":
                return f"{size}B" if unit == "B" else f"{size:g}{unit}"
            size /= 1024

    @staticmethod
    def entry_size(node):
        """Return file content size in bytes; directories have size zero."""
        if node["type"] == "dir":
            return 0
        return len(base64.b64decode(node["content"]))

    def ls(self, args):
        """List VFS entries with -l, -a, -h and combined flags."""
        flags = set()
        paths = []
        for arg in args:
            if arg.startswith("-") and arg != "-":
                if arg == "--":
                    continue
                if not set(arg[1:]) <= {"l", "a", "h"}:
                    raise ShellError(f"ls: неизвестный флаг: {arg}")
                flags.update(arg[1:])
            else:
                paths.append(arg)
        self.count(paths, 0, 1, "ls")
        path = paths[0] if paths else "."
        target = self.node(path)
        if target["type"] == "file":
            entries = [(posixpath.basename(self.resolve(path)), target)]
        else:
            entries = list(target["children"].items())
            if "a" in flags:
                entries += [(".", target), ("..", self.node(
                    posixpath.join(path, "..")))]
        entries = sorted((name, node) for name, node in entries
                         if "a" in flags or not name.startswith("."))
        if "l" not in flags:
            return "\n".join(name for name, _ in entries)
        lines = []
        for name, node in entries:
            kind = "d" if node["type"] == "dir" else "-"
            size = self.entry_size(node)
            displayed = self.human_size(size) if "h" in flags else str(size)
            lines.append(f"{kind}rwxr-xr-x 1 vfs vfs {displayed:>5} {name}")
        return "\n".join(lines)

    def cd(self, args):
        """Change the current virtual directory."""
        self.count(args, 0, 1, "cd")
        path = args[0] if args else "/"
        if self.node(path)["type"] != "dir":
            raise ShellError(f"cd: не каталог: {path}")
        self.cwd = self.resolve(path)
        return ""

    def find(self, args):
        """Recursively list paths below a directory or file."""
        self.count(args, 0, 1, "find")
        path = self.resolve(args[0] if args else ".")
        found = []

        def visit(node, current):
            found.append(current)
            if node["type"] == "dir":
                for name, child in sorted(node["children"].items()):
                    visit(child, posixpath.join(current, name))

        visit(self.node(path), path)
        return "\n".join(found)

    def tail(self, args):
        """Display the final ten lines or -n N lines of a text file."""
        if len(args) == 3 and args[0] == "-n":
            try:
                limit = int(args[1])
            except ValueError as exc:
                raise ShellError("tail: неверное число строк") from exc
            path = args[2]
        else:
            self.count(args, 1, 1, "tail")
            limit, path = 10, args[0]
        if limit < 0:
            raise ShellError("tail: число строк не может быть отрицательным")
        node = self.node(path)
        if node["type"] != "file":
            raise ShellError("tail: требуется файл")
        content = base64.b64decode(node["content"])
        try:
            lines = content.decode("utf-8").splitlines()
        except UnicodeDecodeError as exc:
            raise ShellError("tail: файл не является текстовым UTF-8") from exc
        return "\n".join(lines[-limit:] if limit else [])

    def cal(self, args):
        """Show the current month or a specified month and year."""
        if not args:
            today = datetime.date.today()
            month, year = today.month, today.year
        elif len(args) == 2:
            try:
                month, year = map(int, args)
            except ValueError as exc:
                raise ShellError("cal: нужны числовые месяц и год") from exc
        else:
            raise ShellError("cal: формат cal [месяц год]")
        if not 1 <= month <= 12 or not 1 <= year <= 9999:
            raise ShellError("cal: неверная дата")
        return calendar.month(year, month).rstrip()

    def touch(self, args):
        """Create a zero-byte virtual file if absent."""
        self.count(args, 1, 1, "touch")
        path = self.resolve(args[0])
        if path == "/":
            raise ShellError("touch: нельзя изменить корень")
        parent = self.node(posixpath.dirname(path))
        if parent["type"] != "dir":
            raise ShellError("touch: родитель не каталог")
        name = posixpath.basename(path)
        existing = parent["children"].get(name)
        if existing is not None and existing["type"] != "file":
            raise ShellError("touch: путь является каталогом")
        if existing is None:
            parent["children"][name] = {"type": "file", "content": ""}
        return ""

    def exit(self, args):
        """Terminate the interactive shell."""
        self.count(args, 0, 0, "exit")
        self.running = False
        return ""
