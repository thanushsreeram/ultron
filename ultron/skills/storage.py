from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path


def _key(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip().strip('"')).strip("-")


def _record_path(name: str, brain) -> Path:
    safe = _key(name)
    if not safe:
        raise ValueError("A storage name is required")
    return brain.settings.storage_dir / "records" / f"{safe}.json"


def _store(args, brain) -> str:
    if len(args) < 2:
        return 'Usage: /store "name" "information", Boss.'
    path = _record_path(args[0], brain)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = " ".join(args[1:]).strip('"')
    data = {
        "name": args[0].strip('"'),
        "content": content,
        "updated": datetime.now().isoformat(timespec="seconds"),
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    brain.memory.add("stored_item", content, name=data["name"], file=str(path))
    return f"Stored “{data['name']}” in ULTRON storage, Boss."


def _storage(args, brain) -> str:
    records = brain.settings.storage_dir / "records"
    if not records.exists():
        return "ULTRON storage is empty, Boss."
    items = sorted(records.glob("*.json"))
    if not items:
        return "ULTRON storage is empty, Boss."
    return "Stored items:\n" + "\n".join(f"- {item.stem}" for item in items)


def _retrieve(args, brain) -> str:
    if not args:
        return 'Usage: /retrieve "name", Boss.'
    path = _record_path(" ".join(args), brain)
    if not path.exists():
        query = _key(" ".join(args)).lower()
        candidates = list((brain.settings.storage_dir / "records").glob("*.json"))
        matches = [item for item in candidates if query in item.stem.lower()]
        if len(matches) != 1:
            return f"I found no unique stored item matching “{query}”, Boss."
        path = matches[0]
    data = json.loads(path.read_text(encoding="utf-8"))
    return f"{data['name']}:\n{data['content']}"


def _update(args, brain) -> str:
    if len(args) < 2:
        return 'Usage: /update-store "name" "new information", Boss.'
    path = _record_path(args[0], brain)
    if not path.exists():
        return f"I cannot find stored item “{args[0].strip(chr(34))}”, Boss."
    content = " ".join(args[1:]).strip('"')
    data = json.loads(path.read_text(encoding="utf-8"))
    data["content"] = content
    data["updated"] = datetime.now().isoformat(timespec="seconds")
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    brain.memory.add("stored_item", content, name=data["name"], file=str(path))
    return f"Updated “{data['name']}”, Boss."


def register(registry) -> None:
    registry.register("store", _store, "<name> <information> save persistent information")
    registry.register("storage", _storage, "list stored information and projects")
    registry.register("retrieve", _retrieve, "<name> read a stored item")
    registry.register("update-store", _update, "<name> <information> replace a stored item")
