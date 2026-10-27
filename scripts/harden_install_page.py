"""Generate exact hash-based CSP for Khula's public install page.

The installer includes no user data or access tokens. Its reviewed, static
inline CSS/JS receive SHA-256 hashes; unrelated inline code is blocked by CSP.
Run in the Docker build, not against a live Streamlit or Railway database.

This cannot set HTTP-only security headers on Streamlit's own root response.
"""
import argparse
import base64
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "static" / "install.html"
STYLE_PLACEHOLDER = "KHULA_CSP_STYLE_HASH"
SCRIPT_PLACEHOLDER = "KHULA_CSP_SCRIPT_HASH"
CSP_META = re.compile(
    r'<meta\s+http-equiv="Content-Security-Policy"\s+content="([^"]+)">',
    re.IGNORECASE,
)
STYLE = re.compile(r"<style(?:\s+[^>]*)?>([\s\S]*?)</style>", re.IGNORECASE)
SCRIPT = re.compile(r"<script(?:\s+[^>]*)?>([\s\S]*?)</script>", re.IGNORECASE)


def hash_content(code):
    return base64.b64encode(hashlib.sha256(code.encode("utf-8")).digest()).decode("ascii")


def render_secure_installer(source):
    """Return a hardened static installer with a CSP binding exact source."""
    if not isinstance(source, str):
        raise TypeError("Installer source must be text.")
    styles = STYLE.findall(source)
    scripts = SCRIPT.findall(source)
    policies = CSP_META.findall(source)
    if len(styles) != 1 or len(scripts) != 1 or len(policies) != 1:
        raise ValueError("Installer requires one reviewed CSS/JS block and one CSP meta.")
    if source.count(STYLE_PLACEHOLDER) != 1 or source.count(SCRIPT_PLACEHOLDER) != 1:
        raise ValueError("Missing or duplicate hashed-CSP placeholders.")
    if "unsafe-inline" in policies[0] or "unsafe-eval" in policies[0]:
        raise ValueError("Installer must not allow blanket inline execution.")
    required = (
        "default-src 'none'",
        "connect-src 'none'",
        "worker-src 'none'",
        "form-action 'none'",
        "object-src 'none'",
        "base-uri 'none'",
        "manifest-src 'self'",
    )
    if any(rule not in policies[0] for rule in required):
        raise ValueError("The static installer CSP is missing a required restriction.")
    result = source.replace(STYLE_PLACEHOLDER, hash_content(styles[0]))
    result = result.replace(SCRIPT_PLACEHOLDER, hash_content(scripts[0]))
    validate_hardened_installer(result)
    return result


def validate_hardened_installer(html):
    """Fail closed if a reviewed script/style changes without updating hashes."""
    policies = CSP_META.findall(html)
    styles = STYLE.findall(html)
    scripts = SCRIPT.findall(html)
    if len(policies) != 1 or len(styles) != 1 or len(scripts) != 1:
        raise ValueError("Malformed or duplicate installer blocks.")
    policy = policies[0]
    if (STYLE_PLACEHOLDER in html or SCRIPT_PLACEHOLDER in html
            or "unsafe-inline" in policy or "unsafe-eval" in policy):
        raise ValueError("Installer CSP has unresolved or unsafe permissions.")
    for kind, content in (("style", styles[0]), ("script", scripts[0])):
        expected = f"{kind}-src 'sha256-{hash_content(content)}'"
        if expected not in policy:
            raise ValueError(f"{kind} changed without a matching CSP hash.")
    if ('rel="manifest" href="/app/static/khula-manifest.json"' not in html
            or "https://khula-collective-production.up.railway.app" in html
            or "<iframe" in html.lower()):
        raise ValueError("Installer origin/scope has changed or embeds an iframe.")
    if re.search(r"\bon[a-z]+\s*=", html, re.IGNORECASE):
        raise ValueError("Inline HTML event handlers are forbidden.")
    return True


def build_install_page(path=INSTALLER, *, apply=False):
    path = Path(path)
    raw = path.read_text(encoding="utf-8")
    if STYLE_PLACEHOLDER in raw and SCRIPT_PLACEHOLDER in raw:
        output = render_secure_installer(raw)
    else:
        validate_hardened_installer(raw)
        output = raw
    if apply and output != raw:
        path.write_text(output, encoding="utf-8")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Verify/generate Khula's exact CSP hashes before deployment."
    )
    parser.add_argument("--apply", action="store_true",
                        help="Rewrite installer inside the Docker build only")
    parser.add_argument("--check", action="store_true",
                        help="Validate templates without modifying files")
    args = parser.parse_args()
    output = build_install_page(apply=args.apply and not args.check)
    validate_hardened_installer(output)
    print("Khula secure installer CSP: exact script/style hashes verified.")
