from __future__ import annotations

import ctypes
import os
import time
from ctypes import wintypes


INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
VK_RETURN = 0x0D
VK_TAB = 0x09


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", wintypes.WPARAM),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("union",)
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", INPUT_UNION),
    ]


def _send_key(vk: int) -> None:
    inputs = (INPUT * 2)(
        INPUT(
            type=INPUT_KEYBOARD,
            ki=KEYBDINPUT(vk, 0, 0, 0, 0),
        ),
        INPUT(
            type=INPUT_KEYBOARD,
            ki=KEYBDINPUT(vk, 0, KEYEVENTF_KEYUP, 0, 0),
        ),
    )
    sent = ctypes.windll.user32.SendInput(2, ctypes.byref(inputs), ctypes.sizeof(INPUT))
    if sent != 2:
        raise OSError("Windows could not inject the requested key")


def _send_unicode_unit(unit: int) -> None:
    inputs = (INPUT * 2)(
        INPUT(
            type=INPUT_KEYBOARD,
            ki=KEYBDINPUT(0, unit, KEYEVENTF_UNICODE, 0, 0),
        ),
        INPUT(
            type=INPUT_KEYBOARD,
            ki=KEYBDINPUT(
                0,
                unit,
                KEYEVENTF_UNICODE | KEYEVENTF_KEYUP,
                0,
                0,
            ),
        ),
    )
    sent = ctypes.windll.user32.SendInput(2, ctypes.byref(inputs), ctypes.sizeof(INPUT))
    if sent != 2:
        raise OSError("Windows could not inject Unicode text")


def type_text(text: str, interval: float = 0.002) -> None:
    """Type text through Windows keyboard events instead of clipboard paste."""
    if os.name != "nt":
        raise OSError("Force paste is currently implemented for Windows")
    for character in text:
        if character == "\n":
            _send_key(VK_RETURN)
        elif character == "\t":
            _send_key(VK_TAB)
        else:
            encoded = character.encode("utf-16-le")
            for index in range(0, len(encoded), 2):
                unit = int.from_bytes(encoded[index:index + 2], "little")
                _send_unicode_unit(unit)
        if interval:
            time.sleep(interval)


def _clipboard_text() -> str:
    import pyperclip

    value = pyperclip.paste()
    return value if isinstance(value, str) else str(value)


def _force_paste(args, brain) -> str:
    text = " ".join(args).strip('"') if args else _clipboard_text()
    if not text:
        return "The clipboard is empty, Boss."
    print("ULTRON> Focus the destination field. Force paste starts in 3 seconds...")
    for remaining in (3, 2, 1):
        print(f"ULTRON> {remaining}")
        time.sleep(1)
    try:
        type_text(text)
    except OSError as exc:
        return f"Force paste failed, Boss: {exc}"
    return (
        f"Force-pasted {len(text)} characters into the focused field, Boss. "
        "The clipboard text was not displayed."
    )


def register(registry) -> None:
    registry.register(
        "force-paste",
        _force_paste,
        "[text] type clipboard or supplied text into the focused field",
    )
