from __future__ import annotations

import os
import platform
import json
import re
import shutil
import subprocess
import time
import urllib.parse
import webbrowser
from pathlib import Path


WINDOWS_APPS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "paint": "mspaint.exe",
    "terminal": "wt.exe",
    "powershell": "powershell.exe",
    "command prompt": "cmd.exe",
    "cmd": "cmd.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "the chrome": "chrome.exe",
    "edge": "msedge.exe",
    "microsoft edge": "msedge.exe",
    "firefox": "firefox.exe",
    "mozilla firefox": "firefox.exe",
    "brave": "brave.exe",
    "brave browser": "brave.exe",
    "comet": "comet.exe",
    "commet": "comet.exe",
    "vscode": "code.exe",
    "vs code": "code.exe",
    "visual studio code": "code.exe",
    "word": "winword.exe",
    "microsoft word": "winword.exe",
    "excel": "excel.exe",
    "microsoft excel": "excel.exe",
    "powerpoint": "powerpnt.exe",
    "microsoft powerpoint": "powerpnt.exe",
    "outlook": "outlook.exe",
    "spotify": "spotify.exe",
    "whatsapp": "whatsapp.exe",
    "chatgpt": "chatgpt.exe",
    "teams": "ms-teams.exe",
    "microsoft teams": "ms-teams.exe",
    "steam": "steam.exe",
    "xbox": "xbox.exe",
    "epic games": "EpicGamesLauncher.exe",
    "epic games launcher": "EpicGamesLauncher.exe",
}

WINDOWS_APP_PATHS = {
    "chrome.exe": [
        Path(os.environ.get("PROGRAMFILES", "")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", ""))
        / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("LOCALAPPDATA", ""))
        / "Google/Chrome/Application/chrome.exe",
    ],
    "msedge.exe": [
        Path(os.environ.get("PROGRAMFILES", ""))
        / "Microsoft/Edge/Application/msedge.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", ""))
        / "Microsoft/Edge/Application/msedge.exe",
    ],
    "firefox.exe": [
        Path(os.environ.get("PROGRAMFILES", "")) / "Mozilla Firefox/firefox.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Mozilla Firefox/firefox.exe",
    ],
    "brave.exe": [
        Path(os.environ.get("PROGRAMFILES", ""))
        / "BraveSoftware/Brave-Browser/Application/brave.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", ""))
        / "BraveSoftware/Brave-Browser/Application/brave.exe",
        Path(os.environ.get("LOCALAPPDATA", ""))
        / "BraveSoftware/Brave-Browser/Application/brave.exe",
    ],
    "comet.exe": [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Perplexity/Comet/Application/comet.exe",
    ],
    "code.exe": [
        Path(os.environ.get("LOCALAPPDATA", ""))
        / "Programs/Microsoft VS Code/Code.exe",
        Path(os.environ.get("PROGRAMFILES", "")) / "Microsoft VS Code/Code.exe",
    ],
    "spotify.exe": [
        Path(os.environ.get("APPDATA", "")) / "Spotify/Spotify.exe",
    ],
    "steam.exe": [
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Steam/steam.exe",
        Path(os.environ.get("PROGRAMFILES", "")) / "Steam/steam.exe",
    ],
    "epicgameslauncher.exe": [
        Path(os.environ.get("PROGRAMFILES(X86)", ""))
        / "Epic Games/Launcher/Portal/Binaries/Win64/EpicGamesLauncher.exe",
        Path(os.environ.get("PROGRAMFILES", ""))
        / "Epic Games/Launcher/Portal/Binaries/Win64/EpicGamesLauncher.exe",
    ],
}

