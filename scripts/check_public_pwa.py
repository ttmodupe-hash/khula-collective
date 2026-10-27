"""Read-only external checks for Khula's deployed mobile web-app metadata.

Run after Railway reaches SUCCESS. Fetches only the public HTML/manifest/icon
endpoints, never logs in or touches private member or banking records.
"""
import argparse
import json
import ssl
import struct
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urlsplit

try:
    from scripts.harden_install_page import validate_hardened_installer
except ModuleNotFoundError:
    from harden_install_page import validate_hardened_installer

INSTALL_PATH = "/app/static/install.html"
MANIFEST_PATH = "/app/static/khula-manifest.json"


class _HeadLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.manifests = []

    def handle_starttag(self, tag, attrs):
        if tag == "link":
            attrs = dict(attrs)
            if attrs.get("rel", "").lower() == "manifest":
                self.manifests.append(attrs.get("href", ""))


def _request(url, expected_origin):
    req = urllib.request.Request(
        url, headers={
            "User-Agent": "Khula-Mobile-Install-Readiness/1.1",
            "Accept-Encoding": "identity",
        }
    )
    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    with urllib.request.urlopen(req, timeout=12, context=context) as response:
        if response.status != 200:
            raise AssertionError(f"Expected HTTP 200 for {url}; got {response.status}")
        final = urlsplit(response.geturl())
        delivered_origin = final.scheme + "://" + final.netloc
        if delivered_origin != expected_origin:
            raise AssertionError(
                "Khula installation resource redirected outside the official HTTPS origin."
            )
        return response.headers, response.read(500_000)


def check_public_pwa(base_url):
    parsed = urlsplit(base_url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Use the verified Khula HTTPS production origin.")
    if parsed.query or parsed.fragment or parsed.username or parsed.password:
        raise ValueError("No credentials, query parameters or fragments allowed.")
    base = parsed.scheme + "://" + parsed.netloc
    root_headers, root = _request(base + "/", base)
    if "text/html" not in root_headers.get("Content-Type", "").lower():
        raise AssertionError("Public root is not an HTML document.")
    parser = _HeadLinks()
    parser.feed(root.decode("utf-8"))
    if parser.manifests != [MANIFEST_PATH]:
        raise AssertionError(
            f"Khula manifest must be the sole link in the root HTML head; got {parser.manifests}"
        )

    manifest_headers, manifest_data = _request(base + MANIFEST_PATH, base)
    if "json" not in manifest_headers.get("Content-Type", "").lower():
        raise AssertionError("PWA manifest must be served as JSON.")
    manifest = json.loads(manifest_data.decode("utf-8"))
    if (manifest.get("name") != "Khula Collective"
            or manifest.get("start_url") != "/"
            or manifest.get("scope") != "/"
            or manifest.get("display") != "standalone"):
        raise AssertionError("Live manifest identity or scope differs from reviewed release.")

    install_headers, install = _request(base + INSTALL_PATH, base)
    if "text/html" not in install_headers.get("Content-Type", "").lower():
        raise AssertionError("Mobile installation page should be HTML.")
    install_html = install.decode("utf-8")
    validate_hardened_installer(install_html)
    if (MANIFEST_PATH not in install_html
            or b"Add to Home Screen" not in install
            or b"beforeinstallprompt" not in install):
        raise AssertionError("Mobile installer is incomplete.")

    for headers, label in (
        (manifest_headers, "manifest"), (install_headers, "installer")
    ):
        if headers.get("X-Content-Type-Options", "").lower() != "nosniff":
            raise AssertionError(f"Missing X-Content-Type-Options: nosniff on {label}")

    for icon in manifest.get("icons", []):
        src = icon["src"]
        if not src.startswith("/app/static/khula-icon-"):
            raise AssertionError("Unknown PWA icon source.")
        icon_headers, content = _request(base + src, base)
        if "image/png" not in icon_headers.get("Content-Type", "").lower():
            raise AssertionError(f"Icon has invalid content type: {src}")
        if content[:8] != b"\x89PNG\r\n\x1a\n":
            raise AssertionError("Returned icon does not decode as PNG.")
        dims = struct.unpack(">II", content[16:24])
        expected = 192 if icon["sizes"] == "192x192" else 512
        if dims != (expected, expected):
            raise AssertionError(f"Icon size mismatch: {src}, {dims}")
    print("Official HTTPS origin and strict hashed-only installer CSP validated.")
    print("PWA manifest/installer use nosniff; no cross-origin resource redirects.")
    if len(manifest.get("icons", [])) < 2:
        raise AssertionError("192px and 512px icons are required.")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url",
                        default="https://khula-collective-production.up.railway.app")
    args = parser.parse_args()
    check_public_pwa(args.url)
    print("Khula PWA public HTML, manifest, Android/iOS guide and PNG icons verified.")
