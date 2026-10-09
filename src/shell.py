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
            "ls": self.ls, "cd": self.cd,
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

    def ls(self, args):
        """Stage 3 placeholder."""
        return f"ls: {args}"

    def cd(self, args):
        """Stage 3 placeholder."""
        return f"cd: {args}"

    def exit(self, args):
        """Terminate the interactive shell."""
        self.count(args, 0, 0, "exit")
        self.running = False
        return ""
