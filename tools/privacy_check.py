#!/usr/bin/env python3
"""Privacy-boundary guard for MoneyMan.

MoneyMan's promise is "local by default": it makes no network connections except
for ONE opt-in, off-by-default, address-only home-value lookup. This script makes
that promise *machine-checkable* instead of "trust us":

  * Networking modules may appear ONLY in the files explicitly allowed below.
  * A short list of exfiltration-capable modules may NEVER appear at all.

It parses the real Python (via ``ast``), so comments and docstrings that merely
*mention* networking don't trip it. Run it yourself any time:

    python tools/privacy_check.py

It also runs in CI and in the test suite, so the boundary can't silently erode as
the code changes. Exit code 0 = clean, 1 = a violation was found.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent.parent / "moneyman"

# Networking-capable modules → the only files allowed to import them, and why.
GATED: dict[str, set[str]] = {
    "urllib.request": {"homevalue.py"},   # opt-in, address-only home-value lookup
    "socket": {"serve.py"},               # localhost-only "edit in browser" app
    "http.server": {"serve.py"},          # ditto (binds 127.0.0.1 only)
}

# Modules that must NEVER appear anywhere in the package — there is no legitimate
# local-first use for them, so their presence means the privacy story broke.
FORBIDDEN: set[str] = {
    "requests", "urllib3", "httpx", "aiohttp", "http.client", "httplib",
    "smtplib", "ftplib", "poplib", "imaplib", "telnetlib", "nntplib",
    "xmlrpc.client", "pycurl", "paramiko", "websocket", "websockets",
}


def _imported_modules(tree: ast.AST) -> set[str]:
    """Every dotted module name imported in a parsed source tree."""
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:   # ignore relative (in-package)
                found.add(node.module)
    return found


def check(package_dir: Path = PACKAGE_DIR) -> list[str]:
    """Return a list of human-readable violations (empty list == clean)."""
    violations: list[str] = []
    for path in sorted(package_dir.glob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as e:                   # pragma: no cover - defensive
            violations.append(f"{path.name}: could not parse ({e})")
            continue
        modules = _imported_modules(tree)
        for mod in sorted(modules):
            root = mod.split(".")[0]
            if mod in FORBIDDEN or root in FORBIDDEN:
                violations.append(
                    f"{path.name}: imports forbidden network module '{mod}' "
                    f"— MoneyMan must not use it.")
            for gated, allowed_files in GATED.items():
                if (mod == gated or mod.startswith(gated + ".")) \
                        and path.name not in allowed_files:
                    violations.append(
                        f"{path.name}: imports '{mod}', which is only allowed in "
                        f"{sorted(allowed_files)} (the one documented exception).")
    return violations


def main() -> int:
    violations = check()
    if violations:
        print("PRIVACY CHECK FAILED — networking appeared where it must not:\n")
        for v in violations:
            print(f"  ✗ {v}")
        print("\nIf this is intentional, update tools/privacy_check.py AND the "
              "privacy docs together — never silently.")
        return 1
    print("PRIVACY CHECK PASSED — networking is confined to the documented, "
          "opt-in exceptions only.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
