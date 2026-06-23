from __future__ import annotations


def _voice_type(args, brain) -> str:
    if not args:
        return (
            f"ULTRON is using the {brain.language.voice_gender} "
            f"{brain.language.current.name} voice, Boss."
        )
    requested = " ".join(args).strip('"')
    try:
        selected = brain.language.set_voice_gender(requested)
    except ValueError:
        return "Use /voice-type male or /voice-type female, Boss."
    return (
        f"ULTRON voice changed to {selected}, Boss. "
        "This preference is saved for future sessions."
    )


def register(registry) -> None:
    registry.register(
        "voice-type",
        _voice_type,
        "[male|female] show or change the speaking voice",
    )
