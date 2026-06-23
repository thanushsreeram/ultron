from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Language:
    code: str
    name: str
    locale: str
    female_voice: str
    male_voice: str
    aliases: tuple[str, ...]


LANGUAGES: dict[str, Language] = {
    "en": Language(
        "en",
        "English",
        "en-IN",
        "en-IN-NeerjaNeural",
        "en-IN-PrabhatNeural",
        ("english",),
    ),
    "te": Language(
        "te",
        "Telugu",
        "te-IN",
        "te-IN-ShrutiNeural",
        "te-IN-MohanNeural",
        ("telugu", "తెలుగు", "telungu"),
    ),
    "hi": Language(
        "hi", "Hindi", "hi-IN", "hi-IN-SwaraNeural", "hi-IN-MadhurNeural", ("hindi", "हिंदी")
    ),
    "ta": Language(
        "ta", "Tamil", "ta-IN", "ta-IN-PallaviNeural", "ta-IN-ValluvarNeural", ("tamil", "தமிழ்")
    ),
    "kn": Language(
        "kn", "Kannada", "kn-IN", "kn-IN-SapnaNeural", "kn-IN-GaganNeural", ("kannada", "ಕನ್ನಡ")
    ),
    "ml": Language(
        "ml", "Malayalam", "ml-IN", "ml-IN-SobhanaNeural", "ml-IN-MidhunNeural", ("malayalam", "മലയാളം")
    ),
    "mr": Language(
        "mr", "Marathi", "mr-IN", "mr-IN-AarohiNeural", "mr-IN-ManoharNeural", ("marathi", "मराठी")
    ),
    "bn": Language("bn", "Bengali", "bn-IN", "bn-IN-TanishaaNeural", "bn-IN-BashkarNeural", ("bengali", "বাংলা")),
    "gu": Language("gu", "Gujarati", "gu-IN", "gu-IN-DhwaniNeural", "gu-IN-NiranjanNeural", ("gujarati", "ગુજરાતી")),
    "pa": Language(
        "pa",
        "Punjabi",
        "pa-IN",
        "hi-IN-SwaraNeural",
        "hi-IN-MadhurNeural",
        ("punjabi", "ਪੰਜਾਬੀ"),
    ),
    "ur": Language("ur", "Urdu", "ur-PK", "ur-PK-UzmaNeural", "ur-PK-AsadNeural", ("urdu", "اردو")),
    "es": Language("es", "Spanish", "es-ES", "es-ES-ElviraNeural", "es-ES-AlvaroNeural", ("spanish", "español")),
    "fr": Language("fr", "French", "fr-FR", "fr-FR-DeniseNeural", "fr-FR-HenriNeural", ("french", "français")),
    "de": Language("de", "German", "de-DE", "de-DE-KatjaNeural", "de-DE-ConradNeural", ("german", "deutsch")),
    "pt": Language(
        "pt", "Portuguese", "pt-BR", "pt-BR-FranciscaNeural", "pt-BR-AntonioNeural", ("portuguese", "português")
    ),
    "ar": Language("ar", "Arabic", "ar-SA", "ar-SA-ZariyahNeural", "ar-SA-HamedNeural", ("arabic", "العربية")),
    "ru": Language("ru", "Russian", "ru-RU", "ru-RU-SvetlanaNeural", "ru-RU-DmitryNeural", ("russian", "русский")),
    "ja": Language("ja", "Japanese", "ja-JP", "ja-JP-NanamiNeural", "ja-JP-KeitaNeural", ("japanese", "日本語")),
    "ko": Language("ko", "Korean", "ko-KR", "ko-KR-SunHiNeural", "ko-KR-InJoonNeural", ("korean", "한국어")),
    "zh": Language(
        "zh", "Chinese", "zh-CN", "zh-CN-XiaoxiaoNeural", "zh-CN-YunxiNeural", ("chinese", "中文", "mandarin")
    ),
}

SCRIPT_RANGES = (
    ("te", "\u0c00", "\u0c7f"),
    ("ta", "\u0b80", "\u0bff"),
    ("kn", "\u0c80", "\u0cff"),
    ("ml", "\u0d00", "\u0d7f"),
    ("bn", "\u0980", "\u09ff"),
    ("gu", "\u0a80", "\u0aff"),
    ("pa", "\u0a00", "\u0a7f"),
    ("hi", "\u0900", "\u097f"),
    ("ar", "\u0600", "\u06ff"),
    ("ru", "\u0400", "\u04ff"),
    ("ja", "\u3040", "\u30ff"),
    ("ko", "\uac00", "\ud7af"),
    ("zh", "\u4e00", "\u9fff"),
)


def resolve_language(value: str) -> Language | None:
    normalized = value.strip().lower()
    if normalized in LANGUAGES:
        return LANGUAGES[normalized]
    for language in LANGUAGES.values():
        if normalized in language.aliases or normalized == language.locale.lower():
            return language
    return None


