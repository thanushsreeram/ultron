from __future__ import annotations

import importlib
import pkgutil
import re
import shlex
from dataclasses import dataclass
from typing import Callable

import requests

import skills
from core.language import LanguageManager


Handler = Callable[[list[str], "UltronBrain"], str]


@dataclass
class RegisteredCommand:
    handler: Handler
    help_text: str


class SkillRegistry:
    def __init__(self) -> None:
        self.commands: dict[str, RegisteredCommand] = {}

    def register(self, name: str, handler: Handler, help_text: str) -> None:
        self.commands[name.lower()] = RegisteredCommand(handler, help_text)

    def discover(self) -> None:
        for module_info in pkgutil.iter_modules(skills.__path__):
            if module_info.name.startswith("_"):
                continue
            module = importlib.import_module(f"skills.{module_info.name}")
            register = getattr(module, "register", None)
            if callable(register):
                register(self)

    def dispatch(self, text: str, brain: "UltronBrain") -> str:
        try:
            parts = shlex.split(text, posix=False)
        except ValueError as exc:
            return f"I could not parse that command, Boss: {exc}"
        if not parts:
            return "Please give me a command, Boss."
        name = parts[0].lstrip("/").lower()
        command = self.commands.get(name)
        if command is None:
            return f"Unknown command /{name}, Boss. Type /help to see available commands."
        try:
            return command.handler(parts[1:], brain)
        except Exception as exc:
            return f"I could not complete that action, Boss: {exc}"

    def help(self) -> str:
        lines = ["Available commands, Boss:"]
        for name, command in sorted(self.commands.items()):
            lines.append(f"/{name} {command.help_text}")
        lines.extend(["/voice toggle voice input", "/exit shut ULTRON down"])
        return "\n".join(lines)


