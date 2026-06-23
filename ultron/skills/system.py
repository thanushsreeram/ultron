from __future__ import annotations

import platform
import subprocess
import importlib.util
import os
import ctypes
import json
import re
import sys
from datetime import datetime
from pathlib import Path

WINDOWS_SETTINGS = {
    "home": "ms-settings:",
    "settings": "ms-settings:",
    "display": "ms-settings:display",
    "brightness": "ms-settings:display",
    "sound": "ms-settings:sound",
    "audio": "ms-settings:sound",
    "wifi": "ms-settings:network-wifi",
    "network": "ms-settings:network",
    "bluetooth": "ms-settings:bluetooth",
    "devices": "ms-settings:devices",
    "notifications": "ms-settings:notifications",
    "power": "ms-settings:powersleep",
    "battery": "ms-settings:batterysaver",
    "storage": "ms-settings:storagesense",
    "apps": "ms-settings:appsfeatures",
    "default apps": "ms-settings:defaultapps",
    "privacy": "ms-settings:privacy",
    "updates": "ms-settings:windowsupdate",
    "windows update": "ms-settings:windowsupdate",
    "personalization": "ms-settings:personalization",
    "background": "ms-settings:personalization-background",
    "date": "ms-settings:dateandtime",
    "time": "ms-settings:dateandtime",
    "language": "ms-settings:regionlanguage",
    "microphone": "ms-settings:privacy-microphone",
    "camera": "ms-settings:privacy-webcam",
    "accounts": "ms-settings:accounts",
    "your info": "ms-settings:yourinfo",
    "sign in": "ms-settings:signinoptions",
    "email accounts": "ms-settings:emailandaccounts",
    "family": "ms-settings:family-group",
    "themes": "ms-settings:themes",
    "colors": "ms-settings:colors",
    "lock screen": "ms-settings:lockscreen",
    "taskbar": "ms-settings:taskbar",
    "fonts": "ms-settings:fonts",
    "ethernet": "ms-settings:network-ethernet",
    "vpn": "ms-settings:network-vpn",
    "hotspot": "ms-settings:network-mobilehotspot",
    "proxy": "ms-settings:network-proxy",
    "airplane mode": "ms-settings:network-airplanemode",
    "data usage": "ms-settings:datausage",
    "printers": "ms-settings:printers",
    "mouse": "ms-settings:mousetouchpad",
    "touchpad": "ms-settings:devices-touchpad",
    "typing": "ms-settings:typing",
    "autoplay": "ms-settings:autoplay",
    "usb": "ms-settings:usb",
    "installed apps": "ms-settings:appsfeatures",
    "startup apps": "ms-settings:startupapps",
    "optional features": "ms-settings:optionalfeatures",
    "multitasking": "ms-settings:multitasking",
    "clipboard": "ms-settings:clipboard",
    "remote desktop": "ms-settings:remotedesktop",
    "about": "ms-settings:about",
    "activation": "ms-settings:activation",
    "recovery": "ms-settings:recovery",
    "troubleshoot": "ms-settings:troubleshoot",
    "backup": "ms-settings:backup",
    "security": "windowsdefender:",
    "gaming": "ms-settings:gaming-gamebar",
    "game mode": "ms-settings:gaming-gamemode",
    "accessibility": "ms-settings:easeofaccess",
    "narrator": "ms-settings:easeofaccess-narrator",
    "magnifier": "ms-settings:easeofaccess-magnifier",
    "speech": "ms-settings:speech",
    "location": "ms-settings:privacy-location",
}


def _run(command: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(command, capture_output=True, text=True, timeout=30)


def _is_admin() -> bool:
    if platform.system() != "Windows":
        get_effective_user_id = getattr(os, "geteuid", None)
        return bool(get_effective_user_id and get_effective_user_id() == 0)
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except OSError:
        return False


def _admin(args, brain) -> str:
    if _is_admin():
        return "ULTRON is running with administrator permission, Boss."
    return (
        "ULTRON is running with standard-user permission, Boss. Most personal settings "
        "work, but protected network, service, driver, and system changes may require "
        "administrator permission. Use /elevate when needed."
    )


def _elevate(args, brain) -> str:
    if platform.system() != "Windows":
        return "Administrator relaunch is currently implemented for Windows, Boss."
    if _is_admin():
        return "ULTRON already has administrator permission, Boss."
    if not brain.confirm(
        "Request Windows administrator permission and open a new ULTRON terminal?"
    ):
        return "Administrator request cancelled, Boss."
    main_path = Path(__file__).resolve().parents[1] / "main.py"
    parameters = f'"{main_path}" --voice'
    result = ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        sys.executable,
        parameters,
        str(main_path.parent),
        1,
    )
    if result <= 32:
        return f"Windows did not start the administrator session, Boss. Error code: {result}"
    return (
        "Administrator permission requested, Boss. Approve the Windows UAC prompt. "
        "A new elevated ULTRON terminal will open; close this standard session afterward."
    )


