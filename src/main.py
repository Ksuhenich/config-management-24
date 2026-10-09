"""Command-line entry point for the shell emulator."""
import argparse
import sys
from pathlib import Path

try:
    from .shell import Shell, ShellError
except ImportError:
    from shell import Shell, ShellError


def run_script(shell, path):
    """Echo and execute a script, stopping at its first error."""
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        print(f"Ошибка стартового скрипта: {exc}", file=sys.stderr)
        return False
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        print(shell.prompt + line)
        try:
            result = shell.execute(line)
        except ShellError as exc:
            print(f"Ошибка скрипта, строка {number}: {exc}", file=sys.stderr)
            return False
        if result:
            print(result)
        if not shell.running:
            break
    return True


def main(argv=None):
    """Parse startup options and launch script or interactive REPL."""
    parser = argparse.ArgumentParser(description="Эмулятор UNIX, вариант 24")
    parser.add_argument("--vfs", help="Путь к JSON-файлу VFS")
    parser.add_argument("--script", help="Путь к стартовому скрипту")
    args = parser.parse_args(argv)
    print(f"Конфигурация: VFS={args.vfs!r}, script={args.script!r}")
    try:
        shell = Shell()
    except ShellError as exc:
        print(exc, file=sys.stderr)
        return 1
    if args.script:
        return 0 if run_script(shell, args.script) else 1
    while shell.running:
        try:
            line = input(shell.prompt)
        except (EOFError, KeyboardInterrupt):
            print()
            break
        try:
            output = shell.execute(line)
            if output:
                print(output)
        except ShellError as exc:
            print(f"Ошибка: {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
