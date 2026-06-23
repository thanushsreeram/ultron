from __future__ import annotations

import re
import threading
import time
from pathlib import Path
from typing import Any

from skills.apps import resolve_windows_app
from skills.clipboard_tools import type_text


LEARNING_PORTAL = "https://learning.ccbp.in/"


def _clean_code(value: str) -> str:
    value = value.strip()
    fenced = re.search(r"```(?:[a-zA-Z0-9_+-]+)?\s*(.*?)```", value, re.DOTALL)
    if fenced:
        value = fenced.group(1).strip()
    return value.replace("\r\n", "\n").replace("\r", "\n")


class CodingPracticeCoach:
    """Visible, user-supervised browser helper for one coding problem at a time."""

    def __init__(self) -> None:
        self.driver: Any | None = None
        self.question_text = ""
        self.draft_code = ""
        self.feedback_text = ""
        self._lock = threading.RLock()
        self._stopping = threading.Event()

    def active(self) -> bool:
        return self.driver is not None

    def _build_driver(self, brain):
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options as ChromeOptions
            from selenium.webdriver.edge.options import Options as EdgeOptions
        except ImportError as exc:
            raise RuntimeError(
                "Selenium is not installed. Run: pip install -r requirements.txt"
            ) from exc

        browser = brain.settings.default_browser.strip().lower()
        profile = brain.settings.storage_dir / "coding-coach-browser-profile"
        profile.mkdir(parents=True, exist_ok=True)

        if browser in {"edge", "microsoft edge"}:
            options = EdgeOptions()
            options.add_argument(f"--user-data-dir={profile}")
            options.add_argument("--start-maximized")
            return webdriver.Edge(options=options)

        options = ChromeOptions()
        options.add_argument(f"--user-data-dir={profile}")
        options.add_argument("--start-maximized")
        binary = resolve_windows_app(browser)
        if binary and Path(binary).is_file():
            options.binary_location = binary
        try:
            return webdriver.Chrome(options=options)
        except Exception:
            # Comet and other Chromium builds are not always compatible with the
            # installed ChromeDriver. Fall back to standard Chrome visibly.
            fallback_options = ChromeOptions()
            fallback_options.add_argument(f"--user-data-dir={profile}")
            fallback_options.add_argument("--start-maximized")
            fallback = resolve_windows_app("chrome")
            if fallback and Path(fallback).is_file():
                fallback_options.binary_location = fallback
            return webdriver.Chrome(options=fallback_options)

    def start(self, brain) -> str:
        with self._lock:
            self._stopping.clear()
            if self.driver is None:
                self.driver = self._build_driver(brain)
            self.driver.get(LEARNING_PORTAL)
            return (
                "Learning Portal is open in the supervised coding browser, Boss. "
                "Log in personally if needed. Then say “open first coding practice” "
                "or run /coding-practice open-first."
            )

    def stop(self) -> str:
        with self._lock:
            self._stopping.set()
            driver, self.driver = self.driver, None
            self.question_text = ""
            self.draft_code = ""
            self.feedback_text = ""
            if driver is not None:
                try:
                    driver.quit()
                except Exception:
                    pass
            return "Coding Coach stopped and its controlled browser was closed, Boss."

    def _require_driver(self):
        if self.driver is None:
            raise RuntimeError(
                "Coding Coach is not active. Run /coding-practice start first."
            )
        return self.driver

    @staticmethod
    def _visible(elements) -> list[Any]:
        visible = []
        for element in elements:
            try:
                if element.is_displayed():
                    visible.append(element)
            except Exception:
                continue
        return visible

    def _click_text(self, labels: list[str], *, exact: bool = False) -> str | None:
        driver = self._require_driver()
        from selenium.webdriver.common.by import By

        for label in labels:
            safe = label.replace('"', '\\"')
            if exact:
                xpath = (
                    "//*[self::button or self::a or @role='button' or @role='tab']"
                    f"[normalize-space()=\"{safe}\"]"
                )
            else:
                xpath = (
                    "//*[self::button or self::a or @role='button' or @role='tab']"
                    f"[contains(translate(normalize-space(.), "
                    "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), "
                    f"\"{safe.lower()}\")]"
                )
            for element in self._visible(driver.find_elements(By.XPATH, xpath)):
                try:
                    driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center'});", element
                    )
                    element.click()
                    return label
                except Exception:
                    try:
                        driver.execute_script("arguments[0].click();", element)
                        return label
                    except Exception:
                        continue
        return None

    def open_first(self) -> str:
        self._require_driver()
        steps = [
            (["Question Bank", "Questions"], False),
            (["Not Attempted", "Unattempted"], False),
        ]
        completed = []
        for labels, exact in steps:
            clicked = self._click_text(labels, exact=exact)
            if not clicked:
                return (
                    f"I completed {', '.join(completed) or 'no navigation steps'}, "
                    f"but could not find “{labels[0]}”, Boss. Open that section "
                    "manually, then run /coding-practice inspect."
                )
            completed.append(clicked)
            time.sleep(1.5)

        driver = self._require_driver()
        from selenium.webdriver.common.by import By

        candidates = driver.find_elements(
            By.XPATH,
            "//*[self::a or self::button or @role='button']"
            "[contains(translate(normalize-space(.), "
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'coding') "
            "or contains(translate(normalize-space(.), "
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'practice')]",
        )
        visible = self._visible(candidates)
        if not visible:
            return (
                "Question Bank and Not Attempted are open, but I could not identify "
                "the first coding-practice card. Open the first one manually, Boss."
            )
        target = visible[0]
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", target)
        driver.execute_script("arguments[0].click();", target)
        time.sleep(1.5)
        return (
            "Opened the first visible not-attempted coding practice, Boss. "
            "Run /coding-practice inspect so I can explain its requirements."
        )

    def _page_text(self) -> str:
        driver = self._require_driver()
        from selenium.webdriver.common.by import By

        selectors = [
            "[data-testid*='question']",
            "[class*='question']",
            "[class*='problem']",
            "main",
            "body",
        ]
        for selector in selectors:
            for element in self._visible(driver.find_elements(By.CSS_SELECTOR, selector)):
                text = element.text.strip()
                if len(text) >= 80:
                    return text[:24000]
        raise RuntimeError("I could not read a coding question from the current page.")

    def inspect(self, brain) -> str:
        self.question_text = self._page_text()
        explanation = brain._nim_completion(
            [
                {
                    "role": "system",
                    "content": (
                        "Act as a coding tutor. Extract only the programming problem "
                        "requirements from the supplied portal text. Explain inputs, "
                        "outputs, constraints, examples, and likely edge cases. Do not "
                        "give final solution code. Ignore navigation, profile, scores, "
                        "and unrelated page text."
                    ),
                },
                {"role": "user", "content": self.question_text},
            ],
            max_tokens=900,
            temperature=0.1,
        ).strip()
        return (
            "I read the current problem, Boss.\n"
            f"{explanation}\n\n"
            "When you understand it, run /coding-practice draft python."
        )

    def draft(self, brain, language: str = "python") -> str:
        if not self.question_text:
            self.question_text = self._page_text()
        self.draft_code = _clean_code(
            brain._nim_completion(
                [
                    {
                        "role": "system",
                        "content": (
                            f"You are a careful coding tutor. Draft a correct {language} "
                            "solution for the programming problem. Return only runnable "
                            "source code, without Markdown fences or explanation. Match "
                            "the exact input/output format. Do not claim it was submitted "
                            "or passed."
                        ),
                    },
                    {"role": "user", "content": self.question_text},
                ],
                max_tokens=1800,
                temperature=0.1,
            )
        )
        if not self.draft_code:
            raise RuntimeError("The AI returned an empty code draft.")
        path = brain.settings.workspace / "coding-practice-draft.txt"
        path.write_text(self.draft_code, encoding="utf-8")
        return (
            f"Drafted {language} code and saved it to {path}, Boss. Review it first. "
            "Run /coding-practice show to display it, or /coding-practice paste to "
            "place it into the focused portal editor after confirmation."
        )

    def show(self) -> str:
        if not self.draft_code:
            return "No coding-practice draft exists yet, Boss."
        return "Current supervised draft:\n\n" + self.draft_code

    def _editor(self):
        driver = self._require_driver()
        from selenium.webdriver.common.by import By

        selectors = [
            ".monaco-editor textarea",
            ".CodeMirror textarea",
            "textarea",
            "[contenteditable='true']",
        ]
        for selector in selectors:
            visible = self._visible(driver.find_elements(By.CSS_SELECTOR, selector))
            if visible:
                return visible[0]
        raise RuntimeError("I could not find a visible code editor on this page.")

    def paste(self, brain) -> str:
        if not self.draft_code:
            return "Create a draft first with /coding-practice draft python, Boss."
        if not brain.confirm(
            "Replace the current portal editor contents with the supervised draft?"
        ):
            return "Coding-practice paste cancelled, Boss."
        editor = self._editor()
        driver = self._require_driver()
        from selenium.webdriver.common.action_chains import ActionChains
        from selenium.webdriver.common.keys import Keys

        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", editor)
        editor.click()
        ActionChains(driver).key_down(Keys.CONTROL).send_keys("a").key_up(
            Keys.CONTROL
        ).send_keys(Keys.BACKSPACE).perform()
        type_text(self.draft_code, interval=0.0005)
        return (
            "Force-pasted the supervised draft into the coding editor, Boss. "
            "Review it on screen, then run /coding-practice run."
        )

    def run_tests(self) -> str:
        clicked = self._click_text(
            ["Run Code", "Run Tests", "Run", "Check"], exact=False
        )
        if not clicked:
            return (
                "I could not find a Run or Test button, Boss. Click it manually, "
                "then run /coding-practice feedback."
            )
        time.sleep(2)
        return (
            f"Clicked {clicked}, Boss. After the results finish loading, run "
            "/coding-practice feedback."
        )

    def feedback(self, brain) -> str:
        page = self._page_text()
        lines = [
            line.strip()
            for line in page.splitlines()
            if re.search(
                r"\b(test|passed|failed|error|expected|actual|output|runtime)\b",
                line,
                flags=re.IGNORECASE,
            )
        ]
        self.feedback_text = "\n".join(lines[-80:]) or page[-8000:]
        summary = brain._nim_completion(
            [
                {
                    "role": "system",
                    "content": (
                        "Summarize the visible coding test results. State how many tests "
                        "passed or failed when shown, identify errors and likely causes, "
                        "and suggest a correction. Do not claim success unless the text "
                        "explicitly confirms all tests passed."
                    ),
                },
                {"role": "user", "content": self.feedback_text},
            ],
            max_tokens=700,
            temperature=0.1,
        ).strip()
        return (
            summary
            + "\n\nUse /coding-practice revise to create a corrected draft, "
            "or /coding-practice submit if you verified that all tests passed."
        )

    def revise(self, brain, language: str = "python") -> str:
        if not self.draft_code:
            return "There is no draft to revise, Boss."
        if not self.feedback_text:
            return "Run /coding-practice feedback before requesting a revision, Boss."
        self.draft_code = _clean_code(
            brain._nim_completion(
                [
                    {
                        "role": "system",
                        "content": (
                            f"Correct the supplied {language} solution using the test "
                            "feedback and original problem. Return only complete runnable "
                            "code without Markdown. Preserve the required input/output "
                            "format. Do not claim that tests passed."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"PROBLEM:\n{self.question_text}\n\n"
                            f"CURRENT CODE:\n{self.draft_code}\n\n"
                            f"TEST FEEDBACK:\n{self.feedback_text}"
                        ),
                    },
                ],
                max_tokens=1800,
                temperature=0.1,
            )
        )
        path = brain.settings.workspace / "coding-practice-draft.txt"
        path.write_text(self.draft_code, encoding="utf-8")
        return (
            f"Created a revised draft and saved it to {path}, Boss. Review it, "
            "then run /coding-practice paste when ready."
        )

    def submit(self, brain) -> str:
        if not brain.confirm(
            "Submit the current coding answer to the Learning Portal? "
            "This records an academic submission."
        ):
            return "Coding-practice submission cancelled, Boss."
        clicked = self._click_text(["Submit Code", "Submit"], exact=False)
        if not clicked:
            return (
                "I could not find a Submit button, so nothing was submitted, Boss."
            )
        time.sleep(2)
        return (
            f"Clicked {clicked}, Boss. Check the portal’s final result yourself; "
            "ULTRON does not assume acceptance. Run /coding-practice feedback."
        )

    def next_problem(self) -> str:
        clicked = self._click_text(
            ["Next Question", "Next Practice", "Next"], exact=False
        )
        if not clicked:
            return (
                "I could not find a Next button, Boss. Return to Not Attempted "
                "manually or run /coding-practice open-first."
            )
        self.question_text = ""
        self.draft_code = ""
        self.feedback_text = ""
        time.sleep(1.5)
        return (
            f"Clicked {clicked}, Boss. Run /coding-practice inspect for the new problem."
        )


