from __future__ import annotations

import tempfile
from pathlib import Path
from src.ocr import extract_ocr_text

def test_ocr_graceful_handling():
    # Calling OCR on an arbitrary file or mock path should return a string warning 
    # instead of crashing, even if system binaries are missing.
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(b"Mock scanned text image bytes")
        tmp_name = tmp.name
        
    try:
        res = extract_ocr_text(tmp_name)
        assert isinstance(res, str)
        # Verify it contains standard system notifications or warnings, not crashing
        assert "OCR" in res or "Warning" in res or "Notice" in res
    finally:
        Path(tmp_name).unlink(missing_ok=True)
