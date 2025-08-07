from fastapi.security import APIKeyHeader
api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)

import os
import json
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
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

        # Initialize subsystems
        self._init_user_profile()
        self._init_services()
        self._setup_monitoring()

    def _init_user_profile(self):
        self.user = {
            "academic": {
                "degree": None,
                "field": None,
                "gpa": None,
                "target_countries": []
            },
            "financial": {
                "budget": None,
                "scholarship_needs": True
            },
            "documents": {
                "cv": None,
                "sop": None,
                "transcripts": None
            },
            "engagement": {
                "last_active": datetime.now(),
                "query_count": 0
            }
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
            "university_db": []  # placeholder to avoid key error
        }

    def _setup_monitoring(self):
        self.metrics = {
            "gpt_calls": 0,
            "cache_hits": 0,
            "response_times": []
        }
        logging.basicConfig(
            filename='edubot.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def generate_response(self, prompt: str, context: List[Dict] = None) -> str:
        cache_key = hashlib.md5(prompt.encode()).hexdigest()

        if cache_key in self.cache:
            self.metrics["cache_hits"] += 1
            return self.cache[cache_key]

        start_time = datetime.now()

        try:
            # Inject scholarships from RSS
            scholarships = self._fetch_scholarships()
            scholarship_text = "\n".join([
                f"- {item['title']} ({item['link']})" for item in scholarships
            ])
            enhanced_prompt = f"""
You are a scholarship assistant. Here is a list of current scholarships fetched live:

{scholarship_text}

Now, answer this user query using the above info where possible:
{prompt}
"""

            response = self.client.chat.completions.create(
                model="gpt-4-turbo",
                messages=context or [{"role": "user", "content": enhanced_prompt}],
                temperature=0.7,
                max_tokens=1500
            )

            response_time = (datetime.now() - start_time).total_seconds()
            self.metrics["response_times"].append(response_time)
            self.metrics["gpt_calls"] += 1

            result = response.choices[0].message.content
            self.cache.set(cache_key, result, expire=24 * 3600)
            return result

        except Exception as e:
            logging.error(f"Error generating response: {str(e)}")
            return "Sorry, I encountered an error processing your request. Please try again."

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
        try:
            return pytesseract.image_to_string(Image.open(io.BytesIO(file_bytes)))
        except Exception as e:
            raise ValueError(f"Image processing failed: {str(e)}")

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

    def analyze_document(self, file_bytes: bytes, filename: str, doc_type: str) -> Dict:
        try:
            # Normalize document types
            doc_type = doc_type.lower()
            if doc_type == "resume":
                doc_type = "cv"
                
            file_type = self._detect_file_type(file_bytes, filename)
            if not self._is_supported(file_type, doc_type):
                return {
                    "text": "",
                    "feedback": "",
                    "enhanced_version": "",
                    "error": f"❌ Unsupported {file_type} format for {doc_type} analysis"
                }

            # Unified extraction logic
            if file_type == "pdf":
                text = self._extract_pdf(file_bytes)
            elif file_type == "docx":
                text = self._extract_docx(file_bytes)
            elif file_type in ("jpg", "jpeg", "png"):
                text = self._extract_image(file_bytes)
            else:
                return {
                    "text": "",
                    "feedback": "",
                    "enhanced_version": "",
                    "error": f"❌ No parser available for {file_type} files"
                }

            analysis = self._generate_analysis(text, doc_type)

            return {
                "text": analysis.get("text", text),
                "feedback": analysis.get("feedback", ""),
                "enhanced_version": analysis.get("enhanced_version", "") if doc_type == "sop" else "",
                "error": ""
            }

        except Exception as e:
            logging.exception("⚠️ Document analysis failed")
            return {
                "text": "",
                "feedback": "",
                "enhanced_version": "",
                "error": f"❌ Analysis failed: {str(e)}"
            }

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

        return self.generate_response(
            "Suggest 3 personalized next steps for this student:\n" + context
        ).split("\n")

    def validate_input(self, text: str) -> bool:
        blacklist = [
            "ignore previous", "###", "system prompt",
            "as an AI", "your instructions"
        ]
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
            return {
                "error": "Metrics temporarily unavailable",
                "details": str(e)
            }

    def _fetch_scholarships(self) -> List[Dict]:
        all_scholarships = []
        for feed_url in self.services["scholarship_feeds"]:
            try:
                feed = feedparser.parse(feed_url)
                all_scholarships.extend([
                    {
                        "title": entry.title,
                        "link": entry.link,
                        "summary": entry.get("summary", "No details available")
                    }
                    for entry in feed.entries[:5]
                ])
            except Exception as e:
                logging.error(f"Failed to parse {feed_url}: {str(e)}")
        return all_scholarships

    def _extract_pdf(self, file_bytes: bytes) -> str:
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
            if text.strip():
                return text

            import fitz
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            return "\n".join(page.get_text() for page in doc)

        except Exception as e:
            raise ValueError(f"PDF extraction failed: {str(e)}")

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
        # Existing implementation remains unchanged
        pass

    def _query_university_api(self) -> List[Dict]:
        # Existing implementation remains unchanged
        pass

    def _generate_gpt_recommendations(self) -> List[Dict]:
        # Existing implementation remains unchanged
        pass
