import os
from pathlib import Path

from instagram_home import instagram_home_session

def get_user_followers(page, username: str):
    page.goto(f"https://www.instagram.com/{username}/", wait_until="domcontentloaded")
    followers = page.get_by_text("followers", exact=False)
    followers.wait_for(state="visible", timeout=60_000)

    page.get_by_role("link", name="followers", exact=False).click()
    page.wait_for_selector("div[role='dialog']", timeout=60_000)

    followers_selector = "div[role='dialog'] a[role='link'][href^='/']"

    def extract_usernames():
        hrefs = page.eval_on_selector_all(
            followers_selector, "els => els.map(el => el.getAttribute('href'))"
        ) or []
        usernames = []
        seen = set()
        for href in hrefs:
            if not href:
                continue
            candidate = href.strip("/").split("/", maxsplit=1)[0]
            if candidate and candidate not in seen and "/" not in candidate:
                seen.add(candidate)
                usernames.append(candidate)
        return usernames

    scroll_container = None
    possible_scroll_selectors = [
        "div[role='dialog'] div[style*='overflow: auto']",
        "div[role='dialog'] div[style*='overflow:auto']",
        "div[role='dialog'] div[style*='overflow: hidden auto']",
        "div[role='dialog'] div[style*='overflow: scroll']",
        "div[role='dialog'] ._aano",
        "div[role='dialog'] ul",
        "div[role='dialog']",
    ]
    for selector in possible_scroll_selectors:
        locator = page.locator(selector)
        if locator.count() > 0:
            scroll_container = locator.first
            break

    followers_usernames = extract_usernames()
    last_count = len(followers_usernames)
    stable_rounds = 0
    max_rounds = 60

    for _ in range(max_rounds):
        if scroll_container is not None:
            try:
                scroll_container.evaluate("el => el.scrollTo(0, el.scrollHeight)")
            except Exception:
                scroll_container = None
        else:
            page.mouse.wheel(0, 2000)

        page.wait_for_timeout(1_000)

        followers_usernames = extract_usernames()
        current_count = len(followers_usernames)
        if current_count == last_count:
            stable_rounds += 1
            if stable_rounds >= 3:
                break
        else:
            stable_rounds = 0
            last_count = current_count

    output_path = Path(f"data/people/{username}/followers.txt")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = "\n".join(followers_usernames)
    if followers_usernames:
        serialized += "\n"
    output_path.write_text(serialized, encoding="utf-8")
    return followers_usernames



if __name__ == "__main__":
    with instagram_home_session(headless=False, slow_mo=200) as page:
        username = os.getenv("USERNAME_TO_START")
        get_user_followers(page, username)
