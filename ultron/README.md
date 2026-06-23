# ULTRON

ULTRON is a Python-only personal AI assistant that runs in a terminal. It uses
NVIDIA NIM for chat, supports voice input/output, remembers conversations, and
executes modular desktop skills.

## Setup

```powershell
cd ultron
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Add your key to `.env`:

```text
NVIDIA_API_KEY=your_key_here
```

Then run:

```powershell
python main.py
```

After installing the global launcher, ULTRON can be started from any PowerShell,
Command Prompt, or Windows Terminal without opening VS Code:

```text
ultron
```

`ultron` starts voice mode by default. Other forms:

```text
ultron text
ultron voice
ultron --mute
ultron --once "what is the time"
```

ULTRON can also start automatically in voice mode after Windows sign-in:

```text
/startup on
/startup status
/startup off
```

This uses the current user's Windows startup entry and does not require
administrator permission.

For continuous hands-free conversation:

```powershell
python main.py --voice
```

ULTRON supports multilingual conversation, but replies in English by default.
It changes reply language only when you explicitly request another language.
For example:

```text
Boss> మీరు ఎలా ఉన్నారు?
ULTRON> నేను బాగున్నాను, Boss. మీకు ఎలా సహాయం చేయగలను?
```

Language controls:

```text
/language auto
/language Telugu
/language English
/languages
/translate Telugu "How are you?"
```

You can also say `speak to me in Telugu`, `తెలుగులో మాట్లాడు`, or
`speak to me in English`. The selected mode is saved between sessions.
`/language auto` is still available when you intentionally want automatic
language switching.

Choose a male or female speaking voice:

```text
/voice-type male
/voice-type female
/voice-type
```

You can also say `use male voice`, `switch to female voice`, or
`what voice are you using?`. The choice is saved between sessions and applies
to every supported conversation language.

ULTRON listens for one request, processes it, speaks the complete response, and
then listens again. Say `goodbye` or `exit` to stop.

To interrupt a spoken response:

- Press `Esc` while ULTRON is talking.
- In voice mode say `ULTRON stop`, `stop talking`, `cancel`, or `be quiet`.
- Type `/stop` when ULTRON is waiting for input.
- Press `Ctrl+C` during speech to stop that response without crashing ULTRON.

For paragraphs, long questions, emails, or messages, type `/multi`. Enter each
line normally, then type `/done` on a new line to submit everything together.

```text
Boss> /multi
... Draft an email to my teacher explaining:
... I was absent because I was unwell.
... I will submit the assignment tomorrow.
... Keep it polite and concise.
... /done
```

Run a configuration check:

```powershell
python main.py --mute --once "/diagnose"
```

Useful launch options:

```powershell
python main.py --voice
python main.py --mute
python main.py --once "/help"
```

## Main commands

- `/open notepad`, `/close notepad`, `/processes`
- `/apps`, `/apps office` to list or search installed Windows applications
- `/settings bluetooth`, `/settings sound`, `/settings updates`
- `/website nvidia.com`, `/search "Python tutorials"`
- `/browser edge youtube`, `/browser brave "Python tutorials"`
- `/site-search youtube "one piece"`
- `/images "futuristic cars"`, `/research "quantum computing"`
- `/message "John" "I will be late"`, `/whatsapp "919..." "Hello"`
- `/whatsapp-find "John"`, `/whatsapp-draft "John" "I will be late"`
- `/draft "a professional email asking for leave"`
- `/inbox unread`, `/mail 1`, `/summarize-mail 1`
- `/email-status`, `/email-test`
- `/ai-email "person@example.com" "write a polite greeting from Thanush to Haneesh"`
- `/sendfile "name@example.com" "C:\path\report.pdf" "Report"`
- `/event "tomorrow at 4 PM" "Study Python" 60`
- `/events` to list calendar events created through ULTRON
- `/files`, `/read file.txt`, `/write file.txt "hello"`, `/delete file.txt`
- `/copy source.txt backup.txt`, `/tree`, `/organize .`
- `/pdf "notes.pdf" "content"` or `/pdf-topic "ai.pdf" "Artificial intelligence"`
- `/video "ai.mp4" "Artificial intelligence"`
- `/record "voice-note.wav" 20`, `/voicemail "name@example.com" 20`
- `/readpdf "notes.pdf"`
- `/store "project" "important information"`, `/storage`, `/retrieve "project"`
- `/create document "proposal" "a project proposal for..."` 
- `/change "proposal.md" "add a budget section"`
- `/remember "I prefer concise answers"`, `/recall concise`, `/note "idea"`
- `/task add "Revise calculus"`, `/tasks`
- `/remind "2026-06-20 09:00" "Review notes"`
- `/reminder-done "Review notes"`
- `/clock`, `/date`
- `/study "Learn Python in six weeks, one hour daily"`
- `/teach "machine learning"`, `/explain "how neural networks work"`
- `/email "name@example.com" "Subject" "Message"`
- `/code "debug this Python traceback: ..."`
- `/runpy script.py`
- `/coding-practice start` opens the supervised Learning Portal coding coach
- `/coding-practice open-first`, `inspect`, `draft python`, `show`
- `/coding-practice paste`, `run`, `feedback`, `revise`, `submit`, `next`, `stop`
- `/screenshot`, `/volume up`, `/brightness 60`, `/wifi status`
- `/volume 50`, `/bluetooth off`, `/power-mode "power saver"`
- `/display-off`, `/airplane settings`
- `/force-paste` or `/force-paste "text"`
- `/updates`, `/health`, `/admin`, `/elevate`

System inspection examples:

```text
Check any update in settings
Check my laptop minor details
Check my administrator permission
Run ULTRON as administrator
Close my laptop
What is the time?
Good morning
Remind me on June 25 at 5 PM to submit my assignment
```

ULTRON stores reminders locally and also creates a one-time Windows scheduled
task. At the requested time Windows speaks the reminder and displays a reminder
dialog, even when ULTRON is closed. While ULTRON is open, its reminder monitor
also checks every few seconds.

`/updates` only scans and reports; it never installs updates automatically.
`/elevate` opens a Windows UAC prompt. Windows requires you to approve that
prompt personally—ULTRON cannot silently grant itself administrator permission.
- `/shutdown`, `/restart`
- `/game "Minecraft"` or `/game` to open an installed game launcher
- `/daily`, `/history`, `/frequent`
- `/findfile "resume"`, `/openfile "C:\full\path\resume.pdf"`
- `/summarize-file "C:\full\path\report.docx"`

You can say the same requests naturally in voice mode, for example:

```text
Find images of modern bedroom designs
Open Edge and search One Piece on YouTube
Open Comet and open YouTube in it
Open WhatsApp and search John
Open Spotify and search One Piece
Decrease volume to 50 percent
Set brightness to 60 percent
Turn Bluetooth off
Set power mode to power saver
Search Python decorators and show me the results
Write a message to John saying I will be late
Find John in WhatsApp
Check my latest email and explain it
Add a calendar event tomorrow at 4 PM called Study Python
Remind me today at 8 PM to study
Create a PDF called AI Guide about artificial intelligence
Create a video called AI Intro about artificial intelligence
Teach me computer networking from the beginning
Change proposal.md to add a conclusion
Open my games
```

ULTRON also remembers the active app during the current session. For example:

```text
Boss: Open Edge
Boss: Search for Python decorators
```

The second request searches using Edge.

Comet is ULTRON's default browser. Known online services open by URL in Comet:

```text
Open YouTube
Open Spotify
Open Gmail
Open Netflix
Open Google Drive
Open learning portal
Play any Telugu devotional song
Play a Telugu god song in Edge
Play a song
Sing
```

Generic music requests open Spotify in Comet and search for Telugu devotional
god songs. Specific song requests search Spotify for the requested song. Explicit
video requests continue to use YouTube.

## Force paste

Copy text, focus the destination field, then say `force paste` or run:

```text
/force-paste
```

ULTRON waits three seconds and types the clipboard text through Windows keyboard
events. This works in many fields where normal `Ctrl+V` is disabled. You can also
provide text directly with `/force-paste "your text"`.

To force an installed desktop application, include `app`:

```text
Open Spotify app
Open WhatsApp app
```

To choose another browser explicitly:

```text
Open Spotify in Edge
/browser edge spotify
```

Message, email, WhatsApp, and calendar integrations prepare a draft or open the
appropriate application for review. ULTRON does not claim that something was
sent or added until the external application confirms it.

## Optional inbox and direct email setup

Add the following to `.env` using an email-provider app password:

```text
IMAP_HOST=imap.example.com
IMAP_PORT=993
IMAP_USER=you@example.com
IMAP_PASSWORD=your_app_password

SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=you@example.com
SMTP_PASSWORD=your_app_password
SMTP_FROM=you@example.com
```

Without these credentials ULTRON still opens visible email drafts, but it cannot
read an inbox or truthfully confirm that an attachment was sent.

For Gmail, use:

```text
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=youraddress@gmail.com
SMTP_PASSWORD=your_16_character_app_password
SMTP_FROM=youraddress@gmail.com

IMAP_HOST=imap.gmail.com
IMAP_PORT=993
IMAP_USER=youraddress@gmail.com
IMAP_PASSWORD=your_16_character_app_password
```

Enable two-step verification on the Google account and create a Google app
password. Do not place your normal Gmail password in `.env`.

You can configure this interactively without displaying the app password:

```text
/setup-gmail youraddress@gmail.com
```

Restart ULTRON afterward and run `/email-test`.

ULTRON asks for confirmation before destructive or high-impact actions.

## Supervised Coding Coach

Say `complete my coding practice` or run:

```text
/coding-practice start
```

Log in to the Learning Portal yourself. ULTRON can then navigate to Question
Bank and Not Attempted, explain one problem, create a draft, force-paste it,
run visible tests, summarize failures, and prepare a revision. Use:

```text
/coding-practice open-first
/coding-practice inspect
/coding-practice draft python
/coding-practice show
/coding-practice paste
/coding-practice run
/coding-practice feedback
/coding-practice revise
/coding-practice submit
/coding-practice next
/coding-practice stop
```

This mode is intentionally supervised. Paste and submission require confirmation,
and ULTRON will not silently complete or submit an entire course. Press `Esc` or
say `ULTRON stop` to stop speech and close the controlled coding browser.

## Adding a skill

Create a Python file in `skills/` with handlers and a `register` function:

```python
def hello(args, brain):
    return "Hello, Boss."

def register(registry):
    registry.register("hello", hello, "say hello")
```

It will be discovered automatically the next time ULTRON starts.
# ultron
