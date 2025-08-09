# backend.py — cleaned, Streamlit-safe

import os
import io
import json
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

# Optional deps (guarded)
try:
    import pdfplumber
except Exception:
    pdfplumber = None

try:
    from docx import Document
except Exception:
    Document = None

try:
    from PIL import Image
    import pytesseract
except Exception:
    Image = None
    pytesseract = None

try:
    import magic as _magic
except Exception:
    _magic = None

try:
    import feedparser
except Exception:
    feedparser = None

try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
except Exception:
    SentenceTransformer = None
    cosine_similarity = None
    np = None

# OpenAI client (guarded)
try:
    from openai import OpenAI
    _OPENAI_KEY = os.getenv("OPENAI_API_KEY")
    _client = OpenAI(api_key=_OPENAI_KEY) if _OPENAI_KEY else None
except Exception:
    _client = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class EducationAgent:
    def __init__(self):
        self.client = _client
        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2") if SentenceTransformer else None
        self.services = {
            "scholarship_feeds": [
                "https://scholarshipscorner.website/feed/",
                "https://scholarshipunion.com/feed/",
            ],
            "university_db": [],
        }
        self.metrics = {"gpt_calls": 0, "response_times": [], "cache_hits": 0}

    # -------------------- Public: chat --------------------
    def generate_response(self, prompt: str, context: List[Dict] = None) -> str:
        if self.client:
            try:
                resp = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a concise, helpful education assistant."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.4,
                )
                self.metrics["gpt_calls"] += 1
                return resp.choices[0].message.content
            except Exception:
                pass
        # Fallback
        return "I’m here to help. Share your degree, country preference, GPA, and budget, and I’ll suggest programs & scholarships."

    # -------------------- Public: document analysis --------------------
    def analyze_document(
        self,
        file_bytes: bytes,
        filename: str,
        doc_type: str,
        purpose: Optional[str] = None,
        extra_context: Optional[str] = None,
    ) -> Dict:
        try:
            if not self._validate_file(file_bytes):
                return self._err("❌ Invalid file (empty or >200MB)")

            # Normalize doc type
            doc_type = (doc_type or "").strip().lower()
            if doc_type == "resume":
                doc_type = "cv"

            ftype = self._detect_file_type(file_bytes, filename)
            if not self._is_supported(ftype, doc_type):
                return self._err(f"❌ Unsupported {ftype} format for {doc_type} analysis")

            text = self._extract_text(file_bytes, ftype)
            if not text.strip():
                return self._err("❌ Extracted text is empty")

            feedback, enhanced, issues = self._review(text, doc_type, purpose, extra_context)

            return {
                "text": text,
                "feedback": feedback,
                "enhanced_version": enhanced,
                "issues": issues,
                "error": "",
            }
        except Exception as e:
            logging.exception("analyze_document failed")
            return self._err(f"❌ Analysis failed: {str(e)}", text="")

    # -------------------- Internal helpers --------------------
    def _validate_file(self, file_bytes: bytes) -> bool:
        return bool(file_bytes) and len(file_bytes) <= 200 * 1024 * 1024

    def _detect_file_type(self, file_bytes: bytes, filename: str) -> str:
        # Prefer magic if present
        if _magic:
            try:
                mime = _magic.from_buffer(file_bytes, mime=True)
                map_ = {
                    "application/pdf": "pdf",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
                    "application/msword": "doc",
                    "image/jpeg": "jpg",
                    "image/png": "png",
                    "text/plain": "txt",
                }
                return map_.get(mime, (Path(filename).suffix[1:].lower() or "unknown"))
            except Exception:
                pass
        # Fallback: extension
        return Path(filename).suffix[1:].lower() or "unknown"

    def _is_supported(self, file_type: str, doc_type: str) -> bool:
        supported = {
            "sop": {"pdf", "docx", "jpg", "png", "txt"},
            "cv": {"pdf", "docx", "txt"},
            "transcript": {"pdf", "jpg", "png"},
            "motivation letter": {"pdf", "docx", "txt"},
        }
        return file_type in supported.get(doc_type, set())

    def _extract_text(self, file_bytes: bytes, file_type: str) -> str:
        if file_type == "txt":
            try:
                return file_bytes.decode("utf-8", errors="ignore")
            except Exception:
                return ""

        if file_type == "docx" and Document:
            doc = Document(io.BytesIO(file_bytes))
            return "\n".join(p.text for p in doc.paragraphs)

        if file_type == "pdf" and pdfplumber:
            parts = []
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for p in pdf.pages:
                    parts.append(p.extract_text() or "")
            return "\n".join(parts)

        if file_type in {"jpg", "png"} and Image and pytesseract:
            try:
                img = Image.open(io.BytesIO(file_bytes))
                return pytesseract.image_to_string(img)
            except Exception:
                return ""

        # Last resort
        try:
            return file_bytes.decode("utf-8", errors="ignore")
        except Exception:
            return ""

    def _review(self, text: str, doc_type: str, purpose: Optional[str], extra_context: Optional[str]):
        trimmed = text[:4000]
        purpose = (purpose or "").strip()
        extra = (extra_context or "").strip()

        if self.client:
            try:
                system_msg = (
                    "You are a precise, purpose-aware document reviewer. "
                    "Return a JSON object with keys: feedback, enhanced_version, issues "
                    "(issues is an array of {excerpt, issue, suggested_fix}). "
                    "Keep feedback actionable."
                )
                payload = {
                    "document_type": doc_type,
                    "purpose": purpose,
                    "extra_context": extra,
                    "text": trimmed,
                    "instructions": [
                        "Enhanced version must not invent credentials.",
                        "Issues array should have 3–10 entries.",
                    ],
                }
                resp = self.client.chat.completions.create(
                    model="gpt-4-turbo",
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                    ],
                    temperature=0.3,
                    max_tokens=1400,
                )
                self.metrics["gpt_calls"] += 1
                data = json.loads(resp.choices[0].message.content)
                issues = data.get("issues", [])
                if not isinstance(issues, list):
                    issues = []
                issues_norm = []
                for it in issues:
                    issues_norm.append({
                        "excerpt": (it or {}).get("excerpt", "")[:400],
                        "issue": (it or {}).get("issue", "")[:400],
                        "suggested_fix": (it or {}).get("suggested_fix", "")[:400],
                    })
                return data.get("feedback", ""), data.get("enhanced_version", ""), issues_norm
            except Exception:
                logging.exception("OpenAI review failed")

        # Fallback (no API key / error)
        fb = self._local_feedback(trimmed, doc_type, purpose, extra)
        enh = self._local_enhanced(trimmed)
        iss = self._local_issues(trimmed)
        return fb, enh, iss

    # -------------------- Local fallbacks --------------------
    def _local_feedback(self, text: str, doc_type: str, purpose: str, extra: str) -> str:
        bullets = []
        if doc_type in {"cv", "resume"}:
            bullets += [
                "Add a 2–3 line tailored summary at the top.",
                "Quantify achievements (%, $, time saved).",
                "Use consistent date format (MMM YYYY – MMM YYYY).",
            ]
            if purpose.lower().startswith("job"):
                bullets.append("Mirror 5–7 keywords from the job description to improve ATS matching.")
            if purpose.lower().startswith(("masters", "phd")):
                bullets.append("Highlight coursework/projects and any publications relevant to the program.")
        elif doc_type in {"sop", "motivation letter"}:
            bullets += [
                "Open with a crisp motivation hook.",
                "Use 2–3 concrete examples that prove readiness.",
                "Close with fit (why this program/lab) and clear goals.",
            ]
        else:
            bullets.append("Keep paragraphs short, remove filler, and improve headings.")
        if extra:
            bullets.append(f"Tailor to context provided: {extra[:120]}…")
        return "• " + "\n• ".join(bullets)

    def _local_enhanced(self, text: str) -> str:
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        sample = " ".join(lines[:6])[:900]
        return f"Rewritten (sample start): {sample}"

    def _local_issues(self, text: str) -> List[Dict]:
        out = []
        if len(text) < 200:
            out.append({"excerpt": text[:120], "issue": "Text is very short", "suggested_fix": "Add more detailed achievements and context."})
        if "lorem" in text.lower():
            out.append({"excerpt": "lorem …", "issue": "Placeholder text found", "suggested_fix": "Replace with real content and metrics."})
        return out

    # -------------------- Scholarships (used by generate_response) --------------------
    def _fetch_scholarships(self) -> List[Dict]:
        if not feedparser:
            return []
        items: List[Dict] = []
        for url in self.services["scholarship_feeds"]:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:5]:
                    items.append({"title": entry.title, "link": entry.link, "summary": entry.get("summary", "")})
            except Exception:
                logging.exception(f"Failed to parse feed: {url}")
        return items
