from dataclasses import dataclass
from typing import Optional


@dataclass
class BrowserConfig:
    headless: bool = False
    browser: str = "chromium"


class BrowserController:
    """Playwright browser adapter.

    Playwright is imported lazily so the rest of the agent can start even
    before the browser runtime is installed on the Windows host.
    """

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
        self._page = self._browser.new_page()
        return self

    def open(self, url: str):
        self._require_started()
        self._page.goto(url, wait_until="domcontentloaded")
        return {"url": self._page.url, "title": self._page.title()}

    def screenshot(self, path: str):
        self._require_started()
        self._page.screenshot(path=path, full_page=True)
        return {"path": path}

    def text(self, selector: str = "body"):
        self._require_started()
        return self._page.locator(selector).inner_text()

    def click(self, selector: str):
        self._require_started()
        self._page.locator(selector).click()
        return {"clicked": selector}

    def fill(self, selector: str, value: str):
        self._require_started()
        self._page.locator(selector).fill(value)
        return {"filled": selector}

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
