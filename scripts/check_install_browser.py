"""Check the real Khula installer with mobile Chromium and a strict CSP.

Run against public HTTPS only, in disposable Playwright browser contexts.
Never authenticates to Khula or requests member/financial records.
"""
import argparse
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

INSTALL_PATH = "/app/static/install.html"

DEVICES = (
    (
        "Android",
        "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36",
        "#android-help",
    ),
    (
        "iPhone",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1",
        "#ios-help",
    ),
)


def check(base_url):
    parsed = urlsplit(base_url)
    if parsed.scheme != "https" or parsed.username or parsed.password:
        raise ValueError("Use the official HTTPS Khula origin; no embedded credentials.")
    origin = parsed.scheme + "://" + parsed.netloc
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True, args=["--no-sandbox"]
        )
        try:
            for name, ua, selector in DEVICES:
                context = browser.new_context(
                    viewport={"width": 390, "height": 844},
                    device_scale_factor=2, user_agent=ua,
                    is_mobile=True, has_touch=True,
                )
                page = context.new_page()
                errors = []
                page.on(
                    "console",
                    lambda msg: errors.append(msg.text)
                    if msg.type == "error" and (
                        "content security policy" in msg.text.lower()
                        or "refused to execute" in msg.text.lower()
                    ) else None,
                )
                page.goto(
                    origin + INSTALL_PATH, wait_until="domcontentloaded",
                    timeout=45000,
                )
                page.locator(selector).wait_for(
                    state="visible", timeout=15000
                )
                assert page.locator("#install-button").count() == 1
                assert page.locator("body").get_by_text(
                    "khula-collective-production.up.railway.app"
                ).count() > 0, "Official domain not displayed."
                assert page.locator(
                    "link[rel='manifest']"
                ).get_attribute("href") == "/app/static/khula-manifest.json"
                assert not errors, f"{name} installer CSP console errors: {errors}"
                registrations = page.evaluate(
                    "navigator.serviceWorker ? "
                    "navigator.serviceWorker.getRegistrations().then(x => x.length) : 0"
                )
                assert registrations == 0, (
                    f"An unreviewed service worker was active on {name}"
                )
                assert page.url.startswith(origin + INSTALL_PATH)
                print(
                    f"PASS {name}: strict CSP runs approved install help, "
                    "no service worker and same official HTTPS origin",
                    flush=True,
                )
                context.close()
        finally:
            browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--url",
        default="https://khula-collective-production.up.railway.app",
    )
    args = parser.parse_args()
    check(args.url)