def _updates(args, brain) -> str:
    if platform.system() != "Windows":
        return "Windows Update checking is only available on Windows, Boss."
    script = (
        "$session=New-Object -ComObject Microsoft.Update.Session;"
        "$searcher=$session.CreateUpdateSearcher();"
        "$result=$searcher.Search(\"IsInstalled=0 and IsHidden=0\");"
        "$items=@();"
        "foreach($u in $result.Updates){"
        "$items+=[PSCustomObject]@{Title=$u.Title;Downloaded=$u.IsDownloaded;"
        "Mandatory=$u.IsMandatory;Reboot=$u.RebootRequired}};"
        "$items | ConvertTo-Json -Compress"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            timeout=180,
        )
    except subprocess.TimeoutExpired:
        return (
            "Windows Update scan did not finish within three minutes, Boss. "
            "Opening Windows Update so you can continue the scan."
        )
    if result.returncode != 0:
        os.startfile("ms-settings:windowsupdate")
        return (
            "Windows Update inspection failed, Boss. I opened the Windows Update page. "
            f"Details: {(result.stderr or result.stdout).strip()}"
        )
    raw = result.stdout.strip()
    if not raw:
        return "Windows reports no pending updates, Boss."
    try:
        items = json.loads(raw)
    except json.JSONDecodeError:
        return f"Windows Update returned an unreadable response, Boss: {raw[:500]}"
    if isinstance(items, dict):
        items = [items]
    if not items:
        return "Windows reports no pending updates, Boss."
    lines = [f"Windows found {len(items)} pending update(s), Boss:"]
    for item in items[:20]:
        status = "downloaded" if item.get("Downloaded") else "not downloaded"
        lines.append(f"- {item.get('Title', 'Unnamed update')} ({status})")
    if len(items) > 20:
        lines.append(f"- ...and {len(items) - 20} more")
    lines.append("Nothing was installed. Say “open Windows Update settings” to review them.")
    return "\n".join(lines)


def _health(args, brain) -> str:
    import psutil

    lines = ["Laptop details, Boss:"]
    lines.append(f"- Administrator: {'yes' if _is_admin() else 'no'}")
    lines.append(f"- Windows: {platform.release()} build {platform.version()}")
    boot = datetime.fromtimestamp(psutil.boot_time())
    lines.append(f"- Last boot: {boot:%B %d, %Y at %I:%M %p}")
    memory = psutil.virtual_memory()
    lines.append(
        f"- RAM: {memory.used / 2**30:.1f} GB used of "
        f"{memory.total / 2**30:.1f} GB ({memory.percent:.0f}%)"
    )
    disk = psutil.disk_usage(Path.home().anchor)
    lines.append(
        f"- System storage: {disk.used / 2**30:.1f} GB used, "
        f"{disk.free / 2**30:.1f} GB free"
    )
    battery = psutil.sensors_battery()
    if battery:
        power = "charging/plugged in" if battery.power_plugged else "on battery"
        lines.append(f"- Battery: {battery.percent:.0f}% ({power})")
    lines.append(f"- CPU usage: {psutil.cpu_percent(interval=0.4):.0f}%")

    try:
        from pycaw.pycaw import AudioUtilities

        endpoint = getattr(AudioUtilities.GetSpeakers(), "EndpointVolume", None)
        if endpoint is None:
            raise RuntimeError("Audio endpoint is unavailable")
        lines.append(
            f"- Volume: {round(endpoint.GetMasterVolumeLevelScalar() * 100)}% "
            f"({'muted' if endpoint.GetMute() else 'not muted'})"
        )
    except Exception:
        lines.append("- Volume: unavailable")

    brightness = _run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "(Get-CimInstance -Namespace root/WMI "
            "-ClassName WmiMonitorBrightness | Select-Object -First 1 "
            "-ExpandProperty CurrentBrightness)",
        ]
    )
    if brightness.returncode == 0 and brightness.stdout.strip().isdigit():
        lines.append(f"- Brightness: {brightness.stdout.strip()}%")

    wifi = _run(["netsh", "wlan", "show", "interfaces"])
    if wifi.returncode == 0:
        state = re.search(r"^\s*State\s*:\s*(.+)$", wifi.stdout, re.MULTILINE)
        ssid = re.search(r"^\s*SSID\s*:\s*(.+)$", wifi.stdout, re.MULTILINE)
        if state:
            text = state.group(1).strip()
            if ssid and text.lower() == "connected":
                text += f" to {ssid.group(1).strip()}"
            lines.append(f"- Wi-Fi: {text}")

    gpu = _run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-CimInstance Win32_VideoController | "
            "Select-Object -ExpandProperty Name",
        ]
    )
    names = [line.strip() for line in gpu.stdout.splitlines() if line.strip()]
    if names:
        lines.append("- Graphics: " + ", ".join(names))
    return "\n".join(lines)