def detect_script(text: str) -> str | None:
    counts: dict[str, int] = {}
    for character in text:
        for code, start, end in SCRIPT_RANGES:
            if start <= character <= end:
                counts[code] = counts.get(code, 0) + 1
                break
    return max(counts, key=lambda code: counts[code]) if counts else None


class LanguageManager:
    def __init__(self, path: Path, default: str = "auto") -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.mode = "auto"
        self.current_code = "en"
        self.voice_gender = "female"
        self._load(default)

    @property
    def current(self) -> Language:
        return LANGUAGES.get(self.current_code, LANGUAGES["en"])

    def _load(self, default: str) -> None:
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                mode = str(data.get("mode", default)).lower()
                current = str(data.get("current", "en")).lower()
                voice_gender = str(data.get("voice_gender", "female")).lower()
                self.mode = mode if mode == "auto" or resolve_language(mode) else "auto"
                self.current_code = current if current in LANGUAGES else "en"
                self.voice_gender = (
                    voice_gender if voice_gender in {"male", "female"} else "female"
                )
                return
            except (OSError, ValueError, TypeError):
                pass
        self.set_mode(default)

    def _save(self) -> None:
        self.path.write_text(
            json.dumps(
                {
                    "mode": self.mode,
                    "current": self.current_code,
                    "voice_gender": self.voice_gender,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def set_mode(self, value: str) -> Language:
        normalized = value.strip().lower()
        if normalized in {"auto", "automatic", "detect"}:
            self.mode = "auto"
        else:
            language = resolve_language(normalized)
            if language is None:
                raise ValueError(f"Unsupported language: {value}")
            self.mode = language.code
            self.current_code = language.code
        self._save()
        return self.current

    def detect(self, text: str) -> Language:
        script = detect_script(text)
        if script:
            return LANGUAGES[script]
        clean = re.sub(r"[\d\W_]+", " ", text, flags=re.UNICODE).strip()
        if len(clean) >= 4:
            try:
                from langdetect import DetectorFactory, detect

                DetectorFactory.seed = 0
                code = detect(clean)
                if code in LANGUAGES:
                    return LANGUAGES[code]
            except Exception:
                pass
        if clean and clean.isascii():
            return LANGUAGES["en"]
        return self.current if self.mode != "auto" else LANGUAGES["en"]

    def observe(self, text: str) -> Language:
        if self.mode == "auto":
            detected = self.detect(text)
            self.current_code = detected.code
            self._save()
        return self.current

    def recognition_languages(self, interrupt_only: bool = False) -> list[Language]:
        if self.mode != "auto":
            # Keep the selected reply language fixed, while still recognizing
            # common language-switch and stop commands spoken in other languages.
            priority = [self.current_code, "en", "te", "hi", "ta"]
            seen: set[str] = set()
            result = []
            for code in priority:
                if code in LANGUAGES and code not in seen:
                    seen.add(code)
                    result.append(LANGUAGES[code])
            return result
        priority = ["en", "te", "hi", "ta", "kn", "ml", "mr", "bn"]
        ordered = [self.current_code, *priority]
        if interrupt_only:
            ordered = [self.current_code, "en", "te"]
        seen: set[str] = set()
        result = []
        for code in ordered:
            if code in LANGUAGES and code not in seen:
                seen.add(code)
                result.append(LANGUAGES[code])
        return result

    @property
    def voice_name(self) -> str:
        return (
            self.current.male_voice
            if self.voice_gender == "male"
            else self.current.female_voice
        )

    def set_voice_gender(self, value: str) -> str:
        normalized = value.strip().lower()
        aliases = {
            "man": "male",
            "boy": "male",
            "masculine": "male",
            "woman": "female",
            "girl": "female",
            "feminine": "female",
        }
        normalized = aliases.get(normalized, normalized)
        if normalized not in {"male", "female"}:
            raise ValueError(f"Unsupported voice type: {value}")
        self.voice_gender = normalized
        self._save()
        return self.voice_gender

    def choose_transcript(self, candidates: list[tuple[Language, str]]) -> str:
        if not candidates:
            return ""
        for requested, text in candidates:
            script = detect_script(text)
            if script and script == requested.code:
                if self.mode == "auto":
                    self.current_code = script
                    self._save()
                return text
        for requested, text in candidates:
            detected = self.detect(text)
            if detected.code == requested.code:
                if self.mode == "auto":
                    self.current_code = detected.code
                    self._save()
                return text
        requested, text = candidates[0]
        if self.mode == "auto":
            self.current_code = requested.code
            self._save()
        return text

    def status(self) -> str:
        mode = "automatic detection" if self.mode == "auto" else "fixed"
        return f"{self.current.name} ({mode}), {self.voice_gender} voice"
