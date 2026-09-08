#!/usr/bin/env python
"""Capture an existing website for a design/UX audit.

Drives a real Chromium (Playwright) over the target site and records everything
the three audits need: full-page screenshots at mobile/tablet/desktop, rendered
HTML, a headings/landmarks outline, the computed colour + type "tokens" actually
in use, console errors/warnings, failed + 4xx/5xx requests, pragmatic perf
metrics (nav timing, LCP, CLS), and an axe-core accessibility run.

First run needs the browser binary (one-time, ~150 MB, free):
    python -m playwright install chromium

Usage:
    python tools/capture_site.py --url https://example.com
    python tools/capture_site.py --url https://example.com --slug acme --max-pages 8
    python tools/capture_site.py --url https://example.com --pages / /about /pricing /contact
    python tools/capture_site.py --url https://example.com --no-axe   # skip a11y (offline)

Output (all under .tmp/audit_<slug>/):
    capture.json                     -- manifest the agent reads to run the audits
    screens/<page>__<viewport>.png   -- full-page screenshots
    html/<page>.html                 -- rendered DOM
    outline/<page>.txt               -- headings + landmark outline (reading order)

Exits non-zero if the start URL can't be loaded at all.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

from _common import TMP_DIR, slugify, write_json

AXE_CDN = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js"

DEFAULT_VIEWPORTS = {
    "mobile": (375, 812),
    "tablet": (768, 1024),
    "desktop": (1440, 900),
}

# Script run in the page to pull the design "tokens" actually rendered: every
# distinct colour, font-family, font-size, font-weight, radius and shadow, with
# rough usage counts so the audit can tell a system from a pile of one-offs.
TOKENS_JS = r"""
() => {
  const els = Array.from(document.querySelectorAll('body *')).slice(0, 4000);
  const bump = (m, k) => { if (!k) return; m[k] = (m[k] || 0) + 1; };
  const color = {}, bg = {}, family = {}, size = {}, weight = {}, radius = {}, shadow = {};
  for (const el of els) {
    const s = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    bump(color, s.color);
    if (s.backgroundColor && s.backgroundColor !== 'rgba(0, 0, 0, 0)') bump(bg, s.backgroundColor);
    bump(family, s.fontFamily);
    bump(size, s.fontSize);
    bump(weight, s.fontWeight);
    if (s.borderRadius && s.borderRadius !== '0px') bump(radius, s.borderRadius);
    if (s.boxShadow && s.boxShadow !== 'none') bump(shadow, s.boxShadow);
  }
  const top = (m, n) => Object.entries(m).sort((a, b) => b[1] - a[1]).slice(0, n)
    .map(([k, v]) => ({ value: k, count: v }));
  return {
    text_colors: top(color, 24),
    background_colors: top(bg, 24),
    font_families: top(family, 12),
    font_sizes: top(size, 24),
    font_weights: top(weight, 12),
    border_radii: top(radius, 16),
    shadows: top(shadow, 12),
  };
}
"""

# Headings + landmark outline in DOM order -> a quick read of information
# hierarchy without opening the screenshots.
OUTLINE_JS = r"""
() => {
  const out = [];
  const walk = document.querySelectorAll(
    'h1,h2,h3,h4,h5,h6,header,nav,main,aside,footer,section[aria-label],[role="banner"],[role="navigation"],[role="main"],[role="contentinfo"]'
  );
  for (const el of walk) {
    const tag = el.tagName.toLowerCase();
    const label = (el.getAttribute('aria-label') || el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 120);
    if (/^h[1-6]$/.test(tag)) out.push(`${'  '.repeat(+tag[1] - 1)}${tag.toUpperCase()}  ${label}`);
    else out.push(`[${tag}]  ${label}`);
  }
  return out.join('\n');
}
"""

# Pragmatic Core Web Vitals: LCP via PerformanceObserver, CLS accumulated over
# the observation window, plus navigation timing. Resolves after `settle` ms.
VITALS_JS = """
(settle) => new Promise((resolve) => {
  let lcp = 0, cls = 0;
  try {
    new PerformanceObserver((l) => {
      for (const e of l.getEntries()) lcp = Math.max(lcp, e.renderTime || e.loadTime || e.startTime || 0);
    }).observe({ type: 'largest-contentful-paint', buffered: true });
  } catch (e) {}
  try {
    new PerformanceObserver((l) => {
      for (const e of l.getEntries()) if (!e.hadRecentInput) cls += e.value;
    }).observe({ type: 'layout-shift', buffered: true });
  } catch (e) {}
  setTimeout(() => {
    const nav = performance.getEntriesByType('navigation')[0] || {};
    resolve({
      lcp_ms: Math.round(lcp),
      cls: Math.round(cls * 1000) / 1000,
      dom_content_loaded_ms: Math.round(nav.domContentLoadedEventEnd || 0),
      load_ms: Math.round(nav.loadEventEnd || 0),
      transfer_bytes: nav.transferSize || 0,
      dom_nodes: document.getElementsByTagName('*').length,
    });
  }, settle);
})
"""


def goto_resilient(page, url: str):
    """Navigate, preferring a full networkidle but not depending on it.

    Wix / Squarespace / chat-widget sites keep long-poll connections open, so
    ``networkidle`` never fires and a 45s wait just times out. Fall back to
    ``domcontentloaded`` + a fixed settle so those sites still capture.
    Returns the response (may be None on the fallback path).
    """
    try:
        return page.goto(url, wait_until="networkidle", timeout=30_000)
    except Exception:  # noqa: BLE001 -- networkidle never settled; try a softer wait
        resp = page.goto(url, wait_until="domcontentloaded", timeout=45_000)
        try:
            page.wait_for_load_state("load", timeout=15_000)
        except Exception:  # noqa: BLE001
            pass
        page.wait_for_timeout(3500)
        return resp


def page_slug(url: str, base_path: str) -> str:
    path = urlparse(url).path or "/"
    if path in ("", "/"):
        return "home"
    return slugify(path.strip("/").replace("/", "-")) or "page"


def same_site(a: str, b: str) -> bool:
    return urlparse(a).netloc.replace("www.", "") == urlparse(b).netloc.replace("www.", "")


def discover_links(page, start_url: str, limit: int) -> list[str]:
    hrefs = page.eval_on_selector_all(
        "a[href]", "els => els.map(e => e.getAttribute('href'))"
    )
    seen, ordered = set(), []
    for h in hrefs:
        if not h or h.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        full = urljoin(start_url, h).split("#")[0].rstrip("/")
        if not full or full in seen or not same_site(full, start_url):
            continue
        seen.add(full)
        ordered.append(full)
        if len(ordered) >= limit:
            break
    return ordered


def capture_page(context, url: str, out: Path, viewports: dict, run_axe: bool,
                 settle_ms: int) -> dict:
    page = context.new_page()
    console: list[dict] = []
    page_errors: list[str] = []
    bad_responses: list[dict] = []
    failed_requests: list[dict] = []

    page.on("console", lambda m: console.append({"type": m.type, "text": m.text[:500]})
            if m.type in ("error", "warning") else None)
    page.on("pageerror", lambda e: page_errors.append(str(e)[:500]))
    page.on("requestfailed", lambda r: failed_requests.append(
        {"url": r.url[:300], "reason": (r.failure or "")[:200]}))
    page.on("response", lambda r: bad_responses.append(
        {"url": r.url[:300], "status": r.status}) if r.status >= 400 else None)

    slug = page_slug(url, "")
    record: dict = {"url": url, "slug": slug}
    try:
        resp = goto_resilient(page, url)
        record["http_status"] = resp.status if resp else None
    except Exception as e:  # noqa: BLE001
        record["error"] = f"navigation failed: {e}"
        page.close()
        return record

    page.wait_for_timeout(1200)
    record["title"] = page.title()
    record["meta_description"] = page.eval_on_selector(
        "meta[name=description]", "e => e.content", strict=False) if page.query_selector(
        "meta[name=description]") else None

    # screenshots per viewport
    shots = {}
    for name, (w, h) in viewports.items():
        page.set_viewport_size({"width": w, "height": h})
        page.wait_for_timeout(400)
        shot = out / "screens" / f"{slug}__{name}.png"
        shot.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(shot), full_page=True)
        shots[name] = str(shot.relative_to(TMP_DIR))
    record["screenshots"] = shots
    page.set_viewport_size({"width": 1440, "height": 900})

    # rendered HTML + outline
    html_path = out / "html" / f"{slug}.html"
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(page.content(), encoding="utf-8")
    record["html"] = str(html_path.relative_to(TMP_DIR))

    outline_path = out / "outline" / f"{slug}.txt"
    outline_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        outline_path.write_text(page.evaluate(OUTLINE_JS), encoding="utf-8")
        record["outline"] = str(outline_path.relative_to(TMP_DIR))
    except Exception as e:  # noqa: BLE001
        record["outline_error"] = str(e)

    try:
        record["tokens"] = page.evaluate(TOKENS_JS)
    except Exception as e:  # noqa: BLE001
        record["tokens_error"] = str(e)

    try:
        record["vitals"] = page.evaluate(VITALS_JS, settle_ms)
    except Exception as e:  # noqa: BLE001
        record["vitals_error"] = str(e)

    if run_axe:
        try:
            page.add_script_tag(url=AXE_CDN)
            page.wait_for_function("window.axe !== undefined", timeout=10_000)
            axe = page.evaluate("() => axe.run(document, {resultTypes: ['violations']})")
            record["axe"] = {
                "violations": [
                    {
                        "id": v["id"],
                        "impact": v.get("impact"),
                        "help": v["help"],
                        "nodes": len(v["nodes"]),
                        "sample_target": (v["nodes"][0]["target"] if v["nodes"] else None),
                    }
                    for v in axe.get("violations", [])
                ],
                "counts": _axe_counts(axe.get("violations", [])),
            }
        except Exception as e:  # noqa: BLE001
            record["axe_error"] = f"{e} (use --no-axe if offline)"

    record["console"] = console
    record["page_errors"] = page_errors
    record["bad_responses"] = _dedupe(bad_responses)
    record["failed_requests"] = _dedupe(failed_requests)
    page.close()
    return record


def _axe_counts(violations: list[dict]) -> dict:
    counts = {"critical": 0, "serious": 0, "moderate": 0, "minor": 0}
    for v in violations:
        counts[v.get("impact") or "minor"] = counts.get(v.get("impact") or "minor", 0) + 1
    return counts


def _dedupe(items: list[dict]) -> list[dict]:
    seen, out = set(), []
    for it in items:
        key = json.dumps(it, sort_keys=True)
        if key not in seen:
            seen.add(key)
            out.append(it)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", required=True, help="start URL of the site to audit")
    ap.add_argument("--slug", help="override the derived output folder name")
    ap.add_argument("--pages", nargs="+", metavar="PATH_OR_URL",
                    help="explicit pages to capture (paths are resolved against --url); "
                         "default: crawl same-site links from the start page")
    ap.add_argument("--max-pages", type=int, default=6,
                    help="max pages when crawling (default 6)")
    ap.add_argument("--viewports", help="comma list like 375x812,768x1024,1440x900 "
                    "(default mobile/tablet/desktop)")
    ap.add_argument("--settle-ms", type=int, default=3500,
                    help="how long to observe LCP/CLS per page (default 3500)")
    ap.add_argument("--no-axe", action="store_true", help="skip the axe-core a11y run")
    ap.add_argument("--user-agent", help="override the browser User-Agent string")
    ap.add_argument("--extra-links", nargs="+", metavar="PATH_OR_URL",
                    help="pages the link crawl can't see (JS dropdown nav etc.); "
                         "added to whatever the crawl finds")
    args = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.stderr.write(
            "playwright not installed. Run:\n"
            "  pip install -r requirements.txt\n"
            "  python -m playwright install chromium\n"
        )
        return 1

    if args.viewports:
        viewports = {}
        for chunk in args.viewports.split(","):
            w, h = chunk.lower().split("x")
            viewports[f"{w}w"] = (int(w), int(h))
    else:
        viewports = DEFAULT_VIEWPORTS

    start = args.url if "://" in args.url else "https://" + args.url
    slug = args.slug or slugify(urlparse(start).netloc.replace("www.", ""))
    out = TMP_DIR / f"audit_{slug}"
    out.mkdir(parents=True, exist_ok=True)

    manifest: dict = {
        "target_url": start,
        "slug": slug,
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "viewports": {k: list(v) for k, v in viewports.items()},
        "pages": [],
    }

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        # A stock desktop-Chrome UA. An unusual UA (or a "bot" marker) makes some
        # CDNs/WAFs drop CORS headers or serve a challenge, which silently breaks
        # builder sites (Readymag/Webflow/etc.) that fetch their CSS via XHR.
        context = browser.new_context(
            user_agent=args.user_agent or (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            ),
            ignore_https_errors=True,
        )

        # decide the page list
        if args.pages:
            targets = [p if "://" in p else urljoin(start, p) for p in args.pages]
        else:
            probe = context.new_page()
            try:
                goto_resilient(probe, start)
            except Exception as e:  # noqa: BLE001
                sys.stderr.write(f"could not load start URL {start}: {e}\n")
                probe.close()
                browser.close()
                return 1
            probe.wait_for_timeout(1000)
            targets = [start.rstrip("/")] + discover_links(probe, start, args.max_pages - 1)
            probe.close()
            for extra in (args.extra_links or []):
                full = (extra if "://" in extra else urljoin(start, extra)).rstrip("/")
                if full not in targets:
                    targets.append(full)

        sys.stderr.write(f"[capture] {slug}: {len(targets)} page(s)\n")
        for i, t in enumerate(targets, 1):
            sys.stderr.write(f"[capture]  ({i}/{len(targets)}) {t}\n")
            rec = capture_page(context, t, out, viewports, run_axe=not args.no_axe,
                               settle_ms=args.settle_ms)
            manifest["pages"].append(rec)

        browser.close()

    ok_pages = [p for p in manifest["pages"] if "error" not in p]
    if not ok_pages:
        sys.stderr.write("[capture] every page failed to load\n")
        write_json(out / "capture.json", manifest)
        return 1

    # roll-up so the agent can eyeball severity before opening details
    manifest["summary"] = {
        "pages_ok": len(ok_pages),
        "pages_failed": len(manifest["pages"]) - len(ok_pages),
        "console_errors": sum(
            len([c for c in p.get("console", []) if c["type"] == "error"]) for p in ok_pages),
        "console_warnings": sum(
            len([c for c in p.get("console", []) if c["type"] == "warning"]) for p in ok_pages),
        "page_errors": sum(len(p.get("page_errors", [])) for p in ok_pages),
        "responses_4xx_5xx": sum(len(p.get("bad_responses", [])) for p in ok_pages),
        "failed_requests": sum(len(p.get("failed_requests", [])) for p in ok_pages),
        "axe_critical": sum(p.get("axe", {}).get("counts", {}).get("critical", 0) for p in ok_pages),
        "axe_serious": sum(p.get("axe", {}).get("counts", {}).get("serious", 0) for p in ok_pages),
        "worst_lcp_ms": max((p.get("vitals", {}).get("lcp_ms", 0) for p in ok_pages), default=0),
        "worst_cls": max((p.get("vitals", {}).get("cls", 0) for p in ok_pages), default=0),
    }

    write_json(out / "capture.json", manifest)
    print(json.dumps({
        "slug": slug,
        "capture_file": str(out / "capture.json"),
        "pages": len(manifest["pages"]),
        "summary": manifest["summary"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
