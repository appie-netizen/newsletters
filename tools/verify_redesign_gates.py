#!/usr/bin/env python
"""Strict gates for redesign_website pipeline G0-G7."""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path
from _common import PROJECT_ROOT, TMP_DIR, read_json, write_json
SITES_DIR = PROJECT_ROOT / "sites"
GITHUB_ORG = "github.com/appie-netizen/"
MIN_AUDIT_BYTES = 500

def _fail(gid, reason):
    return {"id": gid, "reason": reason}

def _file_ok(path, *, min_bytes=1):
    try:
        return path.is_file() and path.stat().st_size >= min_bytes
    except OSError:
        return False

def _load_gates_json(site_dir):
    path = site_dir / "gates.json"
    if not path.is_file():
        return {}
    try:
        data = read_json(path)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError, ValueError):
        return {}

def _find_audit_md(audit_dir, letter):
    exact = audit_dir / f"audit_{letter}.md"
    if _file_ok(exact, min_bytes=MIN_AUDIT_BYTES):
        return exact
    matches = sorted(audit_dir.glob(f"audit_{letter}_*.md"))
    for m in matches:
        if _file_ok(m, min_bytes=MIN_AUDIT_BYTES):
            return m
    if exact.exists():
        return exact
    return matches[0] if matches else None

def _has_next_dep(pkg_path):
    try:
        data = read_json(pkg_path)
    except (OSError, json.JSONDecodeError, ValueError):
        return False
    if not isinstance(data, dict):
        return False
    for key in ("dependencies", "devDependencies"):
        deps = data.get(key) or {}
        if isinstance(deps, dict) and "next" in deps:
            return True
    return False

def _find_next_project(site_dir, slug):
    nested = site_dir / f"{slug}-website" / "package.json"
    if nested.is_file() and _has_next_dep(nested):
        return nested.parent
    root_pkg = site_dir / "package.json"
    if root_pkg.is_file() and _has_next_dep(root_pkg):
        return site_dir
    for pkg in sorted(site_dir.glob("*/package.json")):
        if _has_next_dep(pkg):
            return pkg.parent
    return None

def _find_html_deliverable(site_dir):
    for pattern in ("mockup/*.html", "audit/*.html"):
        for p in sorted(site_dir.glob(pattern)):
            if p.is_file() and p.stat().st_size > 0:
                return p
    return None

def _resolve_git_dir(proj):
    git_dir = proj / ".git"
    if git_dir.is_file():
        try:
            text = git_dir.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None
        m = re.search(r"gitdir:\s*(.+)", text)
        if not m:
            return None
        return (proj / m.group(1).strip()).resolve()
    if git_dir.is_dir():
        return git_dir
    return None

def _read_git_origin(proj):
    git_dir = _resolve_git_dir(proj)
    if git_dir is None:
        return None
    cfg = git_dir / "config"
    if not cfg.is_file():
        return None
    try:
        text = cfg.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    in_origin = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("[") and s.endswith("]"):
            in_origin = s.lower() == '[remote "origin"]'
            continue
        if in_origin and s.lower().startswith("url"):
            _, _, val = s.partition("=")
            return val.strip() or None
    return None

def _read_git_head_commit(proj):
    git_dir = _resolve_git_dir(proj)
    if git_dir is None:
        return None
    head = git_dir / "HEAD"
    if not head.is_file():
        return None
    try:
        content = head.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None
    if content.startswith("ref:"):
        ref = content[4:].strip()
        ref_path = git_dir / ref
        if ref_path.is_file():
            try:
                return ref_path.read_text(encoding="utf-8", errors="replace").strip() or None
            except OSError:
                return None
        packed = git_dir / "packed-refs"
        if packed.is_file():
            try:
                for line in packed.read_text(encoding="utf-8", errors="replace").splitlines():
                    if line.startswith("#") or not line.strip():
                        continue
                    parts = line.split()
                    if len(parts) >= 2 and parts[1] == ref:
                        return parts[0]
            except OSError:
                return None
        return None
    if re.fullmatch(r"[0-9a-f]{7,40}", content):
        return content
    return None

