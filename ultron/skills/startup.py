from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "ULTRON"


def _launch_command() -> str:
    root = Path(__file__).resolve().parents[1]
    launcher = root / "scripts" / "launch_ultron.ps1"
    return (
        f'powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass '
        f'-File "{launcher}" voice'
    )


def startup_status() -> tuple[bool, str]:
    if os.name != "nt":
        return False, "Windows startup management is unavailable on this system."
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            value, _ = winreg.QueryValueEx(key, VALUE_NAME)
    except FileNotFoundError:
        return False, "ULTRON automatic startup is disabled."
    expected = _launch_command()
    if str(value).strip() != expected:
        return False, "An outdated ULTRON startup entry exists."
    return True, "ULTRON automatic startup is enabled for Windows sign-in."


def enable_startup() -> str:
    if os.name != "nt":
        return "Automatic startup is currently implemented for Windows, Boss."
    import winreg

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
        winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, _launch_command())
    return (
        "ULTRON automatic startup is enabled, Boss. It will open in voice mode "
        "after you sign in to Windows."
    )


def disable_startup() -> str:
    if os.name != "nt":
        return "Automatic startup is currently implemented for Windows, Boss."
    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            RUN_KEY,
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            winreg.DeleteValue(key, VALUE_NAME)
    except FileNotFoundError:
        pass
    return "ULTRON automatic startup is disabled, Boss."


def _startup(args, brain) -> str:
    action = args[0].strip('"').lower() if args else "status"
    if action in {"on", "enable", "enabled", "start"}:
        return enable_startup()
    if action in {"off", "disable", "disabled", "stop"}:
        return disable_startup()
    if action in {"status", "check"}:
        return startup_status()[1] + " Boss."
    if action in {"test", "launch"}:
        if platform.system() != "Windows":
            return "Startup testing is currently implemented for Windows, Boss."
        subprocess.Popen(
            [
                "powershell.exe",
                "-NoLogo",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(Path(__file__).resolve().parents[1] / "scripts" / "launch_ultron.ps1"),
                "voice",
            ]
        )
        return "Started another ULTRON voice session for testing, Boss."
    return "Usage: /startup <on|off|status|test>, Boss."


def register(registry) -> None:
    registry.register(
        "startup",
        _startup,
        "<on|off|status|test> manage Windows login startup",
    )
