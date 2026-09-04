"""Shared helpers for tools. Import, don't run.

Provides:
- load_env()            -> loads .env from project root
- env(key, default)     -> read an env var, error if required and missing
- PROJECT_ROOT          -> Path to the repo root
- TMP_DIR               -> Path to .tmp/ (created on import)
- tmp_path(name)        -> Path inside .tmp/
- ISSUES_DIR / DOCS_DIR -> Path to issues/ and docs/
- read_json / write_json
- load_config()         -> parsed newsletter.config.yaml as a dict
- slugify(text)         -> filesystem/URL-safe slug
- anthropic_client()    -> configured anthropic.Anthropic (errors if no key)
- model_id(cfg)         -> which Claude model to use
- extract_json(text)    -> parse the first JSON object out of an LLM reply
- run_messages(...)     -> messages.create with pause_turn handling + text join
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TMP_DIR = PROJECT_ROOT / ".tmp"
TMP_DIR.mkdir(exist_ok=True)
ISSUES_DIR = PROJECT_ROOT / "issues"
DOCS_DIR = PROJECT_ROOT / "docs"

DEFAULT_MODEL = "claude-opus-5"

_ENV_LOADED = False


def load_env() -> None:
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    try:
        from dotenv import load_dotenv
    except ImportError:
        sys.stderr.write(
            "python-dotenv not installed. Run: pip install -r requirements.txt\n"
        )
        raise
    load_dotenv(PROJECT_ROOT / ".env")
    _ENV_LOADED = True


def env(key: str, default: str | None = None, *, required: bool = False) -> str | None:
    load_env()
    val = os.getenv(key, default)
    if required and not val:
        sys.stderr.write(f"Missing required env var: {key} (set it in .env)\n")
        sys.exit(1)
    return val


def tmp_path(name: str) -> Path:
    return TMP_DIR / name


def read_json(path: str | Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str | Path, data, *, indent: int = 2) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)
        f.write("\n")


# --- newsletter config -------------------------------------------------------

def load_config(path: str | Path | None = None) -> dict:
    """Parse newsletter.config.yaml. Fails loudly if missing or malformed."""
    import yaml

    cfg_path = Path(path) if path else PROJECT_ROOT / "newsletter.config.yaml"
    if not cfg_path.exists():
        sys.stderr.write(
            f"Config not found: {cfg_path}\n"
            "Copy newsletter.config.example.yaml to newsletter.config.yaml and edit it.\n"
        )
        sys.exit(1)
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if not isinstance(cfg, dict):
        sys.stderr.write(f"Config is not a mapping: {cfg_path}\n")
        sys.exit(1)
    return cfg


def slugify(text: str, *, max_len: int = 60) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text).strip("-")
    return text[:max_len].strip("-") or "issue"


# --- Claude API ------------------------------------------------------------

def anthropic_client():
    """Return a configured anthropic.Anthropic client.

    Reads ANTHROPIC_API_KEY from .env (or any credential source the SDK supports).
    """
    load_env()
    try:
        import anthropic
    except ImportError:
        sys.stderr.write("anthropic not installed. Run: pip install -r requirements.txt\n")
        raise
    if not os.getenv("ANTHROPIC_API_KEY"):
        sys.stderr.write(
            "ANTHROPIC_API_KEY is not set. Add it to .env (see .env.example).\n"
        )
        sys.exit(1)
    return anthropic.Anthropic()


def model_id(cfg: dict | None = None) -> str:
    """Which model to use: --model flag handling is left to callers; this checks
    the config's research.model, then $NEWSLETTER_MODEL, then the built-in default.
    """
    if cfg:
        m = (cfg.get("research") or {}).get("model")
        if m:
            return str(m)
    return env("NEWSLETTER_MODEL") or DEFAULT_MODEL


_JSON_FENCE = re.compile(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", re.DOTALL)


def extract_json(text: str):
    """Pull the first JSON object/array out of an LLM reply.

    Tries a fenced ```json block first, then the first balanced {...} / [...].
    Raises ValueError with the raw text if nothing parses.
    """
    m = _JSON_FENCE.search(text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # Fall back to the first balanced brace/bracket run.
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(text)):
            c = text[i]
            if c == opener:
                depth += 1
            elif c == closer:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        break
    raise ValueError(f"No parseable JSON found in model reply:\n{text[:2000]}")


def message_text(response) -> str:
    """Join all text blocks of a Messages API response."""
    return "".join(b.text for b in response.content if getattr(b, "type", None) == "text")


def run_messages(client, *, model: str, prompt: str, max_tokens: int = 16000,
                 tools: list | None = None, system: str | None = None) -> str:
    """messages.create with pause_turn handling. Returns joined text.

    pause_turn happens on long server-tool (web search) turns; resume by
    resending with the partial assistant content appended.
    """
    messages = [{"role": "user", "content": prompt}]
    kwargs = {"model": model, "max_tokens": max_tokens, "messages": messages}
    if tools:
        kwargs["tools"] = tools
    if system:
        kwargs["system"] = system
    for _ in range(10):
        response = client.messages.create(**kwargs)
        if response.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": response.content})
            continue
        if response.stop_reason == "refusal":
            details = getattr(response, "stop_details", None)
            raise RuntimeError(f"Model refused the request: {details}")
        return message_text(response)
    raise RuntimeError("Too many pause_turn iterations without completion")
