"""First-stage REPL entry point."""
from .shell import Shell, ShellError


def main(argv=None):
    """Run the interactive shell."""
    shell = Shell()
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
    raise SystemExit(main())
