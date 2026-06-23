from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class MemoryStore:
    """Append-only JSON-lines memory stored in data/memory.txt."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)
        self._lock = threading.Lock()

    def add(self, kind: str, content: str, **metadata: Any) -> dict[str, Any]:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "kind": kind,
            "content": content.strip(),
            **metadata,
        }
        with self._lock, self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record

    def all(self, kind: str | None = None) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        with self._lock, self.path.open("r", encoding="utf-8") as stream:
            for line in stream:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    record = {"kind": "legacy", "content": line.strip()}
                if kind is None or record.get("kind") == kind:
                    records.append(record)
        return records

    def recent_conversation(self, limit: int = 12) -> list[dict[str, str]]:
        messages = [
            item for item in self.all() if item.get("kind") in {"user", "assistant"}
        ][-limit:]
        return [
            {
                "role": "user" if item["kind"] == "user" else "assistant",
                "content": item["content"],
            }
            for item in messages
        ]

    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        words = {word.lower() for word in query.split() if len(word) > 2}
        scored = []
        for item in self.all():
            text = item.get("content", "").lower()
            score = sum(word in text for word in words)
            if score or query.lower() in text:
                scored.append((score, item))
        return [item for _, item in sorted(scored, key=lambda row: row[0], reverse=True)[:limit]]

    def delete_matching(self, query: str) -> int:
        query = query.lower()
        records = self.all()
        kept = [item for item in records if query not in item.get("content", "").lower()]
        removed = len(records) - len(kept)
        with self._lock, self.path.open("w", encoding="utf-8") as stream:
            for item in kept:
                stream.write(json.dumps(item, ensure_ascii=False) + "\n")
        return removed