def _screenshot(args, brain) -> str:
    import pyautogui

    target = brain.settings.workspace / f"screenshot-{datetime.now():%Y%m%d-%H%M%S}.png"
    pyautogui.screenshot(str(target))
    return f"Screenshot saved to {target}, Boss."


def _volume(args, brain) -> str:
    if not args:
        return "Usage: /volume <0-100|up|down|mute|unmute>, Boss."
    action = args[0].lower().strip("%")
    keys = {"up": "volumeup", "down": "volumedown"}
    import pyautogui

    if action in keys:
        pyautogui.press(keys[action], presses=5 if action in {"up", "down"} else 1)
        return f"Volume {action} command completed, Boss."
    if action in {"mute", "unmute"}:
        try:
            from pycaw.pycaw import AudioUtilities

            device = AudioUtilities.GetSpeakers()
            endpoint = getattr(device, "EndpointVolume", None)
            if endpoint is None:
                raise RuntimeError("Audio endpoint is unavailable")
            endpoint.SetMute(1 if action == "mute" else 0, None)
            return f"Sound {action}d, Boss."
        except Exception as exc:
            return f"I could not {action} the sound, Boss: {exc}"
    if action.isdigit():
        value = max(0, min(100, int(action)))
        try:
            from pycaw.pycaw import AudioUtilities

            device = AudioUtilities.GetSpeakers()
            endpoint = getattr(device, "EndpointVolume", None)
            if endpoint is None:
                raise RuntimeError("Audio endpoint is unavailable")
            endpoint.SetMute(0, None)
            endpoint.SetMasterVolumeLevelScalar(value / 100.0, None)
            actual = round(endpoint.GetMasterVolumeLevelScalar() * 100)
            return f"Volume set to {actual}%, Boss."
        except Exception as exc:
            return (
                f"Exact volume control failed, Boss: {exc}. "
                "Run /settings sound to adjust it manually."
            )
    return "Volume must be 0-100, up, down, mute, or unmute, Boss."


def _brightness(args, brain) -> str:
    if not args or not args[0].isdigit():
        return "Usage: /brightness <0-100>, Boss."
    value = max(0, min(100, int(args[0])))
    if platform.system() != "Windows":
        return "Brightness control is currently implemented for Windows, Boss."
    script = (
        "$m=(Get-CimInstance -Namespace root/WMI "
        "-ClassName WmiMonitorBrightnessMethods);"
        f"$m | Invoke-CimMethod -MethodName WmiSetBrightness "
        f"-Arguments @{{Timeout=1;Brightness={value}}}"
    )
    result = _run(["powershell", "-NoProfile", "-Command", script])
    if result.returncode != 0:
        return f"Brightness control failed, Boss: {result.stderr.strip()}"
    return f"Brightness set to {value}%, Boss."


def _radio_script(kind: str, state: str) -> str:
    desired = "On" if state == "on" else "Off"
    return (
        "Add-Type -AssemblyName System.Runtime.WindowsRuntime;"
        "$asTask=[System.WindowsRuntimeSystemExtensions].GetMethods() | "
        "Where-Object {$_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1} | "
        "Select-Object -First 1;"
        "$op=[Windows.Devices.Radios.Radio,Windows.System.Devices,ContentType=WindowsRuntime]"
        "::GetRadiosAsync();"
        "$task=$asTask.MakeGenericMethod("
        "[System.Collections.Generic.IReadOnlyList[Windows.Devices.Radios.Radio]])"
        ".Invoke($null,@($op));$task.Wait();"
        f"$radio=$task.Result | Where-Object {{$_.Kind -eq '{kind}'}} | Select-Object -First 1;"
        "if(-not $radio){throw 'Radio not found'};"
        f"$set=$radio.SetStateAsync([Windows.Devices.Radios.RadioState]::{desired});"
        "$setTask=$asTask.MakeGenericMethod([Windows.Devices.Radios.RadioAccessStatus])"
        ".Invoke($null,@($set));$setTask.Wait();"
        "Write-Output $setTask.Result"
    )


