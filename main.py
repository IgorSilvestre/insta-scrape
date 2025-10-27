from datetime import datetime
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from module.instagram_home import instagram_home_session


def sanitize_username(username: str) -> str:
    sanitized = "".join(ch if ch.isalnum() or ch in {"_", "-", "."} else "_" for ch in username)
    sanitized = sanitized.strip("_")
    return sanitized or "unknown_user"


def save_article_images(page, base_dir: Path = Path("data/people")):
    try:
        page.wait_for_selector("article", timeout=20000)
    except PlaywrightTimeoutError:
        print("No articles found to process.")
        return
    articles = page.locator("article")
    count = articles.count()
    print(f"Found {count} articles on the page.")

    for index in range(count):
        article = articles.nth(index)
        try:
            username_locator = article.locator('a[role="link"] span').first
            username = username_locator.inner_text(timeout=5000).strip()
        except PlaywrightTimeoutError:
            print(f"[{index}] Skipping article without username.")
            continue

        if not username:
            print(f"[{index}] Username empty, skipping.")
            continue

        media_candidates = article.locator("div._aagw")
        if media_candidates.count() > 0:
            image_locator = media_candidates.first
        else:
            image_locator = article.locator("img").first
        try:
            image_locator.wait_for(timeout=5000)
        except PlaywrightTimeoutError:
            print(f"[{index}] No image found for {username}, skipping.")
            continue

        safe_username = sanitize_username(username)
        image_dir = base_dir / safe_username / "images"
        image_dir.mkdir(parents=True, exist_ok=True)

        filename = datetime.utcnow().strftime("%Y%m%d%H%M%S%f") + ".png"
        destination = image_dir / filename

        try:
            image_locator.screenshot(path=str(destination), timeout=5000)
            print(f"[{index}] Saved image for {username} -> {destination}")
        except PlaywrightTimeoutError:
            print(f"[{index}] Failed to capture screenshot for {username}.")


def main():
    with instagram_home_session(headless=False, slow_mo=200) as page:
        save_article_images(page)


if __name__ == "__main__":
    main()
