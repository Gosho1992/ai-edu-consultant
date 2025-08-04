import pytesseract
from PIL import Image
import pdfplumber
import io

def parse_uploaded_file(file_bytes: bytes, file_type: str) -> str:
    """Extract text from PDFs/Images"""
    if file_type == "application/pdf":
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            return "\n".join([page.extract_text() for page in pdf.pages])
    elif file_type.startswith("image/"):
        image = Image.open(io.BytesIO(file_bytes))
        return pytesseract.image_to_string(image)
    else:
        raise ValueError("Unsupported file type")