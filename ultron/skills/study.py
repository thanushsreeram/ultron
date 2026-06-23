from __future__ import annotations

import base64
import hashlib
import os
import subprocess
from datetime import datetime
from pathlib import Path

import dateparser


def _schedule_windows_reminder(when: datetime, message: str) -> tuple[bool, str]:
    if os.name != "nt":
        return False, "Persistent OS reminders are currently available on Windows."
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "reminder_alert.ps1"
    if not script_path.exists():
        return False, "The Windows reminder alert script is missing."
    digest = hashlib.sha1(f"{when.isoformat()}|{message}".encode()).hexdigest()[:12]
    task_name = f"ULTRON_Reminder_{digest}"
    encoded = base64.b64encode(message.encode("utf-8")).decode("ascii")
    arguments = (
        f'-NoProfile -ExecutionPolicy Bypass -File "{script_path}" '
        f'-MessageBase64 "{encoded}"'
    )
    powershell = (
        "$action=New-ScheduledTaskAction -Execute 'powershell.exe' "
        "-Argument $env:ULTRON_TASK_ARGS;"
        "$trigger=New-ScheduledTaskTrigger -Once "
        "-At ([datetime]::Parse($env:ULTRON_TASK_DUE));"
        "Register-ScheduledTask -TaskName $env:ULTRON_TASK_NAME "
        "-Action $action -Trigger $trigger "
        "-Description 'ULTRON personal reminder' -Force | Out-Null"
    )
    environment = os.environ.copy()
    environment.update(
        {
            "ULTRON_TASK_ARGS": arguments,
            "ULTRON_TASK_DUE": when.isoformat(),
            "ULTRON_TASK_NAME": task_name,
        }
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", powershell],
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        return False, (result.stderr or result.stdout).strip()
    return True, task_name


def _remember(args, brain) -> str:
    content = " ".join(args).strip('"')
    if not content:
        return "What should I remember, Boss?"
    brain.memory.add("fact", content)
    return "I’ll remember that, Boss."


def _note(args, brain) -> str:
    content = " ".join(args).strip('"')
    if not content:
        return "What should the note say, Boss?"
    brain.memory.add("note", content)
    return "Note saved, Boss."


def _recall(args, brain) -> str:
    query = " ".join(args).strip('"')
    matches = brain.memory.search(query)
    if not matches:
        return f"I have no saved memory matching “{query}”, Boss."
    return "\n".join(f"- [{item.get('kind')}] {item.get('content')}" for item in matches)


def _forget(args, brain) -> str:
    query = " ".join(args).strip('"')
    if not query:
        return "Tell me what to forget, Boss."
    matches = brain.memory.search(query)
    if not matches:
        return "I found nothing matching that memory, Boss."
    if not brain.confirm(f"Forget {len(matches)} matching memory entries?"):
        return "Forget cancelled, Boss."
    count = brain.memory.delete_matching(query)
    return f"Forgot {count} matching entries, Boss."


def _task(args, brain) -> str:
    if len(args) < 2 or args[0].lower() not in {"add", "done"}:
        return 'Usage: /task add "description" or /task done "description", Boss.'
    action = args[0].lower()
    content = " ".join(args[1:]).strip('"')
    brain.memory.add("task", content, status="open" if action == "add" else "done")
    return f"Task {'added' if action == 'add' else 'completed'}, Boss."


def _tasks(args, brain) -> str:
    states: dict[str, str] = {}
    for item in brain.memory.all("task"):
        states[item["content"]] = item.get("status", "open")
    open_tasks = [text for text, status in states.items() if status == "open"]
    if not open_tasks:
        return "You have no open tasks, Boss."
    return "Open tasks:\n" + "\n".join(f"- {text}" for text in open_tasks)


def _remind(args, brain) -> str:
    if len(args) < 2:
        return 'Usage: /remind "YYYY-MM-DD HH:MM" "message", Boss.'
    when_text = args[0].strip('"')
    message = " ".join(args[1:]).strip('"')
    when = dateparser.parse(
        when_text,
        settings={
            "PREFER_DATES_FROM": "future",
            "RELATIVE_BASE": datetime.now(),
            "RETURN_AS_TIMEZONE_AWARE": False,
        },
    )
    if when is None:
        return (
            "I could not understand that time, Boss. Try “today at 6 PM”, "
            "“tomorrow morning”, or “2026-06-21 18:00”."
        )
    scheduled, detail = _schedule_windows_reminder(when, message)
    brain.memory.add(
        "reminder",
        message,
        due=when.isoformat(),
        status="open",
        scheduled_task=detail if scheduled else "",
    )
    result = f"Reminder saved for {when:%B %d, %Y at %I:%M %p}, Boss."
    if scheduled:
        return result + " Windows will alert you even if ULTRON is closed."
    return (
        result
        + " I will alert you while ULTRON is running. Windows background scheduling "
        + f"was unavailable: {detail}"
    )


def get_due_reminders(memory) -> list[str]:
    now = datetime.now()
    due: list[str] = []
    states: dict[str, dict] = {}
    for item in memory.all("reminder"):
        states[item["content"]] = item
    for item in states.values():
        if item.get("status", "open") != "open":
            continue
        try:
            if datetime.fromisoformat(item["due"]) <= now:
                due.append(item["content"])
        except (KeyError, ValueError):
            continue
    return due


def _reminders(args, brain) -> str:
    states: dict[str, dict] = {}
    for item in brain.memory.all("reminder"):
        states[item["content"]] = item
    items = [
        item
        for item in states.values()
        if item.get("status", "open") in {"open", "notified"}
    ]
    if not items:
        return "You have no active reminders, Boss."
    return "\n".join(f"- {item['due']}: {item['content']}" for item in items)


def _reminder_done(args, brain) -> str:
    query = " ".join(args).strip('"')
    if not query:
        return 'Usage: /reminder-done "message", Boss.'
    matches = [
        item for item in brain.memory.all("reminder")
        if query.lower() in item.get("content", "").lower()
        and item.get("status", "open") in {"open", "notified"}
    ]
    if not matches:
        return f'I found no open reminder matching "{query}", Boss.'
    latest = matches[-1]
    brain.memory.add(
        "reminder",
        latest["content"],
        due=latest.get("due", datetime.now().isoformat()),
        status="done",
    )
    return f"Reminder completed: {latest['content']}"


def _study(args, brain) -> str:
    topic = " ".join(args).strip('"')
    if not topic:
        return "Tell me the subject, goal, deadline, and daily study time, Boss."
    return brain.chat(
        f"Create a practical study plan for: {topic}",
        extra_system=(
            "Act as an expert tutor. Produce a realistic schedule with milestones, "
            "active recall, spaced repetition, practice, and progress checks."
        ),
    )


def _teach(args, brain) -> str:
    topic = " ".join(args).strip('"')
    if not topic:
        return "What would you like to learn, Boss?"
    return brain.chat(
        f"Teach me this topic from the beginning: {topic}",
        extra_system=(
            "Act as a patient expert teacher. Assume the learner is new. Explain in "
            "small steps, define unfamiliar terms, use analogies and examples, include "
            "a short practice exercise, and end with a concise recap."
        ),
    )


def _explain(args, brain) -> str:
    topic = " ".join(args).strip('"')
    if not topic:
        return "What should I explain, Boss?"
    return brain.chat(
        f"Explain this clearly and in useful detail: {topic}",
        extra_system=(
            "Give a structured, accurate explanation. Start with the simple idea, then "
            "add detail, examples, common mistakes, and practical applications."
        ),
    )


def register(registry) -> None:
    registry.register("remember", _remember, "<fact> save important information")
    registry.register("note", _note, "<text> save a note")
    registry.register("recall", _recall, "<query> search memory")
    registry.register("forget", _forget, "<query> remove matching memories")
    registry.register("task", _task, "<add|done> <description> update a task")
    registry.register("tasks", _tasks, "list open tasks")
    registry.register("remind", _remind, "<date/time> <message> create a reminder")
    registry.register("reminders", _reminders, "list reminders")
    registry.register("reminder-done", _reminder_done, "<message> complete a reminder")
    registry.register("study", _study, "<goal> create a study plan")
    registry.register("teach", _teach, "<topic> teach a topic from the beginning")
    registry.register("explain", _explain, "<topic> give a detailed explanation")
