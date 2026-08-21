# Browser Engine

The browser layer uses Playwright and is intentionally isolated from the agent core.

Capabilities currently implemented:

- start Chromium visibly or headless;
- open URLs;
- read page text;
- click elements;
- fill form fields;
- capture full-page screenshots;
- clean shutdown.

The Windows setup will install Playwright separately. No browser credentials or
secrets belong in the repository.
