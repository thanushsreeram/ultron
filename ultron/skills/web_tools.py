from __future__ import annotations

import smtplib
import subprocess
import re
import html
import urllib.parse
import webbrowser
from email.message import EmailMessage
from email.utils import formatdate, make_msgid, parseaddr

import requests
from bs4 import BeautifulSoup

from skills.apps import _find_start_app, _launch_start_app, installed_browsers, resolve_windows_app


SITES = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "outlook": "https://outlook.live.com/mail/",
    "whatsapp": "https://web.whatsapp.com",
    "facebook": "https://www.facebook.com",
    "instagram": "https://www.instagram.com",
    "x": "https://x.com",
    "twitter": "https://x.com",
    "reddit": "https://www.reddit.com",
    "github": "https://github.com",
    "amazon": "https://www.amazon.in",
    "flipkart": "https://www.flipkart.com",
    "maps": "https://maps.google.com",
    "google maps": "https://maps.google.com",
    "chatgpt": "https://chatgpt.com",
    "spotify": "https://open.spotify.com",
    "netflix": "https://www.netflix.com",
    "prime video": "https://www.primevideo.com",
    "amazon prime": "https://www.primevideo.com",
    "hotstar": "https://www.hotstar.com",
    "disney plus": "https://www.hotstar.com",
    "linkedin": "https://www.linkedin.com",
    "discord": "https://discord.com/app",
    "twitch": "https://www.twitch.tv",
    "pinterest": "https://www.pinterest.com",
    "telegram": "https://web.telegram.org",
    "microsoft 365": "https://www.microsoft365.com",
    "office": "https://www.microsoft365.com",
    "onedrive": "https://onedrive.live.com",
    "google drive": "https://drive.google.com",
    "drive": "https://drive.google.com",
    "google docs": "https://docs.google.com",
    "google sheets": "https://sheets.google.com",
    "google calendar": "https://calendar.google.com",
    "calendar": "https://calendar.google.com",
    "meet": "https://meet.google.com",
    "zoom": "https://zoom.us",
    "canva": "https://www.canva.com",
    "figma": "https://www.figma.com",
    "wikipedia": "https://www.wikipedia.org",
    "stackoverflow": "https://stackoverflow.com",
    "youtube music": "https://music.youtube.com",
    "gaana": "https://gaana.com",
    "jiosaavn": "https://www.jiosaavn.com",
    "soundcloud": "https://soundcloud.com",
    "apple music": "https://music.apple.com",
    "news": "https://news.google.com",
    "learning portal": "https://learning.ccbp.in/",
    "ccbp learning portal": "https://learning.ccbp.in/",
    "ccbp": "https://learning.ccbp.in/",
}

SITE_SEARCH = {
    "youtube": "https://www.youtube.com/results?search_query={query}",
    "google": "https://www.google.com/search?q={query}",
    "bing": "https://www.bing.com/search?q={query}",
    "duckduckgo": "https://duckduckgo.com/?q={query}",
    "reddit": "https://www.reddit.com/search/?q={query}",
    "github": "https://github.com/search?q={query}",
    "amazon": "https://www.amazon.in/s?k={query}",
    "flipkart": "https://www.flipkart.com/search?q={query}",
    "maps": "https://www.google.com/maps/search/{query}",
    "google maps": "https://www.google.com/maps/search/{query}",
    "spotify": "https://open.spotify.com/search/{query}",
    "youtube music": "https://music.youtube.com/search?q={query}",
    "linkedin": "https://www.linkedin.com/search/results/all/?keywords={query}",
    "twitch": "https://www.twitch.tv/search?term={query}",
    "pinterest": "https://www.pinterest.com/search/pins/?q={query}",
    "wikipedia": "https://en.wikipedia.org/w/index.php?search={query}",
    "stackoverflow": "https://stackoverflow.com/search?q={query}",
}


def _clean_email_field(value: str) -> str:
    value = value.strip()
    while len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1].strip()
    return value.replace("\r\n", "\n").replace("\r", "\n")


def _mailto_url(recipient: str, subject: str, body: str) -> str:
    query = urllib.parse.urlencode(
        {"subject": subject, "body": body},
        quote_via=urllib.parse.quote,
        safe="",
    )
    return f"mailto:{urllib.parse.quote(recipient, safe='@._+-')}?{query}"


def _normalize_url(value: str) -> str:
    value = value.strip().strip('"')
    if not value.startswith(("http://", "https://")):
        value = "https://" + value
    return value