def check_gates(slug, *, run_build=False):
    _ = run_build
    passed = []
    failed = []
    site_dir = SITES_DIR / slug
    audit_dir = TMP_DIR / f"audit_{slug}"
    gates = _load_gates_json(site_dir)

    kickoff = site_dir / "KICKOFF.md"
    readme = site_dir / "README.md"
    if kickoff.is_file() and readme.is_file():
        passed.append("G0")
    else:
        missing = []
        if not kickoff.is_file():
            missing.append(str(kickoff.relative_to(PROJECT_ROOT)))
        if not readme.is_file():
            missing.append(str(readme.relative_to(PROJECT_ROOT)))
        failed.append(_fail("G0", "missing " + ", ".join(missing)))

    capture = audit_dir / "capture.json"
    if _file_ok(capture):
        passed.append("G1")
    else:
        failed.append(_fail("G1", f"missing {capture.relative_to(PROJECT_ROOT)}"))

    g2_ok = True
    g2_reasons = []
    for letter in ("a", "b", "c"):
        found = _find_audit_md(audit_dir, letter)
        if found is None or not _file_ok(found, min_bytes=MIN_AUDIT_BYTES):
            g2_ok = False
            if found is None:
                g2_reasons.append(
                    f"missing audit_{letter}.md (or audit_{letter}_*.md) under "
                    f"{audit_dir.relative_to(PROJECT_ROOT)}"
                )
            else:
                size = found.stat().st_size if found.is_file() else 0
                g2_reasons.append(
                    f"{found.relative_to(PROJECT_ROOT)} too small "
                    f"({size} bytes, need >{MIN_AUDIT_BYTES})"
                )
    if g2_ok:
        passed.append("G2")
    else:
        failed.append(_fail("G2", "; ".join(g2_reasons)))

    brief = audit_dir / "redesign_brief.md"
    if _file_ok(brief, min_bytes=MIN_AUDIT_BYTES):
        passed.append("G3")
    else:
        if not brief.is_file():
            failed.append(_fail("G3", f"missing {brief.relative_to(PROJECT_ROOT)}"))
        else:
            failed.append(
                _fail(
                    "G3",
                    f"{brief.relative_to(PROJECT_ROOT)} too small "
                    f"({brief.stat().st_size} bytes, need >{MIN_AUDIT_BYTES})",
                )
            )

    html = _find_html_deliverable(site_dir)
    if html is not None:
        passed.append("G4")
    else:
        failed.append(
            _fail(
                "G4",
                f"no mockup/*.html or audit/*.html under "
                f"{site_dir.relative_to(PROJECT_ROOT)}",
            )
        )

    next_proj = _find_next_project(site_dir, slug)
    if next_proj is not None:
        passed.append("G5")
    else:
        failed.append(
            _fail(
                "G5",
                f"no Next.js package.json at "
                f"sites/{slug}/{slug}-website/, sites/{slug}/*/package.json, "
                f"or sites/{slug}/package.json with a next dependency",
            )
        )

    build_marker = (next_proj / ".next" / "BUILD_ID") if next_proj else None
    build_ok_stamp = bool(gates.get("build_ok") is True)
    has_build_marker = bool(build_marker and build_marker.is_file())
    if next_proj and has_build_marker:
        passed.append("G6")
    elif next_proj and build_ok_stamp and not has_build_marker:
        failed.append(_fail("G6", f"gates.json build_ok=true but missing {build_marker}"))
    elif next_proj:
        failed.append(
            _fail(
                "G6",
                f"missing {next_proj.relative_to(PROJECT_ROOT)}/.next/BUILD_ID "
                f"and gates.json build_ok is not true",
            )
        )
    else:
        failed.append(_fail("G6", "no Next.js project to verify build (see G5)"))

    if next_proj is None:
        failed.append(_fail("G7", "no Next.js project for remote check (see G5)"))
    else:
        url = _read_git_origin(next_proj)
        commit = _read_git_head_commit(next_proj)
        if not url:
            failed.append(_fail("G7", "no origin url in nested .git/config"))
        else:
            url_l = url.lower()
            url_norm = url_l.replace("git@", "").replace("github.com:", "github.com/")
            if GITHUB_ORG not in url_norm and GITHUB_ORG not in url_l:
                failed.append(
                    _fail("G7", f"origin remote is not under {GITHUB_ORG}: {url!r}")
                )
            elif not commit:
                failed.append(_fail("G7", "no commits / unresolved HEAD in nested repo"))
            else:
                passed.append("G7")

    return passed, failed

def write_status(slug, passed, failed):
    site_dir = SITES_DIR / slug
    site_dir.mkdir(parents=True, exist_ok=True)
    path = site_dir / "gates.json"
    existing = _load_gates_json(site_dir)
    status = {
        **existing,
        "slug": slug,
        "passed": passed,
        "failed": failed,
        "ok": len(failed) == 0,
        "gates": {
            gid: (gid in passed)
            for gid in ("G0", "G1", "G2", "G3", "G4", "G5", "G6", "G7")
        },
    }
    write_json(path, status)
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Verify redesign_website hard gates G0-G7 for a client slug."
    )
    parser.add_argument("--slug", required=True, help="Client slug under sites/")
    parser.add_argument(
        "--write-status",
        action="store_true",
        help="Update sites/<slug>/gates.json with pass/fail per gate",
    )
    parser.add_argument(
        "--run-build",
        action="store_true",
        help="Reserved; prefer existing .next/BUILD_ID or gates.json build_ok",
    )
    args = parser.parse_args(argv)

    slug = (args.slug or "").strip()
    if not slug or re.search(r"[\\/]", slug) or slug in (".", ".."):
        sys.stderr.write("usage error: --slug must be a simple directory name\n")
        return 1

    passed, failed = check_gates(slug, run_build=args.run_build)
    summary = {
        "slug": slug,
        "passed": passed,
        "failed": failed,
        "ok": len(failed) == 0,
    }

    if args.write_status:
        path = write_status(slug, passed, failed)
        summary["gates_json"] = str(path.relative_to(PROJECT_ROOT))

    print(json.dumps(summary, indent=2, ensure_ascii=False))

    if failed:
        for item in failed:
            sys.stderr.write(f"GATE {item['id']} FAIL: {item['reason']}\n")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
