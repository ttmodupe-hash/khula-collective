"""Patch the trusted Streamlit HTML shell at Docker build time.

Streamlit does not expose a supported server-side HTML <head> extension API.
Patch only the installed package's own static index.html in the *built image*,
never a user's member data or the Railway database volume. Fails on a
changed/missing shell instead of silently claiming the app is installable.
"""
import argparse
import re
from pathlib import Path

MARKER = "<!-- KHULA-PWA-METADATA-v1 -->"
MANIFEST_PATH = "/app/static/khula-manifest.json"
HEAD_ADDITION = f"""
{MARKER}
<link rel="manifest" href="{MANIFEST_PATH}">
<link rel="icon" type="image/png" sizes="192x192" href="/app/static/khula-icon-192.png">
<link rel="apple-touch-icon" sizes="192x192" href="/app/static/khula-icon-192.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Khula">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="theme-color" content="#00b894">
<meta name="description" content="Khula Collective member portal — install on your mobile home screen.">
"""
# If the Streamlit build already ships a manifest, replace it so the browser
# does not install Streamlit instead of Khula.
OTHER_MANIFEST_LINK = re.compile(
    r"<link\b(?=[^>]*\brel\s*=\s*['\"]manifest['\"])[^>]*>\s*",
    re.IGNORECASE | re.DOTALL,
)
CLOSE_HEAD = re.compile(r"</head\s*>", re.IGNORECASE)


def inject_head(html):
    if not isinstance(html, str) or "<html" not in html.lower():
        raise ValueError("A complete Streamlit HTML document is required.")
    if MARKER in html:
        if html.count(MARKER) != 1:
            raise ValueError("Duplicate Khula installation metadata marker.")
        return html
    if len(CLOSE_HEAD.findall(html)) != 1:
        raise ValueError("Cannot locate a unique </head> in Streamlit shell.")
    without_existing_manifest = OTHER_MANIFEST_LINK.sub("", html)
    return CLOSE_HEAD.sub(lambda m: HEAD_ADDITION + "\n" + m.group(0),
                          without_existing_manifest, count=1)


def installed_index_file():
    import streamlit
    index = Path(streamlit.__file__).resolve().parent / "static" / "index.html"
    if not index.is_file():
        raise FileNotFoundError(
            "Streamlit index.html location changed; review PWA integration."
        )
    return index


def patch_index(index_file, *, apply=False):
    index = Path(index_file)
    original = index.read_text(encoding="utf-8")
    revised = inject_head(original)
    if apply and revised != original:
        index.write_text(revised, encoding="utf-8")
    return revised


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Verify or apply Khula PWA HTML head integration")
    p.add_argument("--apply", action="store_true",
                   help="Modify installed Streamlit index.html (during Docker build only)")
    p.add_argument("--check", action="store_true",
                   help="Only verify a patch is possible; do not change files")
    p.add_argument("--index-file", help="Override the index.html path for isolated tests")
    args = p.parse_args()
    path = Path(args.index_file) if args.index_file else installed_index_file()
    updated = patch_index(path, apply=args.apply and not args.check)
    if MARKER not in updated:
        raise SystemExit("PWA metadata injection was not validated.")
    print(f"Khula manifest head integration verified: {path}")
