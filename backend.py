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

class EduBot:
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
        """Next-gen user context tracking"""
        self.user = {
            "academic": {
                "degree": None,  # Bachelor's, Master's, PhD
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
        """Microservices architecture"""
        self.services = {
            "university_db": self._load_university_database(),
            "scholarship_feeds": [
                "https://scholarshipscorner.website/feed/",
                "https://scholarshipunion.com/feed/"
            ],
            "apis": {
                "universities": "http://universities.hipolabs.com/search",
                "ranking": "https://edurank.org/api/unis.json"
            }
        }

    def _setup_monitoring(self):
        """Real-time performance tracking"""
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

    # --- Core AI Engine ---
    def generate_response(self, prompt: str, context: List[Dict] = None) -> str:
        """Advanced response generation with hybrid caching"""
        cache_key = hashlib.md5(prompt.encode()).hexdigest()
        
        if cache_key in self.cache:
            self.metrics["cache_hits"] += 1
            return self.cache[cache_key]
        
        start_time = datetime.now()
        response = self.client.chat.completions.create(
            model="gpt-4-turbo",
            messages=context or [{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1500
        )
        
        self.metrics["gpt_calls"] += 1
        self.metrics["response_times"].append((datetime.now() - start_time).total_seconds())
        
        result = response.choices[0].message.content
        self.cache.set(cache_key, result, expire=timedelta(hours=24))
        return result

    # --- University Intelligence ---
    def find_universities(self) -> Dict:
        """3-tier university discovery system"""
        # 1. Check local database
        local_results = self._query_local_db()
        if local_results:
            return {"source": "local_db", "data": local_results}
        
        # 2. Try external APIs
        api_results = self._query_university_api()
        if api_results:
            return {"source": "api", "data": api_results}
        
        # 3. GPT-4 fallback
        gpt_results = self._generate_gpt_recommendations()
        return {"source": "gpt", "data": gpt_results}

    def _query_local_db(self) -> Optional[List]:
        """Query optimized local dataset"""
        return [uni for uni in self.services["university_db"] 
                if uni["country"] in self.user["academic"]["target_countries"]
                and self.user["academic"]["field"].lower() in uni["programs"]]

    # --- Document Analysis Suite ---
    def analyze_document(self, file: bytes, doc_type: str) -> Dict:
        """Multi-format document intelligence"""
        analysis = {
            "text": self._extract_text(file, doc_type),
            "feedback": None,
            "enhanced_version": None
        }
        
        analysis["feedback"] = self.generate_response(
            f"Provide career-focused analysis of this {doc_type}:\n{analysis['text']}\n"
            "Focus on:\n1. Keyword optimization\n2. Structure improvements\n3. ATS compatibility"
        )
        
        if doc_type == "sop":
            analysis["enhanced_version"] = self._enhance_sop(analysis["text"])
        
        return analysis

    def _extract_text(self, file: bytes, doc_type: str) -> str:
        """Universal text extractor"""
        if doc_type == "pdf":
            with pdfplumber.open(file) as pdf:
                return "\n".join([page.extract_text() for page in pdf.pages])
        elif doc_type in ["jpg", "png"]:
            return pytesseract.image_to_string(Image.open(file))
        else:
            raise ValueError("Unsupported format")

    # --- Scholarship Engine ---
    def find_scholarships(self, query: str = None) -> List[Dict]:
        """Semantic scholarship matching"""
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

    # --- Proactive Engagement System ---
    def suggest_next_steps(self) -> List[str]:
        """AI-powered action recommendations"""
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

    # --- Security Layer ---
    def validate_input(self, text: str) -> bool:
        """Advanced injection protection"""
        blacklist = [
            "ignore previous", "###", "system prompt", 
            "as an AI", "your instructions"
        ]
        return not any(phrase in text.lower() for phrase in blacklist)

    # --- Monitoring Endpoints ---
    def get_metrics(self) -> Dict:
        """Real-time performance analytics"""
        return {
            "gpt_calls": self.metrics["gpt_calls"],
            "cache_hit_rate": f"{(self.metrics['cache_hits']/max(1, self.metrics['gpt_calls']))*100:.2f}%",
            "avg_response_time": f"{np.mean(self.metrics['response_times']):.2f}s"
        }

# --- Supporting Functions ---
def _load_university_database():
    """Load optimized university dataset"""
    try:
        with open("data/universities.json") as f:
            return json.load(f)
    except FileNotFoundError:
        logging.warning("Local university database not found")
        return []

def _fetch_scholarships():
    """Multi-source scholarship aggregator"""
    all_scholarships = []
    for feed_url in self.services["scholarship_feeds"]:
        try:
            feed = feedparser.parse(feed_url)
            all_scholarships.extend([
                {
                    "title": entry.title,
                    "link": entry.link,
                    "deadline": entry.get("deadline", ""),
                    "amount": entry.get("amount", "Not specified")
                }
                for entry in feed.entries[:10]  # Limit per feed
            ])
        except Exception as e:
            logging.error(f"Failed to parse {feed_url}: {str(e)}")
    return all_scholarships

