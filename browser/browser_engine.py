from pathlib import Path
from playwright.sync_api import sync_playwright


class BrowserEngine:
    """Local browser tools powered by Playwright/Chromium."""

    def __init__(self, workspace: str):
        self.workspace = Path(workspace).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.screenshots = self.workspace / "browser_screenshots"
        self.screenshots.mkdir(parents=True, exist_ok=True)

    def open_page(self, url: str, take_screenshot: bool = True) -> str:
        if not url.startswith(("http://", "https://", "file:///")):
            raise ValueError("URL must start with http://, https://, or file:///")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(1000)

            title = page.title()
            text = page.locator("body").inner_text(timeout=5000)
            result = f"URL: {page.url}\nTITLE: {title}\nVISIBLE_TEXT:\n{text[:12000]}"

            if take_screenshot:
                shot = self.screenshots / "latest.png"
                page.screenshot(path=str(shot), full_page=True)
                result += f"\nSCREENSHOT: {shot}"

            browser.close()
            return result
