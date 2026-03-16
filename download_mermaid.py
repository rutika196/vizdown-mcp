"""One-time script to download Mermaid.js for offline/fallback use when the CDN is unreachable.

Usage:
    python download_mermaid.py

Saves mermaid.min.js to src/static/mermaid/mermaid.min.js.
The renderer will use it automatically when the CDN fails (e.g. offline, firewall).
"""

import urllib.request
from pathlib import Path

MERMAID_CDN = "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"
OUTPUT_DIR = Path(__file__).resolve().parent / "src" / "static" / "mermaid"
OUTPUT_FILE = OUTPUT_DIR / "mermaid.min.js"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading Mermaid from:\n  {MERMAID_CDN}\n  -> {OUTPUT_FILE}\n")
    try:
        req = urllib.request.Request(MERMAID_CDN, headers={"User-Agent": "clarity-beta/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        if not data.strip().startswith(b"(function") and not data.strip().startswith(b"!"):
            print("  WARNING: Response does not look like minified JS; saving anyway.")
        OUTPUT_FILE.write_bytes(data)
        print(f"  OK    Saved {len(data):,} bytes to {OUTPUT_FILE}")
    except Exception as e:
        print(f"  FAIL  {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
