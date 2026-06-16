from __future__ import annotations

import tempfile
from pathlib import Path
from src.document_loader import load_path

def test_load_txt_file():
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w", encoding="utf-8") as tmp:
        tmp.write("This is a mock RFP details page. Scope includes database caching and API endpoints.")
        tmp_name = tmp.name
        
    try:
        doc = load_path(tmp_name)
        assert doc.name == Path(tmp_name).name
        assert "mock RFP details" in doc.text
        assert len(doc.pages) == 1
    finally:
        Path(tmp_name).unlink(missing_ok=True)
