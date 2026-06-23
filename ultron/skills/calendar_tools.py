from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import dateparser


def _ics_escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def _event(args, brain) -> str:
    if len(args) < 2:
        return (
            'Usage: /event "YYYY-MM-DD HH:MM" "title" [duration minutes] '
            '["description"], Boss.'
        )
    when_text = args[0].strip('"')
    start = dateparser.parse(
        when_text,
        settings={
            "PREFER_DATES_FROM": "future",
            "RELATIVE_BASE": datetime.now(),
            "RETURN_AS_TIMEZONE_AWARE": False,
        },
    )
    if start is None:
        return (
            "I could not understand that date, Boss. Try “tomorrow at 4 PM” "
            "or “2026-06-21 16:00”."
        )

    title = args[1].strip('"')
    duration = 60
    description_start = 2
    if len(args) > 2 and args[2].strip('"').isdigit():
        duration = max(5, int(args[2].strip('"')))
        description_start = 3
    description = " ".join(args[description_start:]).strip('"')
    end = start + timedelta(minutes=duration)
    uid = f"{start:%Y%m%d%H%M%S}-{abs(hash(title))}@ultron.local"
    now_utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    content = "\r\n".join(
        [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//ULTRON AI Assistant//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now_utc}",
            f"DTSTART:{start:%Y%m%dT%H%M%S}",
            f"DTEND:{end:%Y%m%dT%H%M%S}",
            f"SUMMARY:{_ics_escape(title)}",
            f"DESCRIPTION:{_ics_escape(description)}",
            "END:VEVENT",
            "END:VCALENDAR",
            "",
        ]
    )
    events_dir = brain.settings.storage_dir / "calendar"
    events_dir.mkdir(parents=True, exist_ok=True)
    safe_title = "".join(ch if ch.isalnum() else "-" for ch in title).strip("-")[:50]
    path = events_dir / f"{start:%Y%m%d-%H%M}-{safe_title or 'event'}.ics"
    path.write_text(content, encoding="utf-8")
    brain.memory.add(
        "calendar_event",
        title,
        start=start.isoformat(),
        end=end.isoformat(),
        description=description,
        file=str(path),
    )
    if os.name == "nt":
        os.startfile(path)
    return (
        f"Calendar event created for {start:%B %d, %Y at %I:%M %p}, Boss. "
        "Your calendar app is opening so you can confirm it."
    )


def _events(args, brain) -> str:
    events = brain.memory.all("calendar_event")
    if not events:
        return "You have no ULTRON calendar events saved, Boss."
    return "\n".join(
        f"- {item.get('start', 'unknown time')}: {item['content']}"
        for item in events[-30:]
    )


def register(registry) -> None:
    registry.register("event", _event, "<date/time> <title> [minutes] [description]")
    registry.register("events", _events, "list events created through ULTRON")
