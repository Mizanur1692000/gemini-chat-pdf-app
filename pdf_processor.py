import pdfplumber
import pandas as pd
from typing import List, Dict

# Optional OCR fallback
try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


def extract_text_from_pdf(path: str, ocr_fallback: bool = False) -> List[Dict[str, str]]:
    """
    Extracts text per page from a PDF. Returns list of dicts: [{"page": i, "text": "..."}]
    If a page has no selectable text and ocr_fallback=True and OCR is available, uses OCR.
    """
    results = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            if not text.strip() and ocr_fallback and OCR_AVAILABLE:
                # Fallback to OCR
                pil_image = page.to_image(resolution=300).original
                text = pytesseract.image_to_string(pil_image)
            results.append({"page": str(i), "text": text.strip()})
    return results


def save_extracted_text_to_csv(extracted: List[Dict[str, str]], output_csv_path: str):
    """
    Saves the list of page texts to a CSV with columns: page, text.
    """
    df = pd.DataFrame(extracted)
    df.to_csv(output_csv_path, index=False, encoding="utf-8-sig")