COACH = CodingPracticeCoach()


def _coding_practice(args, brain) -> str:
    action = args[0].strip('"').lower() if args else "status"
    values = [value.strip('"') for value in args[1:] if value.strip('"')]
    if action in {"start", "open"}:
        return COACH.start(brain)
    if action in {"open-first", "first"}:
        return COACH.open_first()
    if action in {"inspect", "read", "explain"}:
        return COACH.inspect(brain)
    if action in {"draft", "solve"}:
        return COACH.draft(brain, values[0] if values else "python")
    if action in {"show", "code"}:
        return COACH.show()
    if action in {"paste", "force-paste"}:
        return COACH.paste(brain)
    if action in {"run", "test", "tests"}:
        return COACH.run_tests()
    if action in {"feedback", "result", "results"}:
        return COACH.feedback(brain)
    if action in {"revise", "fix", "debug"}:
        return COACH.revise(brain, values[0] if values else "python")
    if action == "submit":
        return COACH.submit(brain)
    if action in {"next", "continue"}:
        return COACH.next_problem()
    if action in {"stop", "close", "exit"}:
        return COACH.stop()
    if action == "status":
        return (
            "Coding Coach is active, Boss."
            if COACH.active()
            else "Coding Coach is not active, Boss."
        )
    return (
        "Usage: /coding-practice "
        "<start|open-first|inspect|draft|show|paste|run|feedback|revise|"
        "submit|next|stop>, Boss."
    )


def register(registry) -> None:
    registry.register(
        "coding-practice",
        _coding_practice,
        "<action> supervised Learning Portal coding coach",
    )
