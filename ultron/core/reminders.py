from __future__ import annotations

import threading
from datetime import datetime


class ReminderScheduler:
    def __init__(self, memory, voice, interval: float = 5.0):
        self.memory = memory
        self.voice = voice
        self.interval = interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)

    def check_now(self) -> list[str]:
        now = datetime.now()
        latest: dict[str, dict] = {}
        for item in self.memory.all("reminder"):
            latest[item.get("content", "")] = item

        due: list[dict] = []
        for item in latest.values():
            if item.get("status", "open") != "open":
                continue
            try:
                when = datetime.fromisoformat(item["due"])
            except (KeyError, ValueError):
                continue
            if when <= now:
                due.append(item)

        messages = []
        for item in due:
            message = item["content"]
            self.memory.add(
                "reminder",
                message,
                due=item.get("due", now.isoformat()),
                status="notified",
                notified_at=now.isoformat(),
            )
            alert = f"Reminder, Boss: {message}"
            if not item.get("scheduled_task"):
                messages.append(alert)
                print(f"\nULTRON> {alert}")
                if self.voice.enabled:
                    self.voice.stop_speaking()
                    self.voice.speak(alert)
        return messages

    def _run(self) -> None:
        while not self._stop.wait(self.interval):
            try:
                self.check_now()
            except Exception as exc:
                print(f"\nULTRON> Reminder monitor error: {exc}")
