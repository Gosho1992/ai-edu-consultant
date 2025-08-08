# parse_uploaded_file.py

import io
from typing import Optional

import pdfplumber
from PIL import Image, UnidentifiedImageError
from docx import Document
import pytesseract


def _normalize_kind(file_type: str) -> str:
    """
    Normalize incoming file_type (MIME like 'application/pdf' or extension like 'pdf')
    into one of: 'pdf' | 'docx' | 'txt' | 'jpg' | 'png'.
    """
    if not file_type:
        return "unknown"

    ft = file_type.lower().strip()

    # MIME → simple kind
    mime_map = {
        "application/pdf": "pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "application/msword": "docx",  # treat legacy .doc as docx unsupported by this helper
        "text/plain": "txt",
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
        "image/png": "png",
    }
    if "/" in ft:
        return mime_map.get(ft, "unknown")

    # Extension → simple kind
    if ft.startswith("."):
        ft = ft[1:]
    if ft in {"pdf", "docx", "txt", "jpg", "jpeg", "png"}:
        return "jpg" if ft == "jpeg" else ft

    return "unknown"


def _extract_pdf(file_bytes: bytes) -> str:
    text_parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text: Optional[str] = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    text = "\n".join(text_parts).strip()
    if not text:
        # Common for scanned PDFs without embedded text
        raise ValueError("No extractable text found in PDF (likely a scanned PDF without OCR).")
    return text


def _extract_docx(file_bytes: bytes) -> str:
    doc = Document(io.BytesIO(file_bytes))
    return "\n".join(p.text for p in doc.paragraphs).strip()


def _extract_image(file_bytes: bytes) -> str:
    try:
        img = Image.open(io.BytesIO(file_bytes))
        # Let pytesseract use whatever language packs are installed; default is eng.
        return pytesseract.image_to_string(img).strip()
    except UnidentifiedImageError:
        raise ValueError("Invalid image data; unable to open image for OCR.")


def _extract_txt(file_bytes: bytes) -> str:
    return file_bytes.decode("utf-8", errors="ignore").strip()


def parse_uploaded_file(file_bytes: bytes, file_type: str) -> str:
    """
    Extract plain text from an uploaded file.

    Args:
        file_bytes: Raw bytes of the uploaded file.
        file_type: Either a MIME type (e.g., 'application/pdf', 'image/png')
                   or a file extension (e.g., 'pdf', 'docx', 'png').

    Returns:
        Extracted text as a string.

    Raises:
        ValueError: For unsupported type or when no text can be extracted.
    """
    if not file_bytes:
        raise ValueError("Empty file provided.")

    kind = _normalize_kind(file_type)

    if kind == "pdf":
        return _extract_pdf(file_bytes)
    if kind == "docx":
        return _extract_docx(file_bytes)
    if kind in {"jpg", "png"}:
        return _extract_image(file_bytes)
    if kind == "txt":
        return _extract_txt(file_bytes)

    raise ValueError(f"Unsupported file type for extraction: {file_type}")