def _bluetooth(args, brain) -> str:
    action = args[0].lower() if args else "settings"
    if action not in {"on", "off", "settings"}:
        return "Usage: /bluetooth <on|off|settings>, Boss."
    if action == "settings":
        os.startfile("ms-settings:bluetooth")
        return "Opening Bluetooth settings, Boss."
    result = _run(
        ["powershell", "-NoProfile", "-Command", _radio_script("Bluetooth", action)]
    )
    if result.returncode != 0 or "Allowed" not in result.stdout:
        os.startfile("ms-settings:bluetooth")
        return (
            f"Windows blocked direct Bluetooth control, Boss. I opened Bluetooth "
            f"settings so you can turn it {action}. Details: "
            f"{(result.stderr or result.stdout).strip()}"
        )
    return f"Bluetooth turned {action}, Boss."


def _airplane(args, brain) -> str:
    action = args[0].lower() if args else "settings"
    if action not in {"on", "off", "settings"}:
        return "Usage: /airplane <on|off|settings>, Boss."
    os.startfile("ms-settings:network-airplanemode")
    return (
        f"Opening Airplane mode settings, Boss. Windows does not provide a reliable "
        f"standard API for automatically turning it {action}."
    )


def _power_mode(args, brain) -> str:
    mode = " ".join(args).strip('"').lower()
    schemes = {
        "balanced": "381b4222-f694-41f0-9685-ff5bb260df2e",
        "power saver": "a1841308-3541-4fab-bc81-f71556f20b4a",
        "battery saver": "a1841308-3541-4fab-bc81-f71556f20b4a",
        "high performance": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
        "performance": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
    }
    scheme = schemes.get(mode)
    if not scheme:
        return "Use balanced, power saver, or high performance, Boss."
    result = _run(["powercfg", "/setactive", scheme])
    if result.returncode != 0:
        return f"Power mode change failed, Boss: {result.stderr.strip()}"
    return f"Power mode set to {mode}, Boss."


def _display_off(args, brain) -> str:
    if platform.system() != "Windows":
        return "Display power control is currently implemented for Windows, Boss."
    script = (
        "Add-Type -TypeDefinition '[DllImport(\"user32.dll\")]"
        "public static extern int SendMessage(int hWnd,int hMsg,int wParam,int lParam);'"
        " -Name Native -Namespace Win32;"
        "[Win32.Native]::SendMessage(-1,0x0112,0xF170,2) | Out-Null"
    )
    subprocess.Popen(["powershell", "-NoProfile", "-Command", script])
    return "Turning the display off, Boss."


def _wifi(args, brain) -> str:
    if platform.system() != "Windows":
        return "Wi-Fi control is currently implemented for Windows, Boss."
    action = args[0].lower() if args else "status"
    if action == "status":
        result = _run(["netsh", "interface", "show", "interface"])
        return result.stdout.strip()
    if action not in {"on", "off"}:
        return "Usage: /wifi <on|off|status>, Boss."
    if not brain.confirm(f"Turn Wi-Fi {action}?"):
        return "Wi-Fi change cancelled, Boss."
    state = "enabled" if action == "on" else "disabled"
    result = _run(
        ["netsh", "interface", "set", "interface", "name=Wi-Fi", f"admin={state}"]
    )
    if result.returncode != 0:
        return f"Wi-Fi control failed, Boss: {result.stderr.strip()}"
    return f"Wi-Fi turned {action}, Boss."


def _settings(args, brain) -> str:
    if platform.system() != "Windows":
        return "Settings shortcuts are currently implemented for Windows, Boss."
    category = " ".join(args).strip('"').lower() or "home"
    uri = WINDOWS_SETTINGS.get(category)
    if uri is None:
        matches = [
            value for name, value in WINDOWS_SETTINGS.items()
            if category in name or name in category
        ]
        uri = matches[0] if matches else None
    if uri is None:
        os.startfile("ms-settings:")
        return (
            f"I opened Windows Settings, Boss. Windows does not expose a direct URI "
            f"for “{category}”, so use the Settings search box for that page."
        )
    os.startfile(uri)
    return f"Opening {category} settings, Boss."


def _lock(args, brain) -> str:
    if platform.system() == "Windows":
        subprocess.Popen(["rundll32.exe", "user32.dll,LockWorkStation"])
        return "Locking the computer, Boss."
    return "Computer locking is currently implemented for Windows, Boss."


def _sleep(args, brain) -> str:
    if not brain.confirm("Put this computer to sleep now?"):
        return "Sleep cancelled, Boss."
    if platform.system() == "Windows":
        subprocess.Popen(
            ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"]
        )
        return "Putting the computer to sleep, Boss."
    return "Sleep control is currently implemented for Windows, Boss."


