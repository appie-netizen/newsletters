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
    # utf-8-sig tolerates a BOM (some Windows editors add one).
    with open(path, "r", encoding="utf-8-sig") as f:
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


# --- LLM providers -------------------------------------------------------
#
# Two backends, same job:
#   anthropic -> claude-* models, web_search server tool  (needs ANTHROPIC_API_KEY)
#   gemini    -> gemini-* models, google_search grounding (needs GEMINI_API_KEY,
#               free at https://aistudio.google.com)
#
# generate(provider, model, prompt, grounded=...) returns the reply text.

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_GEMINI_IMAGE_MODEL = "gemini-2.5-flash-image"


def resolve_provider(cli_value: str | None = None, cfg: dict | None = None) -> str:
    """Pick the LLM backend: --provider flag > $NEWSLETTER_PROVIDER > config
    research.provider > autodetect from which API key is set > 'anthropic'.
    """
    load_env()
    val = (
        cli_value
        or env("NEWSLETTER_PROVIDER")
        or (cfg or {}).get("research", {}).get("provider")
    )
    if val:
        val = str(val).lower()
        if val not in ("anthropic", "gemini"):
            sys.stderr.write(f"Unknown provider: {val!r} (use 'anthropic' or 'gemini')\n")
            sys.exit(1)
        return val
    if os.getenv("GEMINI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        return "gemini"
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    sys.stderr.write(
        "No LLM credentials found. Set GEMINI_API_KEY (free: https://aistudio.google.com) "
        "or ANTHROPIC_API_KEY in .env.\n"
    )
    sys.exit(1)


def model_id(provider: str, cfg: dict | None = None, override: str | None = None) -> str:
    """Which model to use for the given provider."""
    if override:
        return override
    cfg_model = (cfg or {}).get("research", {}).get("model")
    if provider == "gemini":
        return env("GEMINI_MODEL") or cfg_model or DEFAULT_GEMINI_MODEL
    return env("NEWSLETTER_MODEL") or cfg_model or DEFAULT_MODEL


def anthropic_client():
    """Return a configured anthropic.Anthropic client."""
    load_env()
    try:
        import anthropic
    except ImportError:
        sys.stderr.write("anthropic not installed. Run: pip install -r requirements.txt\n")
        raise
    if not os.getenv("ANTHROPIC_API_KEY"):
        sys.stderr.write("ANTHROPIC_API_KEY is not set. Add it to .env.\n")
        sys.exit(1)
    return anthropic.Anthropic()


def gemini_client():
    """Return a configured google.genai Client (reads GEMINI_API_KEY)."""
    load_env()
    try:
        from google import genai
    except ImportError:
        sys.stderr.write("google-genai not installed. Run: pip install -r requirements.txt\n")
        raise
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        sys.stderr.write(
            "GEMINI_API_KEY is not set. Get a free key at https://aistudio.google.com "
            "and add it to .env.\n"
        )
        sys.exit(1)
    return genai.Client(api_key=key)


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


def _message_text(response) -> str:
    return "".join(b.text for b in response.content if getattr(b, "type", None) == "text")


ANTHROPIC_WEB_SEARCH = env("WEB_SEARCH_TOOL_TYPE") or "web_search_20260209"
ANTHROPIC_WEB_SEARCH_FALLBACK = "web_search_20250305"


def _anthropic_generate(model: str, prompt: str, *, grounded: bool, max_tokens: int) -> str:
    client = anthropic_client()

    def once(tool_type: str | None) -> str:
        messages = [{"role": "user", "content": prompt}]
        kwargs = {"model": model, "max_tokens": max_tokens, "messages": messages}
        if tool_type:
            kwargs["tools"] = [{"type": tool_type, "name": "web_search", "max_uses": 8}]
        for _ in range(10):
            resp = client.messages.create(**kwargs)
            if resp.stop_reason == "pause_turn":
                messages.append({"role": "assistant", "content": resp.content})
                continue
            if resp.stop_reason == "refusal":
                raise RuntimeError(f"Model refused: {getattr(resp, 'stop_details', None)}")
            return _message_text(resp)
        raise RuntimeError("too many pause_turn iterations")

    if not grounded:
        return once(None)
    try:
        return once(ANTHROPIC_WEB_SEARCH)
    except Exception as e:  # noqa: BLE001 - retry once with the basic tool variant
        if any(s in str(e).lower() for s in ("web_search", "tool", "400")):
            sys.stderr.write(f"[anthropic] {ANTHROPIC_WEB_SEARCH} rejected ({e}); retrying basic\n")
            return once(ANTHROPIC_WEB_SEARCH_FALLBACK)
        raise


def _gemini_generate(model: str, prompt: str, *, grounded: bool, max_tokens: int) -> str:
    from google.genai import types

    client = gemini_client()
    # Gemini 2.5 spends part of the output budget on hidden "thinking"; give it
    # generous headroom so the actual answer isn't truncated.
    cfg_kwargs = {"max_output_tokens": max(max_tokens, 32000)}
    if grounded:
        cfg_kwargs["tools"] = [types.Tool(google_search=types.GoogleSearch())]
    resp = client.models.generate_content(
        model=model, contents=prompt,
        config=types.GenerateContentConfig(**cfg_kwargs),
    )
    text = getattr(resp, "text", None)
    if not text:
        reason = getattr(getattr(resp, "candidates", [None])[0], "finish_reason", "?")
        raise RuntimeError(f"Gemini returned no text (finish_reason={reason})")
    return text


def generate(provider: str, model: str, prompt: str, *,
             grounded: bool = False, max_tokens: int = 16000) -> str:
    """Run a prompt through the chosen backend; return the reply text.

    grounded=True enables web search (Anthropic) / Google Search grounding (Gemini).
    """
    if provider == "gemini":
        return _gemini_generate(model, prompt, grounded=grounded, max_tokens=max_tokens)
    return _anthropic_generate(model, prompt, grounded=grounded, max_tokens=max_tokens)
