from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


def now_slug() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def safe_filename(name: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")
    return clean or "rfp_analysis"


def truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 120] + "\n\n[... truncated for model context ...]\n"


def extract_json(text: str) -> dict[str, Any]:
    """Best-effort parser for model JSON output."""
    if not text:
        return {}
    text = text.strip()
    # Direct parse first
    try:
        return json.loads(text)
    except Exception:
        pass
    # Strip fenced code blocks
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        try:
            return json.loads(fenced.group(1).strip())
        except Exception:
            pass
    # Extract largest JSON object
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        snippet = text[start : end + 1]
        try:
            return json.loads(snippet)
        except Exception:
            # Remove trailing commas often produced by LLMs
            snippet = re.sub(r",\s*([}\]])", r"\1", snippet)
            try:
                return json.loads(snippet)
            except Exception:
                return {"raw_text": text}
    return {"raw_text": text}


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