_START_APPS_CACHE: list[dict[str, str]] | None = None


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _windows_start_apps() -> list[dict[str, str]]:
    global _START_APPS_CACHE
    if _START_APPS_CACHE is not None:
        return _START_APPS_CACHE
    command = (
        "Get-StartApps | Select-Object Name,AppID | "
        "ConvertTo-Json -Compress"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if result.returncode != 0 or not result.stdout.strip():
            _START_APPS_CACHE = []
            return _START_APPS_CACHE
        data = json.loads(result.stdout)
        if isinstance(data, dict):
            data = [data]
        _START_APPS_CACHE = [
            {"name": str(item["Name"]), "app_id": str(item["AppID"])}
            for item in data
            if item.get("Name") and item.get("AppID")
        ]
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        _START_APPS_CACHE = []
    return _START_APPS_CACHE


def _find_start_app(name: str) -> dict[str, str] | None:
    query = _normalize(name)
    if not query:
        return None
    apps = _windows_start_apps()
    exact = [app for app in apps if _normalize(app["name"]) == query]
    if exact:
        return exact[0]
    starts = [app for app in apps if _normalize(app["name"]).startswith(query)]
    if len(starts) == 1:
        return starts[0]
    contains = [
        app
        for app in apps
        if query in _normalize(app["name"]) or _normalize(app["name"]) in query
    ]
    return contains[0] if len(contains) == 1 else None


def _launch_start_app(app_id: str) -> None:
    if app_id.startswith(("http://", "https://", "steam://", "file://")):
        os.startfile(app_id)
        return
    if Path(app_id).expanduser().exists():
        os.startfile(str(Path(app_id).expanduser()))
        return
    subprocess.Popen(
        ["explorer.exe", rf"shell:AppsFolder\{app_id}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _registry_app_path(executable: str) -> str | None:
    try:
        import winreg
    except ImportError:
        return None

    subkey = rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{executable}"
    locations = (
        (winreg.HKEY_CURRENT_USER, subkey),
        (winreg.HKEY_LOCAL_MACHINE, subkey),
        (
            winreg.HKEY_LOCAL_MACHINE,
            rf"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\{executable}",
        ),
    )
    for hive, key_name in locations:
        try:
            with winreg.OpenKey(hive, key_name) as key:
                value, _ = winreg.QueryValueEx(key, "")
            if value and Path(value).is_file():
                return value
        except OSError:
            continue
    return None


def resolve_windows_app(name: str) -> str | None:
    """Resolve a friendly app name to a launchable executable or file path."""
    requested = name.strip().strip('"')
    target = WINDOWS_APPS.get(requested.lower(), requested)

    direct = Path(target).expanduser()
    if direct.is_file():
        return str(direct.resolve())

    on_path = shutil.which(target)
    if on_path:
        return on_path

    executable = Path(target).name
    if not executable.lower().endswith(".exe"):
        executable += ".exe"

    registry_path = _registry_app_path(executable)
    if registry_path:
        return registry_path

    for candidate in WINDOWS_APP_PATHS.get(executable.lower(), []):
        if str(candidate) and candidate.is_file():
            return str(candidate)
    return None


def installed_browsers() -> dict[str, str | None]:
    aliases = {
        "chrome": "chrome",
        "google chrome": "chrome",
        "edge": "edge",
        "microsoft edge": "edge",
        "brave": "brave",
        "firefox": "firefox",
        "mozilla firefox": "firefox",
        "comet": "comet",
    }
    found: dict[str, str | None] = {}
    for display, lookup in aliases.items():
        path = resolve_windows_app(lookup)
        start_app = _find_start_app(display)
        if path or start_app:
            found[display] = path
    return found


def _open(args, brain) -> str:
    if not args:
        return "Tell me which application to open, Boss."
    name = " ".join(args).strip('"')
    system = platform.system()
    try:
        if system == "Windows":
            target = resolve_windows_app(name)
            if target:
                subprocess.Popen(
                    [target],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            elif start_app := _find_start_app(name):
                _launch_start_app(start_app["app_id"])
                name = start_app["name"]
            elif name.lower() in {"browser", "web browser", "default browser"}:
                webbrowser.open("about:blank")
            elif Path(name).expanduser().exists():
                os.startfile(str(Path(name).expanduser().resolve()))
            else:
                return (
                    f"I could not find {name}, Boss. If it is installed, give me its "
                    "full executable path."
                )
        elif system == "Darwin":
            subprocess.Popen(["open", "-a", name])
        else:
            subprocess.Popen([name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return f"Opening {name}, Boss."
    except (OSError, FileNotFoundError) as exc:
        return f"I could not open {name}, Boss: {exc}"


def _apps(args, brain) -> str:
    if platform.system() != "Windows":
        return "Installed-app discovery is currently available on Windows, Boss."
    query = " ".join(args).strip('"').lower()
    names = sorted({app["name"] for app in _windows_start_apps()}, key=str.lower)
    if query:
        names = [name for name in names if query in name.lower()]
    if not names:
        return "I found no matching installed applications, Boss."
    shown = names[:100]
    suffix = f"\n...and {len(names) - 100} more." if len(names) > 100 else ""
    return "Installed applications:\n" + "\n".join(f"- {name}" for name in shown) + suffix


def _game(args, brain) -> str:
    if not args:
        for launcher in ("Xbox", "Steam", "Epic Games Launcher"):
            if _find_start_app(launcher) or resolve_windows_app(launcher):
                return _open([launcher], brain)
        return "Tell me which game or game launcher to open, Boss."
    return _open(args, brain)


def _app_search(args, brain) -> str:
    if len(args) < 2:
        return 'Usage: /app-search "app" "query", Boss.'
    app = args[0].strip('"')
    query = " ".join(args[1:]).strip('"')
    normalized = _normalize(app)

    if normalized in {"chrome", "googlechrome", "edge", "microsoftedge", "brave",
                      "firefox", "mozillafirefox", "comet", "commet"}:
        from skills.web_tools import _browser

        return _browser([app, query], brain)
    if normalized in {"whatsapp", "whatsappdesktop"}:
        from skills.communication import _whatsapp_find

        return _whatsapp_find([query], brain)
    if normalized in {"spotify"}:
        from skills.web_tools import _launch_in_browser

        opened = _launch_in_browser(
            brain.settings.default_browser,
            "https://open.spotify.com/search/" + urllib.parse.quote(query),
        )
        return f"Searching Spotify for “{query}” in {opened}, Boss."
    if normalized in {"steam"}:
        webbrowser.open(
            "https://store.steampowered.com/search/?term="
            + urllib.parse.quote_plus(query)
        )
        return f"Searching Steam for “{query}”, Boss."
    if normalized in {"microsoftstore", "store"}:
        os.startfile(
            "ms-windows-store://search/?query=" + urllib.parse.quote_plus(query)
        )
        return f"Searching Microsoft Store for “{query}”, Boss."

    result = _open([app], brain)
    if not result.startswith("Opening"):
        return result
    time.sleep(3)
    import pyautogui

    pyautogui.hotkey("ctrl", "f")
    pyautogui.write(query, interval=0.04)
    return (
        f"Opened {app} and typed “{query}” into its search/find box, Boss. "
        "If that app uses a different search shortcut, tell me the app name and I can "
        "add its exact workflow."
    )


def _close(args, brain) -> str:
    if not args:
        return "Tell me which application to close, Boss."
    name = " ".join(args).strip('"')
    if not brain.confirm(f"Close {name}? Unsaved work in that app may be lost."):
        return "Close cancelled, Boss."
    process = WINDOWS_APPS.get(name.lower(), name)
    process = os.path.basename(process)
    try:
        if platform.system() == "Windows":
            if not process.lower().endswith(".exe"):
                process += ".exe"
            completed = subprocess.run(
                ["taskkill", "/IM", process, "/T"],
                capture_output=True,
                text=True,
                timeout=15,
            )
        else:
            completed = subprocess.run(
                ["pkill", "-f", process], capture_output=True, text=True, timeout=15
            )
        if completed.returncode == 0:
            return f"Closed {name}, Boss."
        return f"I could not close {name}: {(completed.stderr or completed.stdout).strip()}"
    except OSError as exc:
        return f"I could not close {name}, Boss: {exc}"


def _processes(args, brain) -> str:
    command = ["tasklist"] if platform.system() == "Windows" else ["ps", "-e"]
    output = subprocess.run(command, capture_output=True, text=True, timeout=20)
    lines = output.stdout.splitlines()
    return "\n".join(lines[:40]) + ("\n..." if len(lines) > 40 else "")


def register(registry) -> None:
    registry.register("open", _open, "<app> open a desktop application")
    registry.register("close", _close, "<app> close a desktop application")
    registry.register("apps", _apps, "[search] list installed Windows applications")
    registry.register("app-search", _app_search, "<app> <query> open an app and search")
    registry.register("game", _game, "[name] open a game or game launcher")
    registry.register("processes", _processes, "list running processes")
