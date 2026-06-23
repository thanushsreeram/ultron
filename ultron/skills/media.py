from __future__ import annotations

import os
import shutil
import subprocess
import textwrap
from pathlib import Path


def _record_wav(path: Path, seconds: int) -> None:
    import sounddevice as sd
    from scipy.io.wavfile import write

    device = sd.query_devices(kind="input")
    sample_rate = int(device["default_samplerate"])
    audio = sd.rec(
        int(seconds * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype="int16",
    )
    sd.wait()
    write(path, sample_rate, audio)


def _record(args, brain) -> str:
    name = args[0].strip('"') if args else "voice-note.wav"
    seconds = int(args[1].strip('"')) if len(args) > 1 and args[1].strip('"').isdigit() else 15
    seconds = max(1, min(300, seconds))
    if not name.lower().endswith(".wav"):
        name += ".wav"
    path = (brain.settings.workspace / name).resolve()
    path.relative_to(brain.settings.workspace.resolve())
    path.parent.mkdir(parents=True, exist_ok=True)
    print(f"ULTRON> Recording for {seconds} seconds...")
    _record_wav(path, seconds)
    return f"Voice recording saved to {path}, Boss."


def _voice_mail(args, brain) -> str:
    if not args:
        return 'Usage: /voicemail "recipient@example.com" [seconds], Boss.'
    recipient = args[0].strip('"')
    seconds = int(args[1].strip('"')) if len(args) > 1 and args[1].strip('"').isdigit() else 20
    seconds = max(1, min(300, seconds))
    path = brain.settings.workspace / "voice-mail.wav"
    print(f"ULTRON> Recording voice mail for {seconds} seconds...")
    _record_wav(path, seconds)
    from skills.email_tools import _send_file

    return _send_file(
        [recipient, str(path), "Voice mail from ULTRON", "Please find my voice message attached."],
        brain,
    )


def _create_narration(text: str, path: Path, rate: int) -> None:
    script = (
        "Add-Type -AssemblyName System.Speech;"
        "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
        f"$s.Rate={max(-10, min(10, round((rate - 180) / 15)))};"
        "$s.SetOutputToWaveFile($env:ULTRON_WAVE);"
        "$s.Speak($env:ULTRON_TEXT);$s.Dispose()"
    )
    environment = os.environ.copy()
    environment["ULTRON_WAVE"] = str(path)
    environment["ULTRON_TEXT"] = text
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        env=environment,
        check=True,
        capture_output=True,
        text=True,
        timeout=180,
    )


def _video(args, brain) -> str:
    if len(args) < 2:
        return 'Usage: /video "file.mp4" "topic or script", Boss.'
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return "FFmpeg is required to create videos, Boss."
    from PIL import Image, ImageDraw, ImageFont

    name = args[0].strip('"')
    if not name.lower().endswith(".mp4"):
        name += ".mp4"
    output = (brain.settings.workspace / name).resolve()
    output.relative_to(brain.settings.workspace.resolve())
    output.parent.mkdir(parents=True, exist_ok=True)
    request = " ".join(args[1:]).strip('"')
    script = brain.chat(
        f"Write a concise 45 to 75 word narration for a short informational video about: {request}",
        extra_system="Return only the narration, without headings or stage directions.",
    )
    temp_dir = brain.settings.storage_dir / "video-temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    image_path = temp_dir / "slide.png"
    audio_path = temp_dir / "narration.wav"

    image = Image.new("RGB", (1280, 720), (10, 16, 30))
    draw = ImageDraw.Draw(image)
    try:
        title_font = ImageFont.truetype("arialbd.ttf", 54)
        body_font = ImageFont.truetype("arial.ttf", 30)
    except OSError:
        title_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
    title = request[:80]
    draw.text((80, 90), title, fill=(80, 200, 255), font=title_font)
    wrapped = "\n".join(textwrap.wrap(script, width=62))
    draw.multiline_text((80, 210), wrapped, fill="white", font=body_font, spacing=12)
    image.save(image_path)
    _create_narration(script, audio_path, brain.settings.voice_rate)
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-loop",
            "1",
            "-i",
            str(image_path),
            "-i",
            str(audio_path),
            "-c:v",
            "libx264",
            "-tune",
            "stillimage",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-pix_fmt",
            "yuv420p",
            "-shortest",
            str(output),
        ],
        check=True,
        capture_output=True,
        timeout=180,
    )
    return f"Video created at {output}, Boss."


def register(registry) -> None:
    registry.register("record", _record, "[file.wav] [seconds] record a voice note")
    registry.register("voicemail", _voice_mail, "<email> [seconds] record and email voice")
    registry.register("video", _video, "<file.mp4> <topic> create a narrated video")