def _website(args, brain) -> str:
    if not args:
        return "Tell me which website to open, Boss."
    value = " ".join(args).strip('"')
    url = SITES.get(value.lower(), _normalize_url(value))
    opened = _launch_in_browser(brain.settings.default_browser, url)
    return f"Opened {url} in {opened}, Boss."


def _launch_in_browser(browser: str, url: str) -> str:
    if browser.strip().lower() == "commet":
        browser = "comet"
    path = resolve_windows_app(browser)
    if path:
        subprocess.Popen(
            [path, url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return browser
    start_app = _find_start_app(browser)
    if start_app:
        _launch_start_app(start_app["app_id"])
        webbrowser.open(url)
        return start_app["name"]
    webbrowser.open(url)
    return "default browser"


def _browser(args, brain) -> str:
    if not args:
        names = sorted(set(installed_browsers()))
        return (
            "Installed browsers:\n" + "\n".join(f"- {name}" for name in names)
            if names
            else "I found no registered browsers, Boss."
        )
    browser = args[0].strip('"')
    destination = " ".join(args[1:]).strip('"') if len(args) > 1 else ""
    if not destination:
        url = "about:blank"
    elif destination.lower() in SITES:
        url = SITES[destination.lower()]
    elif destination.startswith(("http://", "https://")):
        url = destination
    elif "." in destination and " " not in destination:
        url = _normalize_url(destination)
    else:
        url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(destination)
    opened = _launch_in_browser(browser, url)
    return f"Opened {url} in {opened}, Boss."


def _site_search(args, brain) -> str:
    if len(args) < 2:
        return 'Usage: /site-search "site" "query", Boss.'
    site = args[0].strip('"').lower()
    query = " ".join(args[1:]).strip('"')
    template = SITE_SEARCH.get(site)
    if not template:
        url = (
            "https://www.google.com/search?q="
            + urllib.parse.quote_plus(f"site:{site} {query}")
        )
    else:
        url = template.format(query=urllib.parse.quote_plus(query))
    opened = _launch_in_browser(brain.settings.default_browser, url)
    return f"Searching {site} for “{query}” in {opened}, Boss."


def _browser_search(args, brain) -> str:
    if len(args) < 3:
        return 'Usage: /browser-search "browser" "site" "query", Boss.'
    browser = args[0].strip('"')
    site = args[1].strip('"').lower()
    query = " ".join(args[2:]).strip('"')
    template = SITE_SEARCH.get(site)
    url = (
        template.format(query=urllib.parse.quote_plus(query))
        if template
        else "https://www.google.com/search?q="
        + urllib.parse.quote_plus(f"site:{site} {query}")
    )
    opened = _launch_in_browser(browser, url)
    return f"Searching {site} for “{query}” in {opened}, Boss."


def _top_results(query: str, limit: int = 5) -> list[tuple[str, str]]:
    response = requests.get(
        "https://html.duckduckgo.com/html/",
        params={"q": query},
        headers={"User-Agent": "Mozilla/5.0 ULTRON/1.0"},
        timeout=15,
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    results: list[tuple[str, str]] = []
    for link in soup.select(".result__a"):
        title = link.get_text(" ", strip=True)
        raw_href = link.get("href", "")
        href = raw_href if isinstance(raw_href, str) else ""
        if href.startswith("//"):
            href = "https:" + href
        parsed = urllib.parse.urlparse(href)
        redirected = urllib.parse.parse_qs(parsed.query).get("uddg")
        if redirected:
            href = redirected[0]
        if title and href:
            results.append((title, href))
        if len(results) >= limit:
            break
    return results


def _first_youtube_video(query: str) -> tuple[str, str] | None:
    response = requests.get(
        "https://www.youtube.com/results",
        params={"search_query": query},
        headers={"User-Agent": "Mozilla/5.0 ULTRON/1.0"},
        timeout=20,
    )
    response.raise_for_status()
    video_ids = re.findall(r'"videoId":"([A-Za-z0-9_-]{11})"', response.text)
    if not video_ids:
        return None
    video_id = video_ids[0]
    title_match = re.search(
        rf'"videoId":"{re.escape(video_id)}".{{0,1200}}?"title":\{{"runs":\['
        r'\{"text":"(.*?)"\}',
        response.text,
        flags=re.DOTALL,
    )
    title = html.unescape(title_match.group(1)) if title_match else query
    return title, f"https://www.youtube.com/watch?v={video_id}&autoplay=1"


def _play(args, brain) -> str:
    if not args:
        return "Tell me which song or video to play, Boss."
    browser = brain.settings.default_browser
    values = [part.strip('"') for part in args]
    if len(values) >= 2 and values[-2].lower() == "browser":
        browser = values[-1]
        values = values[:-2]
    query = " ".join(values).strip()
    try:
        result = _first_youtube_video(query)
    except requests.RequestException:
        result = None
    if result:
        title, url = result
        opened = _launch_in_browser(browser, url)
        return f"Playing “{title}” on YouTube in {opened}, Boss."
    url = SITE_SEARCH["youtube"].format(query=urllib.parse.quote_plus(query))
    opened = _launch_in_browser(browser, url)
    return (
        f"I could not select the first video automatically, so I opened YouTube "
        f"results for “{query}” in {opened}, Boss."
    )


def _music(args, brain) -> str:
    browser = brain.settings.default_browser
    values = [part.strip('"') for part in args]
    if len(values) >= 2 and values[-2].lower() == "browser":
        browser = values[-1]
        values = values[:-2]
    query = " ".join(values).strip() or "Telugu devotional god songs"
    url = "https://open.spotify.com/search/" + urllib.parse.quote(query, safe="")
    opened = _launch_in_browser(browser, url)
    return (
        f"Opening Spotify results for “{query}” in {opened}, Boss. "
        "Spotify may require you to press Play depending on your login and autoplay settings."
    )


def _search(args, brain) -> str:
    query = " ".join(args).strip('"')
    if not query:
        return "What should I search for, Boss?"
    url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(query)
    opened = _launch_in_browser(brain.settings.default_browser, url)
    try:
        results = _top_results(query)
    except requests.RequestException:
        results = []
    brain.memory.add("web_search", query, url=url)
    if not results:
        return f"Searching the web for “{query}” in {opened}, Boss. Results are open."
    lines = [f"Top results for “{query}”:"]
    lines.extend(f"{index}. {title}\n   {link}" for index, (title, link) in enumerate(results, 1))
    lines.append(f"I also opened the complete results in {opened}, Boss.")
    return "\n".join(lines)


def _images(args, brain) -> str:
    query = " ".join(args).strip('"')
    if not query:
        return "What kind of images should I find, Boss?"
    url = (
        "https://www.google.com/search?tbm=isch&q="
        + urllib.parse.quote_plus(query)
    )
    opened = _launch_in_browser(brain.settings.default_browser, url)
    return f"Opening image results for “{query}” in {opened}, Boss."


def _research(args, brain) -> str:
    topic = " ".join(args).strip('"')
    if not topic:
        return "What topic should I explain, Boss?"
    _launch_in_browser(
        brain.settings.default_browser,
        "https://www.google.com/search?q=" + urllib.parse.quote_plus(topic),
    )
    return brain.chat(
        f"Give me accurate, useful information about: {topic}",
        extra_system=(
            "Explain the topic clearly. Distinguish established facts from uncertainty. "
            "Include practical examples and suggest what to learn next."
        ),
    )


def _email(args, brain) -> str:
    if len(args) < 3:
        return 'Usage: /email "person@example.com" "Subject" "Message", Boss.'
    recipient = _clean_email_field(args[0])
    subject = _clean_email_field(args[1])
    body = _clean_email_field(args[2])
    # A fourth AI-routed argument is sometimes a requested sender address. Outlook
    # chooses the From account itself, so do not leak that address into the body.
    if len(args) > 3:
        continuation = " ".join(_clean_email_field(part) for part in args[3:])
        if not re.fullmatch(r"(?:from\s+)?[^\s@]+@[^\s@]+\.[^\s@]+", continuation, re.I):
            body = f"{body} {continuation}".strip()
    settings = brain.settings
    parsed_recipient = parseaddr(recipient)[1]
    if "@" not in parsed_recipient or "." not in parsed_recipient.rsplit("@", 1)[-1]:
        return f"“{recipient}” does not look like a valid email address, Boss."
    if not subject:
        subject = "Message from ULTRON"
    if not body:
        return "The email body is empty, Boss."

    if settings.smtp_host and settings.smtp_user and settings.smtp_password:
        if not brain.confirm(f"Send this email to {recipient} with subject “{subject}”?"):
            return "Email cancelled, Boss."
        message = EmailMessage()
        message["From"] = settings.smtp_from or settings.smtp_user
        message["To"] = parsed_recipient
        message["Subject"] = subject
        message["Date"] = formatdate(localtime=True)
        message["Message-ID"] = make_msgid(domain=(settings.smtp_from or settings.smtp_user).split("@")[-1])
        message.set_content(body)
        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(settings.smtp_user, settings.smtp_password)
                refused = server.send_message(message)
        except smtplib.SMTPAuthenticationError:
            return (
                "The mail server rejected the login, Boss. Use an app password in "
                "SMTP_PASSWORD; a normal Gmail password will not work."
            )
        except (smtplib.SMTPException, OSError) as exc:
            return f"The mail server did not accept the email, Boss: {exc}"
        if refused:
            return f"The mail server refused the recipient, Boss: {refused}"
        brain.memory.add(
            "email_submission",
            subject,
            recipient=parsed_recipient,
            message_id=message["Message-ID"],
            status="accepted_by_smtp",
        )
        return (
            f"The SMTP server accepted the email for {parsed_recipient}, Boss. "
            f"Message ID: {message['Message-ID']}. This confirms submission, not final "
            "delivery; the recipient should also check Spam."
        )

    mailto = _mailto_url(parsed_recipient, subject, body)
    webbrowser.open(mailto)
    return (
        "SMTP is not configured, so I did not send the email, Boss. I opened a draft "
        "in your default email application. Review it and press Send there, or configure "
        "SMTP_HOST, SMTP_USER, SMTP_PASSWORD, and SMTP_FROM in .env."
    )


def _ai_email(args, brain) -> str:
    if len(args) < 2:
        return 'Usage: /ai-email "person@example.com" "instructions", Boss.'
    recipient = _clean_email_field(args[0])
    request = " ".join(_clean_email_field(part) for part in args[1:]).strip()
    parsed_recipient = parseaddr(recipient)[1]
    if "@" not in parsed_recipient or "." not in parsed_recipient.rsplit("@", 1)[-1]:
        return f"“{recipient}” does not look like a valid email address, Boss."
    generated = brain._nim_completion(
        [
            {
                "role": "system",
                "content": (
                    "Write a polished email from the user's instructions. Return exactly "
                    "two sections in plain text:\nSUBJECT: one concise subject\n"
                    "BODY:\ncomplete email body\nDo not include To, From, commentary, "
                    "quotation marks around the body, or Markdown fences."
                ),
            },
            {"role": "user", "content": request},
        ],
        max_tokens=700,
        temperature=0.3,
    ).strip()
    match = re.match(
        r"SUBJECT:\s*(.+?)\s*\nBODY:\s*\n?(.*)",
        generated,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if match:
        subject = _clean_email_field(match.group(1))
        body = _clean_email_field(match.group(2))
    else:
        subject = "Message"
        body = _clean_email_field(generated)
    return _email([parsed_recipient, subject, body], brain)


def _email_status(args, brain) -> str:
    settings = brain.settings
    configured = bool(
        settings.smtp_host
        and settings.smtp_user
        and settings.smtp_password
        and (settings.smtp_from or settings.smtp_user)
    )
    if not configured:
        return (
            "Direct email sending is not configured, Boss. No email can be sent by "
            "ULTRON until SMTP_HOST, SMTP_USER, SMTP_PASSWORD, and SMTP_FROM are set "
            "in .env. Use a provider app password."
        )
    return (
        f"Direct email is configured for {settings.smtp_user} through "
        f"{settings.smtp_host}:{settings.smtp_port}, Boss. Run /email-test to verify "
        "the login without sending a message."
    )


def _email_test(args, brain) -> str:
    settings = brain.settings
    if not (settings.smtp_host and settings.smtp_user and settings.smtp_password):
        return _email_status([], brain)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.smtp_user, settings.smtp_password)
    except smtplib.SMTPAuthenticationError:
        return (
            "SMTP connection worked, but authentication failed, Boss. Generate and use "
            "an app password for your email provider."
        )
    except (smtplib.SMTPException, OSError) as exc:
        return f"SMTP diagnostic failed, Boss: {exc}"
    return "SMTP connection and authentication succeeded. No email was sent, Boss."


def register(registry) -> None:
    registry.register("website", _website, "<url> open a website")
    registry.register("browser", _browser, "[browser] [site or query] use an installed browser")
    registry.register(
        "browser-search",
        _browser_search,
        "<browser> <site> <query> search a site in a chosen browser",
    )
    registry.register("site-search", _site_search, "<site> <query> search inside a website")
    registry.register("play", _play, "<song or video> [browser <name>] play on YouTube")
    registry.register("music", _music, "[song] [browser <name>] open Spotify music")
    registry.register("search", _search, "<query> show top results and open Google")
    registry.register("images", _images, "<query> search Google Images")
    registry.register("research", _research, "<topic> search and explain a topic")
    registry.register("email", _email, "<to> <subject> <body> draft or send email")
    registry.register("ai-email", _ai_email, "<to> <instructions> generate a clean email draft")
    registry.register("email-status", _email_status, "show direct-email configuration")
    registry.register("email-test", _email_test, "test SMTP login without sending")
