from __future__ import annotations

from pathlib import Path


TYPE_EXTENSIONS = {
    "note": ".md",
    "document": ".md",
    "article": ".md",
    "plan": ".md",
    "story": ".md",
    "python": ".py",
    "code": ".txt",
    "text": ".txt",
}


def _artifact_path(kind: str, name: str, brain) -> Path:
    extension = TYPE_EXTENSIONS.get(kind.lower(), ".md")
    clean = name.strip('"')
    if not Path(clean).suffix:
        clean += extension
    path = (brain.settings.workspace / "created" / clean).resolve()
    path.relative_to(brain.settings.workspace.resolve())
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _create(args, brain) -> str:
    if len(args) < 3:
        return 'Usage: /create <type> "name" "instructions", Boss.'
    kind = args[0].strip('"').lower()
    name = args[1].strip('"')
    request = " ".join(args[2:]).strip('"')
    path = _artifact_path(kind, name, brain)
    result = brain.chat(
        f"Create a {kind} named {name}. Requirements: {request}",
        extra_system=(
            "Create the requested artifact completely. Return only its final content. "
            "For code, return runnable code without Markdown fences. For documents, use "
            "clear headings and polished prose."
        ),
    )
    if path.exists() and not brain.confirm(f"Overwrite {path.name}?"):
        return "Creation cancelled, Boss."
    path.write_text(result, encoding="utf-8")
    brain.memory.add(
        "artifact",
        request,
        name=name,
        artifact_type=kind,
        file=str(path),
    )
    return f"Created {kind} “{name}” at {path}, Boss."


def _change(args, brain) -> str:
    if len(args) < 2:
        return 'Usage: /change "file" "instructions", Boss.'
    supplied = Path(args[0].strip('"'))
    candidates = [
        (brain.settings.workspace / supplied).resolve(),
        (brain.settings.workspace / "created" / supplied).resolve(),
    ]
    path = next((item for item in candidates if item.is_file()), None)
    if path is None:
        return f"I cannot find {supplied}, Boss."
    path.relative_to(brain.settings.workspace.resolve())
    instruction = " ".join(args[1:]).strip('"')
    original = path.read_text(encoding="utf-8", errors="replace")
    result = brain.chat(
        f"Modify the content according to this instruction: {instruction}\n\n"
        f"CURRENT CONTENT:\n{original[:20000]}",
        extra_system=(
            "Return only the complete revised content. Preserve useful existing content "
            "unless the instruction asks to remove it."
        ),
    )
    if not brain.confirm(f"Replace {path.name} with the revised version?"):
        preview = path.with_name(path.stem + "-preview" + path.suffix)
        preview.write_text(result, encoding="utf-8")
        return f"Original preserved. Revised preview saved to {preview}, Boss."
    backup = path.with_name(path.name + ".bak")
    backup.write_text(original, encoding="utf-8")
    path.write_text(result, encoding="utf-8")
    return f"Updated {path} and saved a backup at {backup}, Boss."


def register(registry) -> None:
    registry.register("create", _create, "<type> <name> <instructions> create new work")
    registry.register("change", _change, "<file> <instructions> revise saved work")