def _power(action: str, brain) -> str:
    if not brain.confirm(f"{action.title()} this computer now?"):
        return f"{action.title()} cancelled, Boss."
    system = platform.system()
    if system == "Windows":
        command = ["shutdown", "/s" if action == "shutdown" else "/r", "/t", "5"]
    elif system == "Darwin":
        command = ["sudo", action, "-h", "now"]
    else:
        command = ["systemctl", action]
    subprocess.Popen(command)
    return f"{action.title()} scheduled, Boss."


def _shutdown(args, brain) -> str:
    return _power("shutdown", brain)


def _restart(args, brain) -> str:
    return _power("restart", brain)


def _system_info(args, brain) -> str:
    return (
        f"System: {platform.system()} {platform.release()}\n"
        f"Machine: {platform.machine()}\n"
        f"Python: {platform.python_version()}\n"
        f"Workspace: {brain.settings.workspace}"
    )


def _diagnose(args, brain) -> str:
    packages = {
        "requests": importlib.util.find_spec("requests") is not None,
        "dotenv": importlib.util.find_spec("dotenv") is not None,
        "pyttsx3": importlib.util.find_spec("pyttsx3") is not None,
        "speech_recognition": importlib.util.find_spec("speech_recognition") is not None,
        "sounddevice": importlib.util.find_spec("sounddevice") is not None,
        "numpy": importlib.util.find_spec("numpy") is not None,
        "pyautogui": importlib.util.find_spec("pyautogui") is not None,
        "reportlab": importlib.util.find_spec("reportlab") is not None,
        "pypdf": importlib.util.find_spec("pypdf") is not None,
        "dateparser": importlib.util.find_spec("dateparser") is not None,
        "beautifulsoup4": importlib.util.find_spec("bs4") is not None,
        "scipy": importlib.util.find_spec("scipy") is not None,
        "python-docx": importlib.util.find_spec("docx") is not None,
        "pycaw": importlib.util.find_spec("pycaw") is not None,
        "selenium": importlib.util.find_spec("selenium") is not None,
        "edge-tts": importlib.util.find_spec("edge_tts") is not None,
        "langdetect": importlib.util.find_spec("langdetect") is not None,
    }
    lines = [
        f"NVIDIA API key: {'configured' if brain.settings.nvidia_api_key else 'missing'}",
        f"NVIDIA model: {brain.settings.nvidia_model}",
        f"Memory file: {brain.settings.memory_file}",
        f"Workspace: {brain.settings.workspace}",
        f"Storage: {brain.settings.storage_dir}",
        f"Default browser: {brain.settings.default_browser}",
        f"Conversation language: {brain.language.status()}",
        f"Inbox access: {'configured' if brain.settings.imap_host and brain.settings.imap_user else 'not configured'}",
        f"Direct email: {'configured' if brain.settings.smtp_host and brain.settings.smtp_user and brain.settings.smtp_password else 'not configured'}",
        "Packages:",
    ]
    lines.extend(f"- {name}: {'ready' if ready else 'missing'}" for name, ready in packages.items())
    return "\n".join(lines)


def register(registry) -> None:
    registry.register("screenshot", _screenshot, "save a screenshot")
    registry.register("volume", _volume, "<0-100|up|down|mute|unmute> control sound")
    registry.register("brightness", _brightness, "<0-100> set display brightness")
    registry.register("wifi", _wifi, "<on|off|status> manage Wi-Fi")
    registry.register("bluetooth", _bluetooth, "<on|off|settings> manage Bluetooth")
    registry.register("airplane", _airplane, "<on|off|settings> manage Airplane mode")
    registry.register(
        "power-mode",
        _power_mode,
        "<balanced|power saver|high performance>",
    )
    registry.register("display-off", _display_off, "turn the display off")
    registry.register("settings", _settings, "[category] open a Windows settings page")
    registry.register("lock", _lock, "lock the computer")
    registry.register("sleep", _sleep, "put the computer to sleep")
    registry.register("shutdown", _shutdown, "shut down the computer")
    registry.register("restart", _restart, "restart the computer")
    registry.register("system", _system_info, "show system information")
    registry.register("health", _health, "show detailed laptop health and minor details")
    registry.register("updates", _updates, "scan Windows Update without installing")
    registry.register("admin", _admin, "show administrator permission status")
    registry.register("elevate", _elevate, "restart ULTRON with Windows administrator permission")
    registry.register("diagnose", _diagnose, "check configuration and optional features")
