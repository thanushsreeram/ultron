from __future__ import annotations

import subprocess
import sys


def _code(args, brain) -> str:
    request = " ".join(args).strip('"')
    if not request:
        return "Tell me what code to generate, explain, or debug, Boss."
    return brain.chat(
        request,
        extra_system=(
            "You are also a senior coding assistant. Give correct, secure, runnable "
            "solutions. Explain important decisions and flag destructive operations."
        ),
    )


def _run_python(args, brain) -> str:
    if not args:
        return 'Usage: /runpy "script.py" [arguments], Boss.'
    script = args[0].strip('"')
    path = brain.settings.workspace / script
    if not path.is_absolute():
        path = brain.settings.workspace / path
    path = path.resolve()
    try:
        path.relative_to(brain.settings.workspace.resolve())
    except ValueError:
        if not brain.settings.allow_outside_workspace:
            return f"Code execution is limited to {brain.settings.workspace}, Boss."
    if not path.is_file():
        return f"I cannot find {path}, Boss."
    if not brain.confirm(f"Run Python script {path.name}? It can modify your computer."):
        return "Code execution cancelled, Boss."
    result = subprocess.run(
        [sys.executable, str(path), *[arg.strip('"') for arg in args[1:]]],
        cwd=path.parent,
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = (result.stdout + result.stderr).strip()
    return f"Exit code: {result.returncode}\n{output or '(no output)'}"


def register(registry) -> None:
    registry.register("code", _code, "<request> generate, explain, or debug code")
    registry.register("runpy", _run_python, "<script.py> [args] run a Python script")
