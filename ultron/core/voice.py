from __future__ import annotations

import os
import platform
import re
import subprocess
import sys
import tempfile
import threading
import time
import unicodedata


class VoiceInterface:
    STOP_PHRASES = {
        "stop",
        "ultron stop",
        "stop ultron",
        "stop talking",
        "be quiet",
        "cancel",
        "cancel response",
        "never mind",
        "nevermind",
        "ఆపు",
        "అల్ట్రాన్ ఆపు",
        "బస్",
        "रुको",
        "बंद करो",
        "நிறுத்து",
    }

    def __init__(self, enabled: bool = True, rate: int = 180, language=None):
        self.enabled = enabled
        self.rate = rate
        self.language = language
        self._engine = None
        self._speak_lock = threading.Lock()
        self._recognizer = None
        self._speech_process: subprocess.Popen | None = None
        self._stop_speech = threading.Event()
        self._speaking = threading.Event()
        self.last_error = ""

    def _get_engine(self):
        if self._engine is None:
            import pyttsx3

            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", self.rate)
        return self._engine

    @classmethod
    def is_stop_phrase(cls, text: str) -> bool:
        normalized = "".join(
            character
            for character in text.lower()
            if character.isalnum()
            or character.isspace()
            or unicodedata.category(character).startswith("M")
        )
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized in cls.STOP_PHRASES

    def _wait_for_process(self, process: subprocess.Popen) -> bool:
        self._speech_process = process
        while process.poll() is None:
            if self._stop_speech.is_set() or self._escape_pressed():
                self.stop_speaking()
                return False
            time.sleep(0.05)
        return not self._stop_speech.is_set()

    def _speak_edge(self, text: str) -> bool:
        if self.language is None:
            return False
        media = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        media_path = media.name
        media.close()
        try:
            generator = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "edge_tts",
                    "--voice",
                    self.language.voice_name,
                    "--text",
                    text,
                    "--write-media",
                    media_path,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
            if not self._wait_for_process(generator):
                return False
            if generator.returncode != 0:
                error = generator.stderr.read().strip() if generator.stderr else ""
                raise RuntimeError(error or "multilingual speech generation failed")
            script = (
                "Add-Type -AssemblyName PresentationCore;"
                "$player=New-Object System.Windows.Media.MediaPlayer;"
                "$player.Open([Uri]$env:ULTRON_AUDIO_FILE);"
                "$player.Play();"
                "while(-not $player.NaturalDuration.HasTimeSpan){Start-Sleep -Milliseconds 50};"
                "$duration=$player.NaturalDuration.TimeSpan.TotalMilliseconds;"
                "Start-Sleep -Milliseconds ([int]$duration+150);"
                "$player.Stop();$player.Close()"
            )
            environment = os.environ.copy()
            environment["ULTRON_AUDIO_FILE"] = media_path
            player = subprocess.Popen(
                ["powershell", "-NoProfile", "-Command", script],
                env=environment,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
            if not self._wait_for_process(player):
                return False
            if player.returncode != 0:
                error = player.stderr.read().strip() if player.stderr else ""
                raise RuntimeError(error or "multilingual audio playback failed")
            return True
        finally:
            try:
                os.unlink(media_path)
            except OSError:
                pass

    def _speak_windows_sapi(self, text: str) -> bool:
        rate = max(-10, min(10, round((self.rate - 180) / 15)))
        script = (
            "Add-Type -AssemblyName System.Speech;"
            "$speaker=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
            f"$speaker.Rate={rate};"
            "$speaker.Speak($env:ULTRON_SPEECH_TEXT);"
            "$speaker.Dispose()"
        )
        environment = os.environ.copy()
        environment["ULTRON_SPEECH_TEXT"] = text
        process = subprocess.Popen(
            ["powershell", "-NoProfile", "-Command", script],
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        if not self._wait_for_process(process):
            return False
        if process.returncode != 0:
            error = process.stderr.read().strip() if process.stderr else ""
            raise RuntimeError(error or "Windows speech synthesis failed")
        return True

    def _speak_windows(self, text: str) -> bool:
        if self.language is None:
            return self._speak_windows_sapi(text)
        try:
            return self._speak_edge(text)
        except Exception:
            return self._speak_windows_sapi(text)

    @staticmethod
    def _escape_pressed() -> bool:
        if platform.system() != "Windows":
            return False
        try:
            import msvcrt

            if not msvcrt.kbhit():
                return False
            key = msvcrt.getwch()
            return key == "\x1b"
        except (ImportError, OSError):
            return False

    def stop_speaking(self) -> bool:
        self._stop_speech.set()
        stopped = self._speaking.is_set()
        process = self._speech_process
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
        if self._engine is not None:
            try:
                self._engine.stop()
            except Exception:
                pass
        return stopped

    def _listen_for_stop(self) -> None:
        time.sleep(0.4)
        while self._speaking.is_set() and not self._stop_speech.is_set():
            phrase = self.listen(
                timeout=1,
                phrase_time_limit=3,
                quiet=True,
                interrupt_only=True,
            )
            if phrase and self.is_stop_phrase(phrase):
                self.stop_speaking()
                return

    @staticmethod
    def _speech_text(text: str) -> str:
        text = re.sub(r"```.*?```", " Code example omitted from speech. ", text, flags=re.DOTALL)
        text = re.sub(r"https?://\S+", " link ", text)
        text = re.sub(r"[*_`#>|]", "", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def speak(self, text: str, allow_voice_interrupt: bool = False) -> bool:
        if not self.enabled or not text:
            return False
        try:
            with self._speak_lock:
                self._stop_speech.clear()
                self._speaking.set()
                speech = self._speech_text(text)[:6000]
                listener = None
                if allow_voice_interrupt:
                    listener = threading.Thread(
                        target=self._listen_for_stop,
                        daemon=True,
                    )
                    listener.start()
                if platform.system() == "Windows":
                    completed = self._speak_windows(speech)
                else:
                    engine = self._get_engine()
                    engine.say(speech)
                    engine.runAndWait()
                    completed = not self._stop_speech.is_set()
                self._speaking.clear()
                self._speech_process = None
                if not completed:
                    print("ULTRON> Response interrupted, Boss.")
            self.last_error = ""
            return completed
        except KeyboardInterrupt:
            self.stop_speaking()
            self._speaking.clear()
            self._speech_process = None
            print("\nULTRON> Response interrupted, Boss.")
            return False
        except Exception as exc:
            self._speaking.clear()
            self._speech_process = None
            self.last_error = str(exc)
            self.enabled = False
            print(f"ULTRON> Speech output unavailable ({exc}).")
            return False

    def listen(
        self,
        timeout: int = 6,
        phrase_time_limit: int = 20,
        quiet: bool = False,
        interrupt_only: bool = False,
    ) -> str:
        try:
            import speech_recognition as sr
        except ImportError as exc:
            self.last_error = f"Voice input unavailable: {exc}"
            print(f"ULTRON> {self.last_error}")
            return ""
        try:
            if self._recognizer is None:
                self._recognizer = sr.Recognizer()
                self._recognizer.dynamic_energy_threshold = True
                self._recognizer.pause_threshold = 0.8
            recognizer = self._recognizer
            if not quiet:
                print("ULTRON> Listening...")
            audio = self._record_with_sounddevice(
                sr, timeout=timeout, phrase_time_limit=phrase_time_limit
            )
            if audio is None:
                return ""
            if not quiet:
                print("ULTRON> Understanding...")
            recognize_google = getattr(recognizer, "recognize_google")
            if self.language is None:
                result = recognize_google(audio).strip()
            else:
                candidates = []
                for language in self.language.recognition_languages(interrupt_only):
                    try:
                        result = recognize_google(
                            audio,
                            language=language.locale,
                        ).strip()
                    except sr.UnknownValueError:
                        continue
                    if result:
                        candidates.append((language, result))
                result = self.language.choose_transcript(candidates)
                if not result:
                    raise sr.UnknownValueError()
            self.last_error = ""
            return result
        except sr.WaitTimeoutError:
            self.last_error = ""
            return ""
        except sr.UnknownValueError:
            self.last_error = "I could not understand that."
            if not quiet:
                print("ULTRON> I could not understand that. Please speak again.")
            return ""
        except sr.RequestError as exc:
            self.last_error = f"Speech recognition service error: {exc}"
            if not quiet:
                print(f"ULTRON> {self.last_error}")
            return ""
        except Exception as exc:
            self.last_error = f"Voice input unavailable: {exc}"
            if not quiet:
                print(f"ULTRON> {self.last_error}")
            return ""

    def _record_with_sounddevice(self, sr, timeout: int, phrase_time_limit: int):
        """Record one spoken phrase without relying on PyAudio."""
        import numpy as np
        import sounddevice as sd

        device = sd.query_devices(kind="input")
        sample_rate = int(device["default_samplerate"])
        block_size = max(512, int(sample_rate * 0.05))
        calibration_blocks = max(1, int(0.35 / (block_size / sample_rate)))
        ambient_levels: list[float] = []
        frames: list[bytes] = []
        speech_started = False
        silent_for = 0.0
        started_at = time.monotonic()

        with sd.RawInputStream(
            samplerate=sample_rate,
            blocksize=block_size,
            channels=1,
            dtype="int16",
        ) as stream:
            for _ in range(calibration_blocks):
                data, _ = stream.read(block_size)
                samples = np.frombuffer(data, dtype=np.int16).astype(np.float32)
                ambient_levels.append(float(np.sqrt(np.mean(samples * samples))))

            ambient = sum(ambient_levels) / max(1, len(ambient_levels))
            threshold = max(250.0, ambient * 2.5)

            while True:
                now = time.monotonic()
                elapsed = now - started_at
                if not speech_started and elapsed >= timeout:
                    return None
                if speech_started and elapsed >= timeout + phrase_time_limit:
                    break

                data, _ = stream.read(block_size)
                raw = bytes(data)
                samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
                level = float(np.sqrt(np.mean(samples * samples)))
                block_seconds = block_size / sample_rate

                if level >= threshold:
                    speech_started = True
                    silent_for = 0.0
                elif speech_started:
                    silent_for += block_seconds

                if speech_started:
                    frames.append(raw)
                    if silent_for >= 1.0:
                        break

        if not frames:
            return None
        return sr.AudioData(b"".join(frames), sample_rate, 2)
