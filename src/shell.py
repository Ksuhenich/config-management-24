"""First-stage interactive shell prototype."""
import getpass
import shlex
import socket


class ShellError(Exception):
    """Command parsing or execution error."""


class Shell:
    """Interactive command-line prototype."""

    def __init__(self, root=None):
        self.running = True

    @property
    def prompt(self):
        """Show the real host user and machine name."""
        return f"{getpass.getuser()}@{socket.gethostname()}:/$ "

    def execute(self, line):
        """Parse quotes and dispatch stub commands."""
        try:
            args = shlex.split(line)
        except ValueError as exc:
            raise ShellError(f"Ошибка кавычек: {exc}") from exc
        if not args:
            return ""
        name, *values = args
        if name in ("ls", "cd"):
            return f"{name}: {values}"
        if name == "exit":
            if values:
                raise ShellError("exit: лишние аргументы")
            self.running = False
            return ""
        raise ShellError(f"Неизвестная команда: {name}")
