from __future__ import annotations

import argparse
import sys
from pathlib import Path

from core.brain import UltronBrain
from core.config import load_settings
from core.language import LanguageManager
from core.memory import MemoryStore
from core.reminders import ReminderScheduler
from core.voice import VoiceInterface

ULTRON_BUILD = "2026.06.21-multilingual"


def source_stamp() -> int:
    root = Path(__file__).resolve().parent
    files = [root / "main.py", *(root / "core").glob("*.py"), *(root / "skills").glob("*.py")]
    return max(path.stat().st_mtime_ns for path in files if path.exists())


def collect_multiline() -> str:
    print("ULTRON> Multiline mode enabled.")
    print("ULTRON> Enter as many lines as you need.")
    print("ULTRON> Type /done on a new line to submit, or /cancel to discard.")
    lines: list[str] = []
    while True:
        try:
            line = input("... ")
        except (EOFError, KeyboardInterrupt):
            print("\nULTRON> Multiline input cancelled.")
            return ""
        command = line.strip().lower()
        if command == "/done":
            return "\n".join(lines).strip()
        if command == "/cancel":
            print("ULTRON> Multiline input cancelled.")
            return ""
        lines.append(line)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ULTRON terminal AI assistant")
    parser.add_argument("--voice", action="store_true", help="Start in voice-input mode")
    parser.add_argument("--mute", action="store_true", help="Disable spoken responses")
    parser.add_argument("--once", metavar="COMMAND", help="Run one command and exit")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    settings = load_settings()
    memory = MemoryStore(settings.memory_file)
    language = LanguageManager(
        settings.storage_dir / "language.json",
        default=settings.language_default,
    )
    voice = VoiceInterface(
        enabled=not args.mute,
        rate=settings.voice_rate,
        language=language,
    )
    brain = UltronBrain(
        settings=settings,
        memory=memory,
        voice=voice,
        language=language,
    )
    reminder_scheduler = ReminderScheduler(memory=memory, voice=voice)
    startup_source_stamp = source_stamp()

    print(f"\nULTRON ONLINE - {ULTRON_BUILD}")
    print("Your personal terminal assistant is ready, Boss.")
    print(
        "Type /help for commands, /multi for multiline text, "
        "/voice to toggle the microphone, or /exit to quit.\n"
        "Press Esc while ULTRON is speaking, or say “ULTRON stop” in voice mode. "
        "ULTRON will stop and return to Boss input immediately.\n"
    )

    if args.once:
        response = brain.handle(args.once)
        print(response)
        voice.speak(response)
        return 0

    voice_mode = args.voice
    from skills.productivity import build_daily_brief

    brief = build_daily_brief(memory)
    from skills.clock_tools import local_now

    now = local_now()
    print(f"ULTRON> Local clock: {now:%A, %B %d, %Y - %I:%M:%S %p %Z}")
    print(f"ULTRON> Language: {language.status()}")
    print(f"ULTRON> {brief}\n")
    reminder_scheduler.check_now()
    reminder_scheduler.start()
    if voice_mode:
        print("ULTRON> Speaking... [Press Esc or say “ULTRON stop”]")
        voice.speak(
            "ULTRON is online, Boss. " + brief,
            allow_voice_interrupt=True,
        )
    while True:
        if source_stamp() != startup_source_stamp:
            message = (
                "ULTRON source files changed while this session was running. "
                "Restart ULTRON to load the update, Boss."
            )
            print(f"\nULTRON> {message}")
            voice.speak(message)
            reminder_scheduler.stop()
            return 2
        try:
            if voice_mode:
                user_input = voice.listen()
                if not user_input:
                    if voice.last_error.startswith("Voice input unavailable"):
                        print("ULTRON> Switching to text mode. Type /voice to try again.")
                        voice_mode = False
                    continue
                print(f"Boss> {user_input}")
            else:
                user_input = input("Boss> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nULTRON> Going offline, Boss.")
            reminder_scheduler.stop()
            break

        if not user_input:
            continue
        if voice.is_stop_phrase(user_input) or user_input.lower() in {
            "/stop",
        }:
            voice.stop_speaking()
            if "coding-practice" in brain.registry.commands:
                brain.registry.dispatch("/coding-practice stop", brain)
            print("ULTRON> Current response cancelled, Boss.")
            continue
        if user_input.lower() in {"/multi", "/compose"}:
            user_input = collect_multiline()
            if not user_input:
                continue
        if user_input.lower() in {"/exit", "exit", "quit", "goodbye"}:
            print("ULTRON> Going offline, Boss.")
            voice.speak("Going offline, Boss.")
            reminder_scheduler.stop()
            break
        if user_input.lower() == "/voice":
            voice_mode = not voice_mode
            message = f"Voice input {'enabled' if voice_mode else 'disabled'}, Boss."
            print(f"ULTRON> {message}")
            voice.speak(message)
            continue

        response = brain.handle(user_input)
        print(f"ULTRON> {response}")
        if voice.enabled and response:
            print("ULTRON> Speaking... [Press Esc or say “ULTRON stop”]")
        voice.speak(response, allow_voice_interrupt=voice_mode)

    reminder_scheduler.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
