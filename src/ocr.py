from __future__ import annotations

import os
from pathlib import Path

def extract_ocr_text(file_path: str | Path) -> str:
    """Extract text from scanned PDFs or images using pytesseract.
    
    If libraries or system binaries are missing, it falls back to a warning.
    """
    file_path = Path(file_path)
    suffix = file_path.suffix.lower()
    
    try:
        import pytesseract
        from pdf2image import convert_from_path
        
        # Check if tesseract binary is available on system
        # Under Windows/Linux/Mac, verify calling pytesseract doesn't fail immediately
        try:
            pytesseract.get_tesseract_version()
        except Exception:
            return (
                f"[OCR Warning] pytesseract was imported, but the system Tesseract binary is not installed "
                f"or not found on PATH. Could not OCR-parse scanned file: {file_path.name}"
            )
            
        if suffix == ".pdf":
            pages = convert_from_path(str(file_path), dpi=150)
            text_parts = []
            for i, page_img in enumerate(pages, start=1):
                page_text = pytesseract.image_to_string(page_img)
                text_parts.append(f"\n\n--- OCR Page {i} ---\n{page_text}")
            return "".join(text_parts).strip()
            
        elif suffix in (".png", ".jpg", ".jpeg", ".tiff", ".bmp"):
            from PIL import Image
            img = Image.open(file_path)
            return pytesseract.image_to_string(img).strip()
            
        else:
            return f"[OCR Error] Unsupported OCR file type: {suffix}"
            
    except ImportError as e:
        return (
            f"[OCR System Notice] Scanned PDF/Image upload detected, but OCR libraries "
            f"(pytesseract and/or pdf2image) are not installed in the python environment. "
            f"Please run 'pip install pytesseract pdf2image pillow' to enable OCR text recovery."
        )
    except Exception as exc:
        return f"[OCR Ingestion Failure] Could not run OCR parser: {exc}"
