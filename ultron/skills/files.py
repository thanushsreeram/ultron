from __future__ import annotations

import shutil
from pathlib import Path

EXTENSION_GROUPS = {
    "Images": {".bmp", ".gif", ".jpeg", ".jpg", ".png", ".svg", ".webp"},
    "Documents": {".csv", ".doc", ".docx", ".md", ".pdf", ".ppt", ".pptx", ".txt", ".xls", ".xlsx"},
    "Audio": {".aac", ".flac", ".m4a", ".mp3", ".ogg", ".wav"},
    "Video": {".avi", ".mkv", ".mov", ".mp4", ".webm"},
    "Archives": {".7z", ".gz", ".rar", ".tar", ".zip"},
    "Code": {".c", ".cpp", ".css", ".go", ".html", ".java", ".js", ".json", ".py", ".rs", ".ts", ".yaml", ".yml"},
}


def _resolve(raw: str, brain, must_exist: bool = False) -> Path:
    raw = raw.strip('"') or "."
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = brain.settings.workspace / candidate
    candidate = candidate.resolve()
    workspace = brain.settings.workspace.resolve()
    if not brain.settings.allow_outside_workspace:
        try:
            candidate.relative_to(workspace)
        except ValueError as exc:
            raise PermissionError(
                f"Access is limited to {workspace}. Set "
                "ULTRON_ALLOW_OUTSIDE_WORKSPACE=true to change this."
            ) from exc
    if must_exist and not candidate.exists():
        raise FileNotFoundError(candidate)
    return candidate


def _files(args, brain) -> str:
    path = _resolve(" ".join(args) if args else ".", brain, must_exist=True)
    if not path.is_dir():
        return f"{path} is not a folder, Boss."
    entries = sorted(path.iterdir(), key=lambda item: (item.is_file(), item.name.lower()))
    if not entries:
        return f"{path} is empty, Boss."
    return "\n".join(("[DIR] " if item.is_dir() else "[FILE] ") + item.name for item in entries[:100])


def _read(args, brain) -> str:
    path = _resolve(" ".join(args), brain, must_exist=True)
    if not path.is_file():
        return f"{path} is not a file, Boss."
    if path.stat().st_size > 1_000_000:
        return "That file is over 1 MB. Please narrow the request, Boss."
    return path.read_text(encoding="utf-8", errors="replace")


def _write(args, brain) -> str:
    if len(args) < 2:
        return 'Usage: /write "file.txt" "content", Boss.'
    path = _resolve(args[0], brain)
    content = " ".join(args[1:]).strip('"')
    if path.exists() and not brain.confirm(f"Overwrite {path}?"):
        return "Write cancelled, Boss."
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"Wrote {path}, Boss."


def _append(args, brain) -> str:
    if len(args) < 2:
        return 'Usage: /append "file.txt" "content", Boss.'
    path = _resolve(args[0], brain)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(" ".join(args[1:]).strip('"') + "\n")
    return f"Updated {path}, Boss."


def _mkdir(args, brain) -> str:
    path = _resolve(" ".join(args), brain)
    path.mkdir(parents=True, exist_ok=True)
    return f"Folder ready: {path}"


def _move(args, brain) -> str:
    if len(args) != 2:
        return 'Usage: /move "source" "destination", Boss.'
    source = _resolve(args[0], brain, must_exist=True)
    destination = _resolve(args[1], brain)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(destination))
    return f"Moved {source} to {destination}, Boss."


def _copy(args, brain) -> str:
    if len(args) != 2:
        return 'Usage: /copy "source" "destination", Boss.'
    source = _resolve(args[0], brain, must_exist=True)
    destination = _resolve(args[1], brain)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not brain.confirm(f"Overwrite {destination}?"):
        return "Copy cancelled, Boss."
    if source.is_dir():
        shutil.copytree(source, destination, dirs_exist_ok=True)
    else:
        shutil.copy2(source, destination)
    return f"Copied {source} to {destination}, Boss."


def _tree(args, brain) -> str:
    path = _resolve(" ".join(args) if args else ".", brain, must_exist=True)
    if not path.is_dir():
        return f"{path} is not a folder, Boss."
    lines = [path.name + "/"]
    for item in sorted(path.rglob("*"), key=lambda entry: str(entry).lower())[:200]:
        depth = len(item.relative_to(path).parts)
        lines.append("  " * depth + ("[D] " if item.is_dir() else "[F] ") + item.name)
    return "\n".join(lines)


def _organize(args, brain) -> str:
    path = _resolve(" ".join(args) if args else ".", brain, must_exist=True)
    if not path.is_dir():
        return f"{path} is not a folder, Boss."
    files = [item for item in path.iterdir() if item.is_file()]
    if not files:
        return f"There are no loose files to organize in {path}, Boss."
    if not brain.confirm(f"Organize {len(files)} files in {path} by file type?"):
        return "Organization cancelled, Boss."
    moved = 0
    for source in files:
        category = "Other"
        for name, extensions in EXTENSION_GROUPS.items():
            if source.suffix.lower() in extensions:
                category = name
                break
        destination_dir = path / category
        destination_dir.mkdir(exist_ok=True)
        destination = destination_dir / source.name
        if destination.exists():
            destination = destination_dir / f"{source.stem}-{source.stat().st_mtime_ns}{source.suffix}"
        shutil.move(str(source), str(destination))
        moved += 1
    return f"Organized {moved} files in {path}, Boss."


def _delete(args, brain) -> str:
    path = _resolve(" ".join(args), brain, must_exist=True)
    if not brain.confirm(f"Permanently delete {path}?"):
        return "Delete cancelled, Boss."
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    return f"Deleted {path}, Boss."


def register(registry) -> None:
    registry.register("files", _files, "[folder] list files and folders")
    registry.register("read", _read, "<file> read a text file")
    registry.register("write", _write, "<file> <text> create or overwrite a file")
    registry.register("append", _append, "<file> <text> append to a file")
    registry.register("mkdir", _mkdir, "<folder> create a folder")
    registry.register("move", _move, "<source> <destination> move or rename")
    registry.register("copy", _copy, "<source> <destination> copy a file or folder")
    registry.register("tree", _tree, "[folder] show a folder tree")
    registry.register("organize", _organize, "[folder] organize files by type")
    registry.register("delete", _delete, "<path> permanently delete a file or folder")
