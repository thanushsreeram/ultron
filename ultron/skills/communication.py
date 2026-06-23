from __future__ import annotations

import os
import re
import time
import urllib.parse
import webbrowser

from skills.apps import _open


def _copy(text: str) -> None:
    try:
        import pyperclip

        pyperclip.copy(text)
    except ImportError:
        import tkinter

        root = tkinter.Tk()
        root.withdraw()
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()
        root.destroy()


def _message(args, brain) -> str:
    if len(args) < 2:
        return 'Usage: /message "contact or phone" "message", Boss.'
    recipient = args[0].strip('"')
    text = " ".join(args[1:]).strip('"')
    _copy(text)

    digits = re.sub(r"\D", "", recipient)
    if len(digits) >= 8:
        url = f"https://wa.me/{digits}?text={urllib.parse.quote(text)}"
        webbrowser.open(url)
        return (
            f"I opened a WhatsApp draft for {recipient} and copied the message, Boss. "
            "Review it and press Send."
        )

    if os.name == "nt":
        try:
            os.startfile("ms-phone:")
            return (
                f"I copied the message and opened Phone Link for {recipient}, Boss. "
                "Choose the contact, paste, review, and send it."
            )
        except OSError:
            pass
    return f"Message copied for {recipient}, Boss. Open your messaging app and paste it."


def _whatsapp(args, brain) -> str:
    if len(args) < 2:
        return 'Usage: /whatsapp "phone number" "message", Boss.'
    recipient = re.sub(r"\D", "", args[0])
    text = " ".join(args[1:]).strip('"')
    if len(recipient) < 8:
        return "Use a phone number with country code, Boss."
    webbrowser.open(
        f"https://wa.me/{recipient}?text={urllib.parse.quote(text)}"
    )
    return f"WhatsApp draft opened for {recipient}, Boss. Review and press Send."


def _whatsapp_find(args, brain) -> str:
    if not args:
        return 'Usage: /whatsapp-find "contact", Boss.'
    contact = " ".join(args).strip('"')
    result = _open(["WhatsApp"], brain)
    if not result.startswith("Opening"):
        webbrowser.open("https://web.whatsapp.com")
    time.sleep(3)
    import pyautogui

    pyautogui.hotkey("ctrl", "f")
    pyautogui.write(contact, interval=0.04)
    return f"WhatsApp is open with “{contact}” in the search box, Boss."


def _whatsapp_draft(args, brain) -> str:
    if len(args) < 2:
        return 'Usage: /whatsapp-draft "contact" "message", Boss.'
    contact = args[0].strip('"')
    text = " ".join(args[1:]).strip('"')
    result = _open(["WhatsApp"], brain)
    if not result.startswith("Opening"):
        webbrowser.open("https://web.whatsapp.com")
    time.sleep(3)
    import pyautogui

    pyautogui.hotkey("ctrl", "f")
    pyautogui.write(contact, interval=0.04)
    time.sleep(1)
    pyautogui.press("enter")
    time.sleep(1)
    pyautogui.write(text, interval=0.02)
    return (
        f"I opened the chat with {contact} and typed the message, Boss. "
        "Review it and press Send."
    )


def _draft(args, brain) -> str:
    request = " ".join(args).strip('"')
    if not request:
        return "Tell me what message or email you want drafted, Boss."
    result = brain.chat(
        f"Draft this communication: {request}",
        extra_system=(
            "Write a polished message or email. Match the requested tone. Return only "
            "the ready-to-send draft unless the user explicitly asks for alternatives."
        ),
    )
    _copy(result)
    return result + "\n\nI copied the draft to your clipboard, Boss."


def register(registry) -> None:
    registry.register("message", _message, "<contact> <text> prepare a message")
    registry.register("text", _message, "<contact> <text> prepare a text message")
    registry.register("whatsapp", _whatsapp, "<phone> <text> open a WhatsApp draft")
    registry.register("whatsapp-find", _whatsapp_find, "<contact> search WhatsApp")
    registry.register(
        "whatsapp-draft",
        _whatsapp_draft,
        "<contact> <text> type a WhatsApp draft without sending",
    )
    registry.register("draft", _draft, "<request> draft and copy a message or email")