class UltronBrain:
    SYSTEM_PROMPT = (
        "You are ULTRON, a professional, intelligent personal AI assistant. "
        "The user is your Boss; address them as Boss naturally, without overusing it. "
        "Be concise, accurate, proactive, and practical. Never claim that you executed "
        "an action unless a tool result confirms it. Never claim an email, message, file, "
        "or event was sent, delivered, or created based only on conversation. When "
        "teaching, explain clearly and "
        "use examples. Respect privacy and ask before destructive or high-impact actions."
    )

    def __init__(self, settings, memory, voice, language=None) -> None:
        self.settings = settings
        self.memory = memory
        self.voice = voice
        self.language = language or LanguageManager(
            settings.storage_dir / "language.json",
            default=getattr(settings, "language_default", "auto"),
        )
        self.registry = SkillRegistry()
        self.registry.discover()
        self.active_target: dict[str, str] = {}

    def confirm(self, prompt: str) -> bool:
        answer = input(f"ULTRON> {prompt} [y/N] ").strip().lower()
        return answer in {"y", "yes"}

    def handle(self, user_input: str) -> str:
        text = user_input.strip()
        if text and not text.startswith("/"):
            self.language.observe(text)
        if text == "/help" or text.lower() == "help":
            return self._localize_command_result(self.registry.help(), "/help")
        if text.startswith("/"):
            result = self.registry.dispatch(text, self)
            result = self._localize_command_result(result, text)
            self._remember_active_target(text)
            self.memory.add("user", text)
            self.memory.add("assistant", result)
            self.memory.add(
                "action",
                text,
                command=text.split(maxsplit=1)[0],
                result=result[:500],
            )
            return result

        command = self._contextual_command(text) or self._natural_command(text)
        commands = [command] if command else []
        if not commands and (
            self._looks_actionable(text) or self._looks_actionable_multilingual(text)
        ):
            commands = self._route_actions_with_nim(text)
        if commands:
            results = []
            for routed_command in commands:
                result = self.registry.dispatch(routed_command, self)
                result = self._localize_command_result(result, routed_command)
                results.append(result)
                self._remember_active_target(routed_command)
                self.memory.add(
                    "action",
                    text,
                    command=routed_command.split(maxsplit=1)[0],
                    routed_command=routed_command,
                    result=result[:500],
                )
            result = "\n".join(results)
            self.memory.add("user", text)
            self.memory.add("assistant", result)
            return result

        self.memory.add("user", text)
        result = self.chat(text)
        self.memory.add("assistant", result)
        return result

    def _localize_command_result(self, result: str, command: str) -> str:
        if (
            not result
            or self.language.current.code == "en"
            or command.lstrip("/").split(maxsplit=1)[0].lower() == "translate"
            or not self.settings.nvidia_api_key
        ):
            return result
        try:
            return self._nim_completion(
                [
                    {
                        "role": "system",
                        "content": (
                            f"Translate this assistant message into "
                            f"{self.language.current.name}. Preserve commands beginning "
                            "with /, URLs, file paths, code, numbers, and formatting. "
                            "Keep the respectful form of address 'Boss'. Return only "
                            "the translated message."
                        ),
                    },
                    {"role": "user", "content": result},
                ],
                max_tokens=1600,
                temperature=0.1,
            ).strip()
        except (requests.RequestException, KeyError, IndexError, TypeError, ValueError):
            return result

    def _remember_active_target(self, command: str) -> None:
        try:
            parts = shlex.split(command, posix=False)
        except ValueError:
            return
        if not parts:
            return
        name = parts[0].lstrip("/").lower()
        args = [part.strip('"') for part in parts[1:]]
        if name == "browser" and args:
            self.active_target = {"kind": "browser", "name": args[0]}
        elif name == "browser-search" and args:
            self.active_target = {"kind": "browser", "name": args[0]}
        elif name == "website" and args:
            self.active_target = {"kind": "site", "name": args[0]}
        elif name == "site-search" and args:
            self.active_target = {"kind": "site", "name": args[0]}
        elif name in {"open", "app-search"} and args:
            self.active_target = {"kind": "app", "name": args[0]}

    def _contextual_command(self, text: str) -> str | None:
        if re.match(
            r"^(?:yes[, ]*)?(?:send|send it|send the mail|send the email)(?: now)?$",
            text.strip(),
            flags=re.IGNORECASE,
        ):
            return "/email-status"
        if not self.active_target:
            return None
        match = re.match(
            r"^(?:now )?(?:search|look up|find) (?:for )?(.+?)(?: in it| there)?$",
            text.strip(),
            flags=re.IGNORECASE,
        )
        if not match:
            return None
        query = match.group(1)
        kind = self.active_target.get("kind")
        name = self.active_target.get("name", "")
        if kind == "browser":
            return f'/browser "{name}" "{query}"'
        if kind == "site":
            return f'/site-search "{name}" "{query}"'
        if kind == "app":
            return f'/app-search "{name}" "{query}"'
        return None

    def _natural_command(self, text: str) -> str | None:
        routing_text = re.sub(r"\s+", " ", text).strip()
        # Speech recognition sometimes returns the letter "o" instead of zero,
        # for example "5o%" when the user says "50 percent".
        routing_text = re.sub(
            r"\b([0-9])(?:o|O)\b(?=\s*(?:%|percent\b))",
            r"\g<1>0",
            routing_text,
        )
        number_words = {
            "ten": "10",
            "twenty": "20",
            "thirty": "30",
            "forty": "40",
            "fifty": "50",
            "sixty": "60",
            "seventy": "70",
            "eighty": "80",
            "ninety": "90",
            "one hundred": "100",
        }
        for words, digits in number_words.items():
            routing_text = re.sub(
                rf"\b{words}\b(?=\s*(?:%|percent))",
                digits,
                routing_text,
                flags=re.IGNORECASE,
            )
        normalized = re.sub(
            r"^(?:please\s+|could you\s+|can you\s+|would you\s+)+",
            "",
            routing_text,
            flags=re.IGNORECASE,
        )
        lowered = normalized.lower()
        patterns = [
            (
                r"^(?:use|set|change to|switch to) (?:a |the )?"
                r"(male|man|boy|female|woman|girl) voice$",
                r'/voice-type "\1"',
            ),
            (
                r"^(?:change|switch) (?:your |ultron )?voice to "
                r"(male|man|boy|female|woman|girl)$",
                r'/voice-type "\1"',
            ),
            (
                r"^(?:what|which) voice (?:are you using|is active)$",
                r"/voice-type",
            ),
            (
                r"^(?:enable|turn on|add|set up) (?:ultron )?"
                r"(?:automatic )?startup$",
                r"/startup on",
            ),
            (
                r"^(?:disable|turn off|remove|stop) (?:ultron )?"
                r"(?:automatic )?startup$",
                r"/startup off",
            ),
            (
                r"^(?:check|show) (?:ultron )?(?:automatic )?startup"
                r"(?: status)?$",
                r"/startup status",
            ),
            (
                r"^(?:start|open|launch) ultron automatically "
                r"(?:when|after) (?:i )?(?:open|start|sign in to) "
                r"(?:my )?(?:laptop|computer|windows)$",
                r"/startup on",
            ),
            (
                r"^(?:close|lock|secure) (?:my |the )?"
                r"(?:laptop|computer|pc|screen)$",
                r"/lock",
            ),
            (
                r"^(?:speak|talk|reply|answer) (?:to me )?in (.+)$",
                r'/language "\1"',
            ),
            (
                r"^(?:change|set) (?:the )?(?:conversation )?language to (.+)$",
                r'/language "\1"',
            ),
            (r"^(?:detect language automatically|auto language)$", r"/language auto"),
            (r"^తెలుగులో మాట్లాడు$", r'/language "Telugu"'),
            (r"^हिंदी में बात करो$", r'/language "Hindi"'),
            (r"^தமிழில் பேசு$", r'/language "Tamil"'),
            (
                r"^(?:complete|do|start|help me with) (?:my )?"
                r"(?:coding practice|coding practices|code practice)$",
                r"/coding-practice start",
            ),
            (
                r"^(?:open|go to) (?:the )?first (?:not attempted )?"
                r"(?:coding practice|code practice)$",
                r"/coding-practice open-first",
            ),
            (
                r"^(?:inspect|read|explain|understand) (?:the |this )?"
                r"(?:coding )?(?:question|problem|practice)$",
                r"/coding-practice inspect",
            ),
            (
                r"^(?:draft|write|generate) (?:the )?(?:solution|code)"
                r"(?: in (python|javascript|java|c\+\+|c))?$",
                r'/coding-practice draft "\1"',
            ),
            (
                r"^(?:paste|force paste|force past) (?:the )?"
                r"(?:draft|solution|code)$",
                r"/coding-practice paste",
            ),
            (
                r"^(?:run|check) (?:the )?(?:tests|test cases|code)$",
                r"/coding-practice run",
            ),
            (
                r"^(?:check|read|explain) (?:the )?"
                r"(?:test results|test result|feedback)$",
                r"/coding-practice feedback",
            ),
            (
                r"^(?:revise|fix|debug) (?:the )?(?:draft|solution|code)$",
                r"/coding-practice revise",
            ),
            (
                r"^submit (?:the )?(?:coding )?(?:answer|solution|code)$",
                r"/coding-practice submit",
            ),
            (
                r"^(?:next|continue to next) (?:coding )?"
                r"(?:practice|question|problem)$",
                r"/coding-practice next",
            ),
            (
                r"^stop (?:the )?(?:coding coach|coding practice)$",
                r"/coding-practice stop",
            ),
            (
                r"^(?:force paste|force-paste|force past)(?: (?:my )?clipboard)?$",
                r"/force-paste",
            ),
            (
                r"^(?:force paste|force-paste|force past)(?: (?:this|text))? (.+)$",
                r'/force-paste "\1"',
            ),
            (r"^good (morning|afternoon|evening|night)$", r'/greet "\1"'),
            (
                r"^(?:what(?:'s| is) (?:the |current )?time|"
                r"tell me (?:the |current )?time|"
                r"current time|show (?:the )?clock)$",
                r"/clock",
            ),
            (
                r"^(?:what(?:'s| is) (?:the |today'?s? )?date|"
                r"what is today'?s? date|what day is it|"
                r"today'?s date|tell me (?:the |today'?s? )?date)$",
                r"/date",
            ),
            (
                r"^(?:check|scan|look for) (?:any )?(?:windows |system )?"
                r"updates?(?: in settings)?$",
                r"/updates",
            ),
            (
                r"^(?:check|show|tell me) (?:my )?(?:laptop|computer|pc) "
                r"(?:health|details|status|minor details)$",
                r"/health",
            ),
            (
                r"^(?:check|show) (?:the )?(?:minor|minuor|small) details "
                r"(?:of|about) (?:my )?(?:laptop|computer|pc)$",
                r"/health",
            ),
            (r"^(?:check|show) (?:my )?admin(?:istrator)? (?:status|permission)$", r"/admin"),
            (
                r"^(?:give|get|request) (?:administrator|admin) permission$",
                r"/elevate",
            ),
            (r"^(?:run|restart) (?:ultron )?as administrator$", r"/elevate"),
            (
                r"^(?:open|show|go to) (?:the )?(bluetooth|display|sound|audio|wifi|"
                r"network|notifications|power|battery|storage|apps|default apps|privacy|"
                r"updates|windows update|personalization|background|date|time|language|"
                r"microphone|camera|accounts|your info|sign in|email accounts|family|"
                r"themes|colors|lock screen|taskbar|fonts|ethernet|vpn|hotspot|proxy|"
                r"airplane mode|data usage|printers|mouse|touchpad|typing|autoplay|usb|"
                r"installed apps|startup apps|optional features|multitasking|clipboard|"
                r"remote desktop|about|activation|recovery|troubleshoot|backup|security|"
                r"gaming|game mode|accessibility|narrator|magnifier|speech|location) settings$",
                r'/settings "\1"',
            ),
            (r"^(?:open|show|go to) (?:windows )?settings$", r"/settings"),
            (r"^(?:change|manage) (?:my |the )?(?:laptop|windows|system) settings$", r"/settings"),
            (
                r"^(?:open|show|go to) (?:the )?(.+?) settings$",
                r'/settings "\1"',
            ),
            (
                r"^(?:open|launch|start) (chrome|google chrome|edge|microsoft edge|"
                r"brave|firefox|comet|commet) and (?:search|look up) (.+?) "
                r"(?:on|in) (youtube|google|bing|duckduckgo|reddit|github|amazon|"
                r"flipkart|maps|google maps)$",
                r'/browser-search "\1" "\3" "\2"',
            ),
            (
                r"^(?:open|launch|start) (chrome|google chrome|edge|microsoft edge|"
                r"brave|firefox|comet|commet) and (?:search|look up) "
                r"(?:for )?(.+?)(?: and open it| in it)?$",
                r'/browser "\1" "\2"',
            ),
            (
                r"^(?:open|launch|start) (chrome|google chrome|edge|microsoft edge|"
                r"brave|firefox|comet|commet) (?:and )?(?:search|look up) "
                r"(?:for )?(.+?)(?: and open it| in it)?$",
                r'/browser "\1" "\2"',
            ),
            (
                r"^(?:open|launch|start) (.+?) in "
                r"(chrome|google chrome|edge|microsoft edge|brave|firefox|comet|commet)$",
                r'/browser "\2" "\1"',
            ),
            (
                r"^(?:sing|sing a song|play|play a song|play songs|play music)$",
                r'/music "Telugu devotional god songs"',
            ),
            (
                r"^(?:sing|play) (?:a |an |any )?(.+?) (?:song|songs) in "
                r"(chrome|google chrome|edge|microsoft edge|brave|firefox|comet|commet)$",
                r'/music "\1" browser "\2"',
            ),
            (
                r"^(?:sing|play) (?:a |an |any )?(.+?) (?:song|songs)$",
                r'/music "\1"',
            ),
            (
                r"^(?:play|start) (?:a |an |any )?(.+?) (?:song|video) in "
                r"(chrome|google chrome|edge|microsoft edge|brave|firefox|comet|commet)$",
                r'/play "\1 song" browser "\2"',
            ),
            (
                r"^(?:play|start) (?:a |an |any )?(.+?) "
                r"(?:song|video)(?: on youtube)?$",
                r'/play "\1"',
            ),
            (
                r"^(?:play|start) (?:a |an |any )?(?:song|video) "
                r"(?:about|related to|of) (.+)$",
                r'/play "\1"',
            ),
            (
                r"^(?:play|start) (?:a |an |any )?(.+? video)$",
                r'/play "\1"',
            ),
            (
                r"^(?:open|launch|start) (.+?) and (?:open|go to) (.+?) in it$",
                r'/app-search "\1" "\2"',
            ),
            (
                r"^(?:open|launch|start) (.+?) and (?:search|look up|find) "
                r"(?:for )?(.+?)(?: in it)?$",
                r'/app-search "\1" "\2"',
            ),
            (
                r"^(?:open|launch|start) (youtube|google|gmail|outlook|whatsapp|"
                r"facebook|instagram|reddit|github|amazon|flipkart|maps|google maps|"
                r"chatgpt|spotify|netflix|prime video|amazon prime|hotstar|disney plus|"
                r"linkedin|discord|twitch|pinterest|telegram|microsoft 365|office|"
                r"onedrive|google drive|drive|google docs|google sheets|google calendar|"
                r"calendar|meet|zoom|canva|figma|wikipedia|stackoverflow) "
                r"and (?:search|look up) (.+)$",
                r'/site-search "\1" "\2"',
            ),
            (
                r"^(?:search|look up) (.+?) (?:on|in) (youtube|google|bing|"
                r"duckduckgo|reddit|github|amazon|flipkart|maps|google maps)$",
                r'/site-search "\2" "\1"',
            ),
            (
                r"^(?:open|launch|start) (spotify|whatsapp|chatgpt|discord|telegram|"
                r"outlook|zoom) app$",
                r'/open "\1"',
            ),
            (
                r"^(?:open|launch|start|go to) (youtube|google|gmail|outlook|"
                r"whatsapp|facebook|instagram|reddit|github|amazon|flipkart|maps|"
                r"google maps|chatgpt|spotify|netflix|prime video|amazon prime|hotstar|"
                r"disney plus|linkedin|discord|twitch|pinterest|telegram|microsoft 365|"
                r"office|onedrive|google drive|drive|google docs|google sheets|"
                r"google calendar|calendar|meet|zoom|canva|figma|wikipedia|"
                r"stackoverflow|learning portal|ccbp learning portal|ccbp)$",
                r'/website "\1"',
            ),
            (
                r"^(?:open|launch|start|go to) (?:my |the )?"
                r"(learning portal|ccbp learning portal|ccbp)$",
                r'/website "\1"',
            ),
            (r"^(?:open|launch|start) (?:the )?(?:game )?(.+ game)$", r'/game "\1"'),
            (r"^(?:open|launch|start) (?:my )?games$", r"/game"),
            (
                r"^(?:open|launch|start|go to) "
                r"((?:https?://)?[a-z0-9.-]+\.[a-z]{2,}(?:/\S*)?)$",
                r'/website "\1"',
            ),
            (r"^(?:open|launch|start) (?:app )?(.+)$", r'/open "\1"'),
            (r"^(?:close|quit|stop) (?:app )?(.+)$", r'/close "\1"'),
            (r"^(?:search(?: the web)? for|google) (.+)$", r'/search "\1"'),
            (r"^(?:search|look up) (.+?)(?: and show me (?:the )?results)?$", r'/search "\1"'),
            (r"^(?:find|search for|show me|get me) images? (?:of|for)? ?(.+)$", r'/images "\1"'),
            (r"^(?:research|find information about) (.+)$", r'/research "\1"'),
            (r"^(?:open website|go to) (.+)$", r'/website "\1"'),
            (
                r"^(?:write|send|prepare) (?:a )?(?:message|text) to (.+?) "
                r"(?:saying|that says|with message) (.+)$",
                r'/message "\1" "\2"',
            ),
            (
                r"^(?:write|type|prepare) (?:a )?whatsapp (?:message )?to (.+?) "
                r"(?:saying|that says|with message) (.+)$",
                r'/whatsapp-draft "\1" "\2"',
            ),
            (
                r"^(?:find|search for|look for) (.+?) (?:on|in) whatsapp$",
                r'/whatsapp-find "\1"',
            ),
            (
                r"^(?:send|write|draft|prepare) (?:a |an )?(?:mail|email) to "
                r"([^\s]+@[^\s]+) (?:saying|texting|with message|that) (.+)$",
                r'/ai-email "\1" "\2"',
            ),
            (
                r"^(?:send|write|draft|prepare) (?:a |an )?(?:mail|email) to "
                r"([^\s]+@[^\s]+) (.+)$",
                r'/ai-email "\1" "\2"',
            ),
            (
                r"^(?:draft|write|prepare) (?:an? )?email (.+)$",
                r'/draft "email \1"',
            ),
            (
                r"^(?:setup|configure) (?:my )?gmail for ([^\s]+@[^\s]+)$",
                r'/setup-gmail "\1"',
            ),
            (r"^(?:setup|configure) (?:my )?gmail$", r"/setup-gmail"),
            (
                r"^(?:mail|email) ([^\s]+@[^\s]+) (?:text|body|message) (.+)$",
                r'/email "\1" "Hello" "\2"',
            ),
            (
                r"^(?:mail|email) ([^\s]+@[^\s]+) subject (.+?) "
                r"(?:text|body|message) (.+)$",
                r'/email "\1" "\2" "\3"',
            ),
            (
                r"^(?:add|create|schedule) (?:an? )?(?:calendar )?event "
                r"(?:on|for|at) (.+?) (?:called|named|titled) (.+)$",
                r'/event "\1" "\2"',
            ),
            (
                r"^create (?:a )?pdf (?:called|named) (.+?) about (.+)$",
                r'/pdf-topic "\1" "\2"',
            ),
            (
                r"^create (?:a )?(?:short )?video (?:called|named) (.+?) about (.+)$",
                r'/video "\1" "\2"',
            ),
            (
                r"^(?:record|create) (?:a )?voice ?mail (?:to|for) (.+?)(?: for (\d+) seconds)?$",
                r'/voicemail "\1" "\2"',
            ),
            (
                r"^(?:send|email) (?:the )?file (.+?) to (.+?)(?: with subject (.+))?$",
                r'/sendfile "\2" "\1" "\3"',
            ),
            (r"^(?:find|search for|locate) (?:the )?file (.+)$", r'/findfile "\1"'),
            (r"^(?:open|show) (?:the )?file (.+)$", r'/openfile "\1"'),
            (
                r"^(?:explain|summarize|tell me about) (?:the )?file (.+)$",
                r'/summarize-file "\1"',
            ),
            (
                r"^(?:check|read) (?:my )?(?:latest )?(?:mail|email) "
                r"(?:and )?(?:explain|summarize)(?: it)?$",
                r"/summarize-mail",
            ),
            (r"^(?:check|show|list) (?:my )?(?:unread )?(?:mail|email|inbox)$", r"/inbox"),
            (r"^(?:read|open) (?:my )?(?:latest )?(?:mail|email)$", r"/mail"),
            (
                r"^(?:explain|summarize|tell me about) (?:my )?(?:latest )?(?:mail|email)$",
                r"/summarize-mail",
            ),
            (
                r"^(?:remind me|set a reminder) (?:on|at|for) (.+?) (?:to|that) (.+)$",
                r'/remind "\1" "\2"',
            ),
            (
                r"^(?:remind me|set a reminder) to (.+?) "
                r"(?:on|at|for) (.+)$",
                r'/remind "\2" "\1"',
            ),
            (
                r"^(?:remind me|set a reminder) (.+?) (?:to|that) (.+)$",
                r'/remind "\1" "\2"',
            ),
            (r"^(?:teach me|help me learn) (?:about )?(.+)$", r'/teach "\1"'),
            (r"^(?:explain|give me details about) (.+)$", r'/explain "\1"'),
            (
                r"^create (?:a |an )?(note|document|article|plan|story|python|code|text) "
                r"(?:called|named) (.+?) (?:about|that) (.+)$",
                r'/create "\1" "\2" "\3"',
            ),
            (r"^(?:change|modify|edit) (.+?) (?:to|so that) (.+)$", r'/change "\1" "\2"'),
            (r"^(?:store|save) (.+?) as (.+)$", r'/store "\2" "\1"'),
            (r"^(?:retrieve|show me) stored (.+)$", r'/retrieve "\1"'),
            (r"^(?:remember that|remember) (.+)$", r'/remember "\1"'),
            (r"^(?:take a note|note that|note) (.+)$", r'/note "\1"'),
            (r"^(?:what do you remember about|recall) (.+)$", r'/recall "\1"'),
            (r"^what did we (?:discuss|talk about)(?: about)? (.+)$", r'/recall "\1"'),
            (r"^(?:list|show) (?:my )?tasks$", r"/tasks"),
            (r"^add task (.+)$", r'/task add "\1"'),
            (r"^create (?:a )?folder (.+)$", r'/mkdir "\1"'),
            (r"^list files(?: in)?(?: (.+))?$", r'/files "\1"'),
            (r"^read (?:the )?file (.+)$", r'/read "\1"'),
            (r"^copy (.+?) to (.+)$", r'/copy "\1" "\2"'),
            (r"^(?:move|rename) (.+?) to (.+)$", r'/move "\1" "\2"'),
            (r"^organize (?:the )?(?:folder )?(.+)$", r'/organize "\1"'),
            (r"^set (?:the )?volume (up|down|mute)$", r"/volume \1"),
            (r"^set (?:the )?volume to (\d+)(?:\s*%|\s+percent)?$", r"/volume \1"),
            (
                r"^(?:increase|raise|decrease|lower|reduce) (?:the )?volume "
                r"(?:to )?(\d+)(?:\s*%|\s+percent)?$",
                r"/volume \1",
            ),
            (r"^(?:increase|raise|turn up) (?:the )?volume$", r"/volume up"),
            (r"^(?:decrease|lower|reduce|turn down) (?:the )?volume$", r"/volume down"),
            (r"^mute (?:the )?(?:sound|volume|audio)$", r"/volume mute"),
            (r"^unmute (?:the )?(?:sound|volume|audio)$", r"/volume unmute"),
            (r"^set (?:the )?brightness to (\d+)(?:\s*%|\s+percent)?$", r"/brightness \1"),
            (
                r"^(?:increase|raise|decrease|lower|reduce) (?:the )?brightness "
                r"(?:to )?(\d+)(?:\s*%|\s+percent)?$",
                r"/brightness \1",
            ),
            (r"^turn (?:the )?wi-?fi (on|off)$", r"/wifi \1"),
            (r"^enable (?:the )?wi-?fi$", r"/wifi on"),
            (r"^disable (?:the )?wi-?fi$", r"/wifi off"),
            (r"^turn (?:the )?bluetooth (on|off)$", r"/bluetooth \1"),
            (r"^enable (?:the )?bluetooth$", r"/bluetooth on"),
            (r"^disable (?:the )?bluetooth$", r"/bluetooth off"),
            (r"^turn (?:the )?airplane mode (on|off)$", r"/airplane \1"),
            (r"^enable (?:the )?airplane mode$", r"/airplane on"),
            (r"^disable (?:the )?airplane mode$", r"/airplane off"),
            (
                r"^set (?:the )?power mode to "
                r"(balanced|power saver|battery saver|high performance|performance)$",
                r'/power-mode "\1"',
            ),
            (r"^turn (?:the )?(?:screen|display|monitor) off$", r"/display-off"),
            (r"^lock (?:the )?(?:computer|pc|screen)$", r"/lock"),
            (r"^(?:sleep|put (?:the )?(?:computer|pc) to sleep)$", r"/sleep"),
            (r"^(?:show|list) (?:my )?reminders$", r"/reminders"),
            (
                r"^(?:what do i have today|what is on today|what's on today|"
                r"give me (?:my )?daily briefing|today's briefing)$",
                r"/daily",
            ),
            (r"^(?:show|list) (?:my )?(?:usage |action )?history$", r"/history"),
            (r"^(?:what do i use most|show my frequent features)$", r"/frequent"),
            (r"^take (?:a )?screenshot$", r"/screenshot"),
            (r"^(shutdown|restart)(?: the computer)?$", r"/\1"),
        ]
        for pattern, replacement in patterns:
            if re.match(pattern, lowered, flags=re.IGNORECASE):
                return re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
        return None

    @staticmethod
    def _looks_actionable(text: str) -> bool:
        return bool(
            re.match(
                r"^(?:please\s+|could you\s+|can you\s+|would you\s+)?"
                r"(?:open|close|launch|start|stop|search|google|create|make|read|"
                r"write|append|copy|move|rename|delete|organize|remember|forget|"
                r"note|add|list|show|remind|email|send|take|set|turn|run|find|"
                r"research|teach|explain|store|save|retrieve|change|modify|edit)\b",
                text.strip(),
                flags=re.IGNORECASE,
            )
        )

    @staticmethod
    def _looks_actionable_multilingual(text: str) -> bool:
        normalized = text.strip().lower()
        action_words = {
            "te": (
                "తెరువు",
                "ఓపెన్",
                "వెతుకు",
                "సెర్చ్",
                "సృష్టించు",
                "రాయి",
                "పంపు",
                "మార్చు",
                "గుర్తు చేయి",
                "ప్లే",
                "ఆపు",
                "తొలగించు",
            ),
            "hi": (
                "खोलो",
                "खोजो",
                "बनाओ",
                "लिखो",
                "भेजो",
                "बदलो",
                "याद दिलाओ",
                "चलाओ",
                "रुको",
                "हटाओ",
            ),
            "ta": (
                "திற",
                "தேடு",
                "உருவாக்கு",
                "எழுது",
                "அனுப்பு",
                "மாற்று",
                "நினைவூட்டு",
                "இயக்கு",
                "நிறுத்து",
            ),
            "kn": (
                "ತೆರೆ",
                "ಹುಡುಕು",
                "ರಚಿಸು",
                "ಬರೆ",
                "ಕಳುಹಿಸು",
                "ಬದಲಾಯಿಸು",
                "ನೆನಪಿಸು",
                "ಚಲಾಯಿಸು",
                "ನಿಲ್ಲಿಸು",
            ),
            "ml": (
                "തുറക്കുക",
                "തിരയുക",
                "സൃഷ്ടിക്കുക",
                "എഴുതുക",
                "അയയ്ക്കുക",
                "മാറ്റുക",
                "ഓർമ്മിപ്പിക്കുക",
                "പ്ലേ",
                "നിർത്തുക",
            ),
        }
        return any(
            word in normalized
            for words in action_words.values()
            for word in words
        )

    def _route_actions_with_nim(self, text: str) -> list[str]:
        """Translate an action request into a short sequence of registered commands."""
        if not self.settings.nvidia_api_key:
            return []
        command_list = "\n".join(
            f"/{name} {item.help_text}"
            for name, item in sorted(self.registry.commands.items())
        )
        try:
            result = self._nim_completion(
                [
                    {
                        "role": "system",
                        "content": (
                            "Convert the user's request into one or more commands from "
                            "the list below. The request may be in any language. Return "
                            "only slash commands in English, one per line, "
                            "in execution order, with quoted arguments when needed. Use "
                            "at most four commands. Return NONE if no command safely "
                            "matches. Return NONE for greetings, ordinary conversation, "
                            "questions about wellbeing, or general chat. Never invent a "
                            "command.\n\n" + command_list
                        ),
                    },
                    {"role": "user", "content": text},
                ],
                max_tokens=160,
                temperature=0.0,
            ).strip()
        except (requests.RequestException, KeyError, IndexError, TypeError, ValueError):
            return []
        commands = []
        known_sites = {
            "youtube",
            "google",
            "gmail",
            "outlook",
            "whatsapp",
            "spotify",
            "netflix",
            "learning portal",
            "ccbp",
            "ccbp learning portal",
        }
        for line in result.splitlines()[:4]:
            command = line.strip()
            if not command.startswith("/"):
                continue
            name = command.split(maxsplit=1)[0].lstrip("/").lower()
            try:
                parts = shlex.split(command, posix=False)
            except ValueError:
                continue
            if name == "browser" and len(parts) == 2:
                destination = parts[1].strip('"').lower()
                if destination in known_sites or "." in destination:
                    command = f'/website "{destination}"'
                    name = "website"
            if name in self.registry.commands:
                commands.append(command)
        return commands

    def _route_action_with_nim(self, text: str) -> str | None:
        """Backward-compatible helper returning the first routed command."""
        commands = self._route_actions_with_nim(text)
        return commands[0] if commands else None

    def _nim_completion(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int = 1200,
        temperature: float = 0.3,
    ) -> str:
        response = requests.post(
            f"{self.settings.nvidia_base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.settings.nvidia_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.settings.nvidia_model,
                "messages": messages,
                "temperature": temperature,
                "top_p": 0.9,
                "max_tokens": max_tokens,
                "stream": False,
            },
            timeout=90,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def chat(self, prompt: str, extra_system: str = "") -> str:
        if not self.settings.nvidia_api_key:
            return (
                "I need an NVIDIA NIM API key before I can answer conversational "
                "questions, Boss. Add NVIDIA_API_KEY to ultron/.env. Local commands "
                "such as /help, /open, /files, /note, and /tasks already work."
            )

        facts = [
            item["content"]
            for item in self.memory.all()
            if item.get("kind") in {"fact", "preference"}
        ][-20:]
        system = self.SYSTEM_PROMPT
        system += (
            f"\nThe current conversation language is {self.language.current.name}. "
            "Reply in that language, matching the user's script and natural style. "
            "Keep commands, code, URLs, filenames, and technical identifiers unchanged. "
            "If the user mixes languages, follow the dominant language."
        )
        if extra_system:
            system += "\n" + extra_system
        if facts:
            system += "\nUseful remembered facts:\n- " + "\n- ".join(facts)

        messages = [{"role": "system", "content": system}]
        messages.extend(self.memory.recent_conversation(limit=12))
        if not messages or messages[-1].get("content") != prompt:
            messages.append({"role": "user", "content": prompt})

        try:
            return self._nim_completion(messages).strip()
        except requests.RequestException as exc:
            return f"The NVIDIA NIM service is unavailable right now, Boss: {exc}"
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            return f"I received an unexpected response from NVIDIA NIM, Boss: {exc}"

    def due_reminders(self) -> list[str]:
        from skills.study import get_due_reminders

        return get_due_reminders(self.memory)
