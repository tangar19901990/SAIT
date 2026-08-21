from dataclasses import dataclass
from typing import Optional


@dataclass
class BrowserConfig:
    headless: bool = False
    browser: str = "chromium"


class BrowserController:
    """Local Playwright browser controller used by the SAIT agent."""

    def __init__(self, config: Optional[BrowserConfig] = None):
        self.config = config or BrowserConfig()
        self._playwright = None
        self._browser = None
        self._page = None

    def start(self):
        from playwright.sync_api import sync_playwright
        self._playwright = sync_playwright().start()
        browser_factory = getattr(self._playwright, self.config.browser)
        self._browser = browser_factory.launch(headless=self.config.headless)
        self._page = self._browser.new_page(viewport={"width": 1440, "height": 900})
        return self

    def open(self, url: str):
        self._require_started()
        self._page.goto(url, wait_until="domcontentloaded")
        return {"url": self._page.url, "title": self._page.title()}

    def text(self, selector: str = "body"):
        self._require_started()
        return self._page.locator(selector).inner_text()

    def html(self, selector: str = "html"):
        self._require_started()
        return self._page.locator(selector).evaluate("el => el.outerHTML")

    def click(self, selector: str):
        self._require_started()
        self._page.locator(selector).click()
        return {"clicked": selector}

    def fill(self, selector: str, value: str):
        self._require_started()
        self._page.locator(selector).fill(value)
        return {"filled": selector}

    def press(self, selector: str, key: str):
        self._require_started()
        self._page.locator(selector).press(key)
        return {"pressed": key, "selector": selector}

    def screenshot(self, path: str):
        self._require_started()
        from pathlib import Path
        target = Path(path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        self._page.screenshot(path=str(target), full_page=True)
        return {"path": str(target)}

    def current(self):
        self._require_started()
        return {"url": self._page.url, "title": self._page.title()}

    def stop(self):
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
        self._browser = None
        self._page = None
        self._playwright = None

    def _require_started(self):
        if self._page is None:
            raise RuntimeError("Browser is not started. Call start() first.")
