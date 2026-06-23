from __future__ import annotations

from collections import Counter
from datetime import datetime


def _latest_states(memory, kind: str) -> dict[str, dict]:
    states: dict[str, dict] = {}
    for item in memory.all(kind):
        states[item.get("content", "")] = item
    return states


def build_daily_brief(memory) -> str:
    now = datetime.now()
    today = now.date()

    reminders = []
    for item in _latest_states(memory, "reminder").values():
        if item.get("status", "open") != "open":
            continue
        try:
            due = datetime.fromisoformat(item["due"])
        except (KeyError, ValueError):
            continue
        if due.date() <= today:
            label = "overdue" if due.date() < today else due.strftime("%I:%M %p")
            reminders.append(f"{item['content']} ({label})")

    events = []
    for item in memory.all("calendar_event"):
        try:
            start = datetime.fromisoformat(item["start"])
        except (KeyError, ValueError):
            continue
        if start.date() == today:
            events.append(f"{start:%I:%M %p} - {item['content']}")

    tasks = [
        content
        for content, item in _latest_states(memory, "task").items()
        if item.get("status", "open") == "open"
    ]

    lines = [f"Daily briefing for {now:%A, %B %d, %Y}, Boss."]
    lines.append("Today's reminders: " + ("; ".join(reminders) if reminders else "none"))
    lines.append("Today's events: " + ("; ".join(events) if events else "none"))
    lines.append(
        "Open tasks: "
        + ("; ".join(tasks[:8]) if tasks else "none")
        + (f" and {len(tasks) - 8} more" if len(tasks) > 8 else "")
    )
    return "\n".join(lines)


def _daily(args, brain) -> str:
    return build_daily_brief(brain.memory)


def _history(args, brain) -> str:
    limit = 20
    if args and args[0].strip('"').isdigit():
        limit = max(1, min(100, int(args[0].strip('"'))))
    actions = brain.memory.all("action")[-limit:]
    if not actions:
        return "No action history is stored yet, Boss."
    return "Recent ULTRON actions:\n" + "\n".join(
        f"- {item.get('timestamp', '')[:19]}: {item['content']}"
        for item in reversed(actions)
    )


def _frequent(args, brain) -> str:
    actions = brain.memory.all("action")
    if not actions:
        return "I need more usage history before I can identify frequent features, Boss."
    counts = Counter(item.get("command", "unknown") for item in actions)
    return "Your most-used ULTRON features:\n" + "\n".join(
        f"- {command}: {count} times" for command, count in counts.most_common(10)
    )


def register(registry) -> None:
    registry.register("daily", _daily, "show today's reminders, events, and tasks")
    registry.register("history", _history, "[count] show recent assistant actions")
    registry.register("frequent", _frequent, "show your most-used ULTRON features")
