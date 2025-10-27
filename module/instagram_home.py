import os
import re
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright

SELECTOR_TEMPLATES = [
    'button:has-text("{label}")',
    '[role="button"]:has-text("{label}")',
    (
        "xpath=//*[("
        "@role='button' or self::button or self::div or self::span"
        ")"
        " and contains(translate(normalize-space(.), "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), "
        "'{label_lower}')]"
    ),
]


def try_click_selector(page, selector, timeout=5000):
    try:
        locator = page.locator(selector).first
        locator.click(timeout=timeout)
        page.wait_for_timeout(400)
        return True
    except PlaywrightTimeoutError:
        return False


def dismiss_not_now_prompts(page, attempts=3):
    label_variants = ["Not now", "Not Now", "Not now!"]
    for _ in range(attempts):
        clicked = False
        for label in label_variants:
            for template in SELECTOR_TEMPLATES:
                selector = template.format(label=label, label_lower=label.lower())
                if try_click_selector(page, selector):
                    clicked = True
                    break
            if clicked:
                break
        if not clicked:
            break


@lru_cache(maxsize=1)
def load_credentials(env_path: Path | None = None):
    username = os.getenv("INSTAGRAM_USERNAME")
    password = os.getenv("PASSWORD")

    if username and password:
        return username, password

    path = env_path or Path(__file__).resolve().parents[1] / ".env"
    if path.exists():
        with path.open("r", encoding="utf-8") as env_file:
            for raw_line in env_file:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key == "USERNAME" and not username:
                    username = value
                elif key == "PASSWORD" and not password:
                    password = value

    missing = []
    if not username:
        missing.append("USERNAME")
    if not password:
        missing.append("PASSWORD")
    if missing:
        missing_str = ", ".join(missing)
        raise RuntimeError(
            f"Missing credentials: {missing_str}. Set them via environment variables or the .env file."
        )

    return username, password


@contextmanager
def instagram_home_session(
    headless=False,
    slow_mo=200,
    username=None,
    password=None,
):
    env_username, env_password = load_credentials()
    if username is None:
        username = env_username
    if password is None:
        password = env_password

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless, slow_mo=slow_mo)
        page = browser.new_page()
        page.goto("https://www.instagram.com/accounts/login/", wait_until="domcontentloaded")
        page.wait_for_selector('input[name="username"]', timeout=5000)

        page.fill('input[name="username"]', username)
        page.fill('input[name="password"]', password)
        page.click('button[type="submit"]')

        home_loaded = False
        home_url_pattern = re.compile(r"https://www\.instagram\.com/.*")

        for _ in range(3):
            dismiss_not_now_prompts(page)
            if home_url_pattern.match(page.url):
                home_loaded = True
                break
            try:
                page.wait_for_url(home_url_pattern, timeout=5000)
                home_loaded = True
                break
            except PlaywrightTimeoutError:
                continue

        if not home_loaded:
            print("Login likely failed; home page not reached.")

        if home_loaded:
            print("Reached Instagram home page.")
            dismiss_not_now_prompts(page)
            page.wait_for_timeout(1000)
        else:
            dismiss_not_now_prompts(page)

        try:
            yield page
        finally:
            page.wait_for_timeout(5000)
            browser.close()
