#!/usr/bin/env python
"""Push a Markdown report into Google Docs.

Used by the redesign_website workflow to deliver the three audits and the
redesign brief as editable Google Docs (the WAT "deliverables live in the cloud"
rule). Drive converts the Markdown on import, so headings, lists, tables and
bold/italic survive.

One-time setup (no cost):
  1. https://console.cloud.google.com  ->  create a project
  2. APIs & Services -> Enable APIs -> enable "Google Drive API"
  3. APIs & Services -> Credentials -> Create credentials -> OAuth client ID
     -> type "Desktop app" -> download the JSON
  4. Save it as  credentials.json  in the project root (already gitignored)
  5. First run opens a browser to authorise; the token is cached to token.json

Usage:
    python tools/export_gdoc.py --md .tmp/audit_acme/audit_a.md --title "Acme — Brand & Anti-Slop Audit"
    python tools/export_gdoc.py --md report.md --title "..." --folder-id 1AbC...   # into a Drive folder
    python tools/export_gdoc.py --md report.md --doc-id 1XyZ...                    # overwrite an existing doc

Prints {"doc_id": "...", "url": "https://docs.google.com/document/d/..."} on success.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _common import PROJECT_ROOT

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
CREDS = PROJECT_ROOT / "credentials.json"
TOKEN = PROJECT_ROOT / "token.json"

SETUP_HINT = (
    "Google Docs export isn't set up yet.\n"
    f"  Missing: {CREDS.name}\n"
    "  See the setup steps in tools/export_gdoc.py's docstring "
    "(enable Drive API, make a Desktop OAuth client, save credentials.json).\n"
    "  Until then, hand off the .md file directly or paste it into a doc."
)


def get_service():
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        sys.stderr.write(
            "Google client libs not installed. Run: pip install -r requirements.txt\n"
        )
        raise

    creds = None
    if TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDS.exists():
                sys.stderr.write(SETUP_HINT + "\n")
                sys.exit(2)
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN.write_text(creds.to_json(), encoding="utf-8")
    return build("drive", "v3", credentials=creds)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--md", required=True, help="path to the Markdown file to upload")
    ap.add_argument("--title", help="Google Doc title (default: the file stem)")
    ap.add_argument("--folder-id", help="Drive folder ID to create the doc in")
    ap.add_argument("--doc-id", help="overwrite this existing Google Doc instead of creating one")
    args = ap.parse_args()

    md_path = Path(args.md)
    if not md_path.exists():
        sys.stderr.write(f"file not found: {md_path}\n")
        return 1
    title = args.title or md_path.stem.replace("_", " ").replace("-", " ").title()

    from googleapiclient.http import MediaFileUpload

    service = get_service()
    media = MediaFileUpload(str(md_path), mimetype="text/markdown", resumable=False)

    if args.doc_id:
        doc = service.files().update(
            fileId=args.doc_id, media_body=media,
            body={"name": title}, supportsAllDrives=True,
        ).execute()
    else:
        meta = {"name": title, "mimeType": "application/vnd.google-apps.document"}
        if args.folder_id:
            meta["parents"] = [args.folder_id]
        doc = service.files().create(
            body=meta, media_body=media, fields="id",
            supportsAllDrives=True,
        ).execute()

    doc_id = doc["id"]
    print(json.dumps({
        "doc_id": doc_id,
        "url": f"https://docs.google.com/document/d/{doc_id}/edit",
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
