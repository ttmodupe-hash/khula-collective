"""Browser acceptance for the actual Khula public sign-in layout.

Never accesses production credentials, member identities or financial data.
Use with a temporary, empty SQLite DB and the real Streamlit app. Tests both
desktop and narrow mobile viewport dimensions; saves screenshots for review.
"""
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright


def check(url, screenshot_dir):
    shots = Path(screenshot_dir)
    shots.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        try:
            for name, width, height in [
                ("desktop", 1440, 900),
                ("mobile", 390, 844),
            ]:
                page = browser.new_page(viewport={"width": width, "height": height},
                                        device_scale_factor=1)
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                username = page.get_by_role("textbox", name="Username or email", exact=True)
                username.wait_for(state="visible", timeout=45000)
                page.get_by_text("Welcome back", exact=True).wait_for(
                    state="visible", timeout=45000)
                page.get_by_text("New to Khula? Apply for membership").wait_for(
                    state="visible", timeout=45000)
                page.get_by_role("link", name="Add Khula to your phone").wait_for(
                    state="visible", timeout=45000)

                # This exact stray output was visible at the top of the
                # screenshot before load_css() was called correctly.
                stray = page.get_by_text("None", exact=True)
                assert stray.count() == 0, (
                    f"Raw None text rendered on {name} public login"
                )

                logo = page.locator(".khula-auth-hero img")
                assert logo.count() == 1, f"Missing Khula app logo on {name}"
                icon_ok = logo.evaluate(
                    "(img) => img.complete && img.naturalWidth >= 192"
                )
                assert icon_ok, f"Khula home-screen icon did not load on {name}"

                input_box = username.bounding_box()
                assert input_box is not None, f"Missing username box for {name}"
                center = input_box["x"] + input_box["width"] / 2
                assert abs(center - width / 2) <= max(55, width * .10), (
                    f"Login username box is not centered for {name}: {input_box}"
                )
                assert input_box["width"] > (width * .35), (
                    f"Login form is too narrow on {name}: {input_box}"
                )
                if name == "desktop":
                    assert input_box["width"] < 760, (
                        "Login input incorrectly spans most of the desktop screen"
                    )
                else:
                    assert input_box["width"] < width - 15, (
                        "Mobile username input overflows its viewport"
                    )
                overflow = page.evaluate(
                    "Math.max(document.documentElement.scrollWidth, "
                    "document.body.scrollWidth) - window.innerWidth"
                )
                assert overflow <= 24, (
                    f"Horizontal overflow on {name}: {overflow} CSS pixels"
                )
                body_text = page.locator("body").inner_text()
                assert "The club is finalising" in body_text or (
                    "New requests are temporarily closed" in body_text
                ), "Temporary registration hold is not explained"
                assert "Submit membership request" not in body_text, (
                    "Real registration should remain closed with missing approvals"
                )
                page.screenshot(path=str(shots / f"khula-login-{name}.png"),
                                full_page=True, animations="disabled")
                print(f"PASS {name}: centered {input_box['width']:.0f}px login "
                      f"on {width}px viewport; overflow={overflow}")
                page.close()
        finally:
            browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8501")
    parser.add_argument("--screenshots", default="visual-tests")
    args = parser.parse_args()
    check(args.url, args.screenshots)
