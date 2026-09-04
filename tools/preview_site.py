#!/usr/bin/env python
"""Serve docs/ locally so you can review the site exactly as it will publish.

Usage:
    python tools/preview_site.py                 # serve, open the index
    python tools/preview_site.py --slug my-slug  # open that issue
    python tools/preview_site.py --port 8080 --no-open

Serves over real HTTP (not file://) so relative asset paths and feed.xml resolve
the same as on GitHub Pages. Ctrl+C to stop.
"""
from __future__ import annotations

import argparse
import contextlib
import functools
import sys
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from _common import DOCS_DIR, ISSUES_DIR, read_json


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--slug", help="open this issue instead of the index")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--no-open", action="store_true", help="don't launch a browser")
    args = ap.parse_args()

    if not (DOCS_DIR / "index.html").exists():
        sys.stderr.write("docs/index.html not found. Run: python tools/build_site.py --drafts\n")
        return 1

    path = "/"
    if args.slug:
        path = f"/issues/{args.slug}.html"
        title = "?"
        issue_json = ISSUES_DIR / f"{args.slug}.json"
        if issue_json.exists():
            data = read_json(issue_json)
            title = data.get("title", "?")
            words = sum(len(s.get("body_html", "").split()) for s in data.get("sections", []))
            sys.stderr.write(f"[preview] {data.get('title')}\n[preview] dek: {data.get('dek')}\n")
            sys.stderr.write(f"[preview] ~{words} words, {len(data.get('sections', []))} sections\n")

    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(DOCS_DIR))
    httpd = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    url = f"http://127.0.0.1:{args.port}{path}"
    print(f"[preview] serving {DOCS_DIR} at {url}")
    print("[preview] Ctrl+C to stop")

    if not args.no_open:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    with contextlib.suppress(KeyboardInterrupt):
        httpd.serve_forever()
    httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
