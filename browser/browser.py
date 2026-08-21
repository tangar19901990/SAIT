from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse


@dataclass
class BrowserConfig:
    headless: bool = False
    browser: str = "chromium"
    navigation_timeout_ms: int = 30000
    action_timeout_ms: int = 10000


class BrowserController:
    """Local Playwright browser controller used by the SAIT agent."""

    def __init__(self, config: Optional[BrowserConfig] = None):
        self.config = config or BrowserConfig()
        self._playwright = None
        self._browser = None
        self._page = None

    def start(self):
        if self._page is not None:
            return self
        from playwright.sync_api import sync_playwright
        self._playwright = sync_playwright().start()
        browser_factory = getattr(self._playwright, self.config.browser, None)
        if browser_factory is None:
            self.stop()
            raise ValueError(f"Unsupported browser: {self.config.browser}")
        try:
            self._browser = browser_factory.launch(headless=self.config.headless)
            self._page = self._browser.new_page(viewport={"width": 1440, "height": 900})
            self._page.set_default_timeout(self.config.action_timeout_ms)
            self._page.set_default_navigation_timeout(self.config.navigation_timeout_ms)
            return self
        except Exception:
            self.stop()
            raise

    def open(self, url: str):
        self._require_started()
        parsed = urlparse(url.strip())
        if parsed.scheme not in {"http", "https", "file"}:
            raise ValueError("URL must start with http://, https://, or file:///")
        self._page.goto(url, wait_until="domcontentloaded")
        return self.current()

    def text(self, selector: str = "body"):
        self._require_started()
        return self._page.locator(selector).inner_text()

    def html(self, selector: str = "html"):
        self._require_started()
        return self._page.locator(selector).evaluate("el => el.outerHTML")

    def click(self, selector: str):
        self._require_started()
        self._page.locator(selector).click()
        self._settle()
        return {"clicked": selector, **self.current()}

    def fill(self, selector: str, value: str):
        self._require_started()
        self._page.locator(selector).fill(value)
        return {"filled": selector}

    def press(self, selector: str, key: str):
        self._require_started()
        self._page.locator(selector).press(key)
        self._settle()
        return {"pressed": key, "selector": selector, **self.current()}

    def screenshot(self, path: str):
        self._require_started()
        target = Path(path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        self._page.screenshot(path=str(target), full_page=True)
        return {"path": str(target), **self.current()}

    def current(self):
        self._require_started()
        return {"url": self._page.url, "title": self._page.title()}

    def stop(self):
        try:
            if self._page:
                self._page.close()
        finally:
            try:
                if self._browser:
                    self._browser.close()
            finally:
                if self._playwright:
                    self._playwright.stop()
        self._browser = None
        self._page = None
        self._playwright = None

    def _settle(self):
        try:
            self._page.wait_for_load_state("domcontentloaded", timeout=1500)
        except Exception:
            pass

    def _require_started(self):
        if self._page is None:
            raise RuntimeError("Browser is not started. Call start() first.")
