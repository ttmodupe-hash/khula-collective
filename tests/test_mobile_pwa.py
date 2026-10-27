"""Installable Khula PWA: manifest, build-time head integration and branded icons.

No service worker, offline member data or browser-side bank ledger is allowed.
"""
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scripts.generate_pwa_icons import generate_icons
from scripts.patch_streamlit_pwa import inject_head, patch_index, MARKER
from scripts.harden_install_page import (
    render_secure_installer, validate_hardened_installer, build_install_page,
    SCRIPT_PLACEHOLDER, STYLE_PLACEHOLDER,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "static" / "khula-manifest.json"
INSTALLER = ROOT / "static" / "install.html"


class KhulaMobilePwaTests(unittest.TestCase):
    def test_manifest_standalone_https_ready_and_correct_identity(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "Khula Collective")
        self.assertEqual(manifest["short_name"], "Khula")
        self.assertEqual(manifest["start_url"], "/")
        self.assertEqual(manifest["id"], "/")
        self.assertEqual(manifest["scope"], "/")
        self.assertEqual(manifest["display"], "standalone")
        self.assertEqual(manifest["prefer_related_applications"], False)
        self.assertEqual(manifest["lang"], "en-ZA")
        icons = manifest["icons"]
        declared = {
            (item["sizes"], item["type"], item["purpose"]) for item in icons
        }
        self.assertIn(("192x192", "image/png", "any"), declared)
        self.assertIn(("512x512", "image/png", "any"), declared)
        self.assertIn(("512x512", "image/png", "maskable"), declared)
        for icon in icons:
            self.assertTrue(icon["src"].startswith("/app/static/khula-icon-"))
            self.assertTrue(icon["src"].endswith(".png"))
            self.assertNotIn("http", icon["src"])
        self.assertNotIn("bank account", json.dumps(manifest).lower())

    def test_icon_generator_creates_valid_raster_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            files = generate_icons(tmp)
            self.assertEqual(len(files), 3)
            for p in files:
                self.assertTrue(p.is_file())
                self.assertEqual(p.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
                with Image.open(p) as image:
                    image.verify()
                with Image.open(p) as image:
                    self.assertEqual(image.mode, "RGBA")
                    self.assertEqual(image.width, image.height)
                    expected = 192 if "-192" in p.name else 512
                    self.assertEqual(image.size, (expected, expected))
            with Image.open(files[0]) as icon:
                self.assertEqual(icon.getpixel((0, 0))[3], 0)
            with Image.open(files[2]) as maskable:
                self.assertEqual(maskable.getpixel((0, 0))[3], 255)

    def test_head_patch_is_idempotent_and_overrides_default_manifest(self):
        html = (
            '<!doctype html><html lang="en"><head>'
            '<meta charset="utf-8">'
            '<link rel="manifest" href="/streamlit-default.json">'
            '<title>Streamlit</title></head><body><div id="root"></div></body></html>'
        )
        revised = inject_head(html)
        self.assertIn('rel="manifest" href="/app/static/khula-manifest.json"', revised)
        self.assertIn('rel="apple-touch-icon"', revised)
        self.assertIn('name="apple-mobile-web-app-title" content="Khula"', revised)
        self.assertNotIn("streamlit-default.json", revised)
        self.assertEqual(revised.count(MARKER), 1)
        self.assertEqual(inject_head(revised), revised)
        with tempfile.TemporaryDirectory() as tmp:
            index = Path(tmp) / "index.html"
            index.write_text(html, encoding="utf-8")
            self.assertEqual(patch_index(index, apply=False), revised)
            self.assertEqual(index.read_text(encoding="utf-8"), html)
            self.assertEqual(patch_index(index, apply=True), revised)
            self.assertEqual(index.read_text(encoding="utf-8"), revised)
        with self.assertRaises(ValueError):
            inject_head("<div>Not a Streamlit HTML shell</div>")
        with self.assertRaises(ValueError):
            inject_head("<html><body>No head close</body></html>")

    def test_mobile_installer_has_branded_manifest_and_no_financial_offline_cache(self):
        page = INSTALLER.read_text(encoding="utf-8")
        self.assertIn('rel="manifest" href="/app/static/khula-manifest.json"', page)
        self.assertIn('rel="apple-touch-icon"', page)
        self.assertIn('href="/"', page)
        self.assertIn("beforeinstallprompt", page)
        self.assertIn("Add to Home Screen", page)
        self.assertIn("Safari", page)
        self.assertIn("Chrome", page)
        self.assertIn("internet connection is required", page.lower())
        self.assertNotIn("serviceWorker.register", page)
        self.assertNotIn("localStorage", page)
        self.assertNotIn("indexedDB", page)
        self.assertNotIn("<iframe", page.lower())

    def test_hardened_installer_blocks_unreviewed_inline_code(self):
        template = INSTALLER.read_text(encoding="utf-8")
        self.assertEqual(template.count(SCRIPT_PLACEHOLDER), 1)
        self.assertEqual(template.count(STYLE_PLACEHOLDER), 1)
        self.assertNotIn("'unsafe-inline'", template)
        self.assertNotIn("'unsafe-eval'", template)
        hardened = render_secure_installer(template)
        self.assertTrue(validate_hardened_installer(hardened))
        self.assertNotIn(SCRIPT_PLACEHOLDER, hardened)
        self.assertNotIn(STYLE_PLACEHOLDER, hardened)
        self.assertIn("script-src 'sha256-", hardened)
        self.assertIn("style-src 'sha256-", hardened)
        self.assertIn("connect-src 'none'", hardened)
        self.assertIn("worker-src 'none'", hardened)
        self.assertIn("form-action 'none'", hardened)
        self.assertIn("manifest-src 'self'", hardened)

        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "install.html"
            target.write_text(template, encoding="utf-8")
            self.assertEqual(build_install_page(target, apply=False), hardened)
            self.assertEqual(target.read_text(encoding="utf-8"), template)
            self.assertEqual(build_install_page(target, apply=True), hardened)
            self.assertEqual(build_install_page(target, apply=True), hardened)
            self.assertEqual(target.read_text(encoding="utf-8"), hardened)

        with self.assertRaises(ValueError):
            validate_hardened_installer(
                hardened.replace("button.hidden = true;", "button.hidden = false;", 1)
            )
        with self.assertRaises(ValueError):
            validate_hardened_installer(
                hardened.replace("#07120f", "#080808", 1)
            )
        with self.assertRaises(ValueError):
            render_secure_installer(template.replace(
                "script-src 'sha256-" + SCRIPT_PLACEHOLDER + "'",
                "script-src 'unsafe-inline'",
            ))
        with self.assertRaises(ValueError):
            render_secure_installer(template.replace(
                "form-action 'none'", "form-action 'self'",
            ))

    def test_install_from_https_only_and_no_offline_financial_data(self):
        page = INSTALLER.read_text(encoding="utf-8")
        self.assertIn("khula-collective-production.up.railway.app", page)
        self.assertIn("official HTTPS website", page)
        self.assertIn("unofficial Khula APK", page)
        self.assertIn('content="no-referrer"', page)
        self.assertIn('content="noindex,nofollow,noarchive"', page)
        self.assertNotIn("serviceWorker.register", page)
        self.assertNotIn("localStorage", page)
        self.assertNotIn("indexedDB", page)
        self.assertNotIn("fetch(", page)
        self.assertNotIn("<iframe", page.lower())

    def test_static_serving_enabled_and_installer_accessible_from_login(self):
        config = (ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
        self.assertIn("enableStaticServing = true", config)
        login = (ROOT / "khula_pages1.py").read_text(encoding="utf-8")
        app = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("/app/static/install.html", login)
        self.assertIn("/app/static/install.html", app)


if __name__ == "__main__":
    unittest.main()
