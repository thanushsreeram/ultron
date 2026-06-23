from __future__ import annotations

from datetime import datetime


def local_now() -> datetime:
    return datetime.now().astimezone()


def greeting_for(hour: int) -> str:
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 22:
        return "evening"
    return "night"


def _clock(args, brain) -> str:
    now = local_now()
    zone = now.tzname() or "local time"
    return f"It is {now:%I:%M:%S %p} ({zone}) on {now:%A, %B %d, %Y}, Boss."


def _date(args, brain) -> str:
    now = local_now()
    return f"Today is {now:%A, %B %d, %Y}, Boss."


def _greet(args, brain) -> str:
    said = " ".join(args).strip('"').lower()
    now = local_now()
    correct = greeting_for(now.hour)
    if said == correct:
        return f"Good {correct}, Boss. It is {now:%I:%M %p}."
    return (
        f"Good {correct}, Boss. It is {now:%I:%M %p}, so “good {said}” "
        f"is not the correct greeting for the current time."
    )


def register(registry) -> None:
    registry.register("clock", _clock, "show the exact local time and date")
    registry.register("date", _date, "show today's local date")
    registry.register("greet", _greet, "<morning|afternoon|evening|night>")
