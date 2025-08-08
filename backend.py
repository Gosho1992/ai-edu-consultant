from fastapi.security import APIKeyHeader
api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)
from parse_uploaded_file import parse_uploaded_file

import os
import json
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from fastapi import HTTPException, Security
from dotenv import load_dotenv
from openai import OpenAI
from sentence_transformers import SentenceTransformer
from diskcache import Cache
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import pytesseract
from PIL import Image
import pdfplumber
import requests
from bs4 import BeautifulSoup
import feedparser
import io
import magic
from typing import Dict, Union
from pathlib import Path
from docx import Document

# Configure Tesseract path
if os.name == 'nt':  # Windows
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
else:  # Linux/Mac
    pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

# --- Configuration ---
load_dotenv()
API_KEY_NAME = "X-API-KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

class SecurityManager:
    @staticmethod
    def validate_api_key(api_key: str = Security(api_key_header)):
        if api_key != os.getenv("API_KEY"):
            raise HTTPException(403, "Invalid API key")
        return True

class EducationAgent:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.cache = Cache("edubot_cache")
        self.security = SecurityManager()
        self._init_user_profile()
        self._init_services()
        self._setup_monitoring()

    def _init_user_profile(self):
        self.user = {
            "academic": {"degree": None, "field": None, "gpa": None, "target_countries": []},
            "financial": {"budget": None, "scholarship_needs": True},
            "documents": {"cv": None, "sop": None, "transcripts": None},
            "engagement": {"last_active": datetime.now(), "query_count": 0}
        }

    def _init_services(self):
        self.services = {
            "scholarship_feeds": [
                "https://scholarshipscorner.website/feed/",
                "https://scholarshipunion.com/feed/"
            ],
            "apis": {
                "universities": "http://universities.hipolabs.com/search",
                "ranking": "https://edurank.org/api/unis.json"
            },
            "university_db": []
        }

    def _setup_monitoring(self):
        self.metrics = {"gpt_calls": 0, "cache_hits": 0, "response_times": []}
        logging.basicConfig(filename='edubot.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    def _get_mime_type(self, file_bytes: bytes) -> str:
        return magic.from_buffer(file_bytes, mime=True)

    def _validate_file(self, file_bytes: bytes) -> bool:
        if not file_bytes:
            return False
        if len(file_bytes) > 200 * 1024 * 1024:
            return False
        return True

    def analyze_url(self, url: str) -> Dict:
        try:
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            text = ' '.join([p.get_text() for p in soup.find_all('p')])
            return {"text": text, "source": url, "error": ""}
        except Exception as e:
            return {"text": "", "source": url, "error": f"❌ URL analysis failed: {str(e)}"}

    def _detect_file_type(self, file_bytes: bytes, filename: str) -> str:
        try:
            mime = magic.from_buffer(file_bytes, mime=True)
            ext = Path(filename).suffix[1:].lower()
            type_map = {
                "application/pdf": "pdf",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
                "image/jpeg": "jpg",
                "image/jpg": "jpg",
                "image/png": "png",
                "text/plain": "txt"
            }
            return type_map.get(mime, ext)
        except Exception as e:
            logging.error(f"File type detection failed: {str(e)}")
            return Path(filename).suffix[1:].lower()

    def _extract_pdf(self, file_bytes: bytes) -> str:
        try:
            text = ""
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            logging.error(f"PDF extraction failed: {str(e)}")
            raise

    def _extract_docx(self, file_bytes: bytes) -> str:
        try:
            doc = Document(io.BytesIO(file_bytes))
            return "\n".join(para.text for para in doc.paragraphs)
        except Exception as e:
            logging.error(f"DOCX extraction failed: {str(e)}")
            raise

    def _is_supported(self, file_type: str, doc_type: str) -> bool:
        supported_types = {
            "sop": {"pdf", "docx", "jpg", "png"},
            "cv": {"pdf", "docx"},
            "transcript": {"pdf", "jpg", "png"}
        }
        return file_type in supported_types.get(doc_type.lower(), set())

    def analyze_document(self, file_bytes: bytes, filename: str, doc_type: str) -> Dict:
        try:
            logging.info(f"Analyzing document: {filename}, type: {doc_type}")

            # Validate file
            if not self._validate_file(file_bytes):
                return {"error": "❌ Invalid file (empty or >200MB)"}

            # Detect file type
            file_type = self._detect_file_type(file_bytes, filename)
            logging.info(f"Detected file type: {file_type} for {filename}")

            # Normalize doc type
            doc_type = "cv" if doc_type in ["resume", "cv"] else doc_type
            
            # Check support
            if not self._is_supported(file_type, doc_type):
                return {"error": f"❌ Unsupported {file_type} format for {doc_type}"}

            # Extract text based on file type
            if file_type == "pdf":
                text = self._extract_pdf(file_bytes)
            elif file_type == "docx":
                text = self._extract_docx(file_bytes)
            elif file_type in ["jpg", "jpeg", "png"]:
                text = pytesseract.image_to_string(Image.open(io.BytesIO(file_bytes)))
            elif file_type == "txt":
                text = file_bytes.decode("utf-8")
            else:
                return {"error": f"❌ Unsupported file type: {file_type}"}
            
            if not text.strip():
                return {"error": "❌ Extracted text is empty"}

            # Generate analysis
            return self._generate_analysis(text, doc_type)

        except Exception as e:
            logging.exception(f"Document analysis failed: {str(e)}")
            return {"error": f"❌ Analysis failed: {str(e)}"}

    def _generate_analysis(self, text: str, doc_type: str) -> Dict:
        try:
            # Truncate text intelligently
            max_chars = 3000 if doc_type in ["sop", "cv"] else 1000
            text = text[:max_chars].strip() + "..." if len(text) > max_chars else text

            # Prepare for GPT processing
            system_msg = f"Provide feedback and improvements for this {doc_type} in JSON format"
            user_msg = json.dumps({"text": text})
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model="gpt-4-turbo",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg}
                ],
                temperature=0.5,
                max_tokens=1000
            )
            
            # Parse response
            analysis = json.loads(response.choices[0].message.content)
            return {
                "text": text,
                "feedback": analysis.get("feedback", ""),
                "enhanced_version": analysis.get("enhanced_version", "")
            }

        except Exception as e:
            logging.exception("Analysis generation failed")
            return {
                "text": text,
                "feedback": "Analysis failed",
                "enhanced_version": "",
                "error": str(e)
            }

    # ... (rest of your existing methods remain unchanged)

    def find_universities(self) -> Dict:
        try:
            local_results = self._query_local_db()
            if local_results:
                return {"source": "local_db", "data": local_results}
            api_results = self._query_university_api()
            if api_results:
                return {"source": "api", "data": api_results}
            gpt_results = self._generate_gpt_recommendations()
            return {"source": "gpt", "data": gpt_results}
        except Exception as e:
            logging.error(f"University search failed: {str(e)}")
            return {"source": "error", "data": "Unable to fetch university information at this time"}

    def _query_local_db(self) -> Optional[List]:
        return [uni for uni in self.services["university_db"]
                if uni["country"] in self.user["academic"]["target_countries"]
                and self.user["academic"]["field"].lower() in uni["programs"]]

    def _extract_image(self, file_bytes: bytes) -> str:
        return parse_uploaded_file(file_bytes, "image/png")

    def _detect_file_type(self, file_bytes: bytes, filename: str) -> str:
        try:
            mime = magic.from_buffer(file_bytes, mime=True)
            ext = Path(filename).suffix[1:].lower()
            type_map = {
                "application/pdf": "pdf",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
                "image/jpeg": "jpg",
                "image/jpg": "jpg",
                "image/png": "png",
                "text/plain": "txt"
            }
            return type_map.get(mime, ext)
        except:
            return Path(filename).suffix[1:].lower()

    def _extract_pdf(self, file_bytes: bytes) -> str:
        return parse_uploaded_file(file_bytes, "application/pdf")

    def _extract_text(self, file: bytes, doc_type: str) -> str:
        try:
            if doc_type == "pdf":
                return self._extract_pdf(file)
            elif doc_type == "docx":
                return self._extract_docx(file)
            elif doc_type in ["jpg", "jpeg", "png"]:
                return pytesseract.image_to_string(Image.open(io.BytesIO(file)))
            elif doc_type == "txt":
                return file.decode("utf-8")
            else:
                raise ValueError(f"Unsupported format: {doc_type}")
        except Exception as e:
            logging.error(f"Extraction failed for {doc_type}: {str(e)}")
            raise

    def find_scholarships(self, query: str = None) -> List[Dict]:
        all_scholarships = self._fetch_scholarships()
        if query:
            query_embed = self.embedding_model.encode(query)
            scholarships_with_scores = []
            for scholarship in all_scholarships:
                title_embed = self.embedding_model.encode(scholarship["title"])
                score = cosine_similarity([query_embed], [title_embed])[0][0]
                scholarships_with_scores.append((scholarship, score))
            return sorted(scholarships_with_scores, key=lambda x: x[1], reverse=True)[:5]
        return all_scholarships[:10]

    def suggest_next_steps(self) -> List[str]:
        context = f"""
User Profile:
- Degree: {self.user['academic']['degree']}
- Field: {self.user['academic']['field']}
- Target Countries: {self.user['academic']['target_countries']}
Documents Uploaded: {len(self.user['documents'].keys())}
"""
        return self.generate_response("Suggest 3 personalized next steps for this student:\n" + context).split("\n")

    def validate_input(self, text: str) -> bool:
        blacklist = ["ignore previous", "###", "system prompt", "as an AI", "your instructions"]
        return not any(phrase in text.lower() for phrase in blacklist)

    def get_metrics(self) -> Dict:
        try:
            avg_time = 0.0
            if self.metrics["response_times"]:
                avg_time = np.mean(self.metrics["response_times"])
            return {
                "gpt_calls": self.metrics["gpt_calls"],
                "cache_hit_rate": f"{(self.metrics['cache_hits']/max(1, self.metrics['gpt_calls']))*100:.2f}%",
                "avg_response_time": f"{avg_time:.2f}s",
                "total_queries": self.user["engagement"]["query_count"]
            }
        except Exception as e:
            logging.error(f"Metrics generation failed: {str(e)}")
            return {"error": "Metrics temporarily unavailable", "details": str(e)}

    def _fetch_scholarships(self) -> List[Dict]:
        all_scholarships = []
        for feed_url in self.services["scholarship_feeds"]:
            try:
                feed = feedparser.parse(feed_url)
                all_scholarships.extend([
                    {"title": entry.title, "link": entry.link, "summary": entry.get("summary", "No details available")}
                    for entry in feed.entries[:5]
                ])
            except Exception as e:
                logging.error(f"Failed to parse {feed_url}: {str(e)}")
        return all_scholarships

    def _extract_docx(self, file_bytes: bytes) -> str:
        try:
            from docx import Document
            doc = Document(io.BytesIO(file_bytes))
            return "\n".join(para.text for para in doc.paragraphs)
        except Exception as e:
            raise ValueError(f"DOCX extraction failed: {str(e)}")

    def _is_supported(self, file_type: str, doc_type: str) -> bool:
        supported_types = {
            "sop": {"pdf", "docx", "jpg", "png"},
            "cv": {"pdf", "docx"},
            "transcript": {"pdf", "jpg", "png"}
        }
        return file_type in supported_types.get(doc_type.lower(), set())

    def _generate_analysis(self, text: str, doc_type: str) -> Dict:
        try:
            import tiktoken
            from openai import OpenAI

            max_chars = 3000 if doc_type in ["sop", "resume", "cv"] else 1000
            text = text.strip()[:max_chars]

            system_msg = f"You are a helpful assistant reviewing a {doc_type}. Provide feedback and improve it."
            user_msg = f"Here is the extracted text of the {doc_type}:\n\n{text}\n\nPlease provide:\n1. A short feedback for improvement.\n2. A rewritten professional version of it."

            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            completion = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg}
                ],
                temperature=0.7,
                max_tokens=800
            )

            ai_output = completion.choices[0].message.content

            if "2." in ai_output:
                feedback_part, enhanced_part = ai_output.split("2.", 1)
                feedback = feedback_part.replace("1.", "").strip()
                enhanced = enhanced_part.strip()
            else:
                feedback = "Could not separate feedback and rewrite."
                enhanced = ai_output

            return {
                "text": text,
                "feedback": feedback,
                "enhanced_version": enhanced
            }

        except Exception as e:
            logging.exception("Error in _generate_analysis")
            return {
                "text": text,
                "feedback": "Analysis failed.",
                "enhanced_version": None,
                "error": str(e)
            }

    def _query_university_api(self) -> List[Dict]:
        pass

    def _generate_gpt_recommendations(self) -> List[Dict]:
        pass




