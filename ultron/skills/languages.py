from __future__ import annotations

from core.language import LANGUAGES, resolve_language


def _language(args, brain) -> str:
    if not args:
        return f"Conversation language: {brain.language.status()}, Boss."
    requested = " ".join(args).strip('"')
    try:
        language = brain.language.set_mode(requested)
    except ValueError:
        return (
            f"I do not have a configured voice for “{requested}”, Boss. "
            "Run /languages to see supported languages."
        )
    if brain.language.mode == "auto":
        return (
            "Automatic language detection is enabled, Boss. Speak or type naturally; "
            "I will answer in the language I detect."
        )
    return (
        f"Conversation language set to {language.name}, Boss. "
        "Speech recognition, AI replies, and voice output will use this language."
    )


def _languages(args, brain) -> str:
    names = ", ".join(language.name for language in LANGUAGES.values())
    return (
        f"Supported conversation languages: {names}.\n"
        "Use /language auto or /language Telugu, Boss."
    )


def _translate(args, brain) -> str:
    if len(args) < 2:
        return 'Usage: /translate "language" "text", Boss.'
    target_name = args[0].strip('"')
    target = resolve_language(target_name)
    if target is None:
        return f"Unsupported translation language: {target_name}, Boss."
    text = " ".join(args[1:]).strip('"')
    if not text:
        return "Tell me what text to translate, Boss."
    return brain._nim_completion(
        [
            {
                "role": "system",
                "content": (
                    f"Translate the user's text accurately into {target.name}. "
                    "Preserve meaning, names, formatting, and technical terms. "
                    "Return only the translation."
                ),
            },
            {"role": "user", "content": text},
        ],
        max_tokens=1200,
        temperature=0.1,
    ).strip()


def register(registry) -> None:
    registry.register(
        "language",
        _language,
        "[auto|language] show or change conversation language",
    )
    registry.register("languages", _languages, "list supported conversation languages")
    registry.register("translate", _translate, "<language> <text> translate text")
