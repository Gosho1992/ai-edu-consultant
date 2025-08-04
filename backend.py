import os
import json
from typing import Dict, List
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime
import logging

from rss_fetcher import fetch_rss_scholarships
from document_parser import parse_uploaded_file
from url_analyzer import analyze_url_content

# Load env and initialize OpenAI
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class EducationAgent:
    def __init__(self):
        self.user_profile = {
            "degree": None,
            "field": None,
            "country": None,
            "gpa": None,
            "budget": None,
            "documents": []
        }
        self.conversation_history = []

    def _extract_profile(self, message: str) -> Dict:
        prompt = f"""
Extract education profile details from this message:
{message}

Fields:
- degree (Bachelor's, Master's, PhD)
- field_of_study
- country
- gpa (4.0 scale)
- budget (USD/year)

Return JSON.
"""
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)

    def _find_universities(self) -> str:
        if not all([self.user_profile["degree"], self.user_profile["field"], self.user_profile["country"]]):
            return "Please specify your degree, field of study, and target country first."

        prompt = f"""
Recommend 5 universities for:
- Degree: {self.user_profile["degree"]}
- Field: {self.user_profile["field"]}
- Country: {self.user_profile["country"]}
- GPA: {self.user_profile.get("gpa", "Not specified")}
- Budget: {self.user_profile.get("budget", "Not specified")} USD/year

Format:
1. [University Name] - [Program Name]
   • Features
   • Cost
   • [Admissions Link]
"""
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content

    def get_latest_scholarships(self, topic: str = "") -> str:
        items = fetch_rss_scholarships()
        if topic:
            items = [i for i in items if topic.lower() in i["title"].lower()]
        items = items[:5] if items else []

        if not items:
            return "❌ No recent scholarships found."

        return "\n".join([
            f"{i+1}. **{item['title']}**\n   - 📅 {item['published']}\n   - {item['summary']}\n   - 🔗 [View]({item['link']})"
            for i, item in enumerate(items)
        ])

    def analyze_document(self, file_bytes: bytes, file_type: str) -> str:
        """Process CV/Resume/SOPs"""
        extracted_text = parse_uploaded_file(file_bytes, file_type)
        self.user_profile["documents"].append(extracted_text)

        prompt = f"""
Analyze this document:
{extracted_text}

Focus:
1. Missing keywords
2. Length issues
3. Formatting fixes
"""

        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You're a career counselor. Give concise, structured feedback."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content

    def analyze_scholarship_url(self, url: str) -> str:
        """Summarize web scholarship pages"""
        page_content = analyze_url_content(url)

        prompt = f"""
Summarize this scholarship page:

{page_content}

Include:
- Eligibility
- Deadline
- Benefits
- 3 Action Steps
"""
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    def generate_essay_feedback(self, essay_text: str, purpose: str = "motivation letter") -> str:
        """Improve SOPs or Cover Letters"""
        prompt = f"""
Give feedback on this {purpose}:
{essay_text}

Focus:
1. Tone & structure
2. Grammar & clarity
3. Recommended improvements
"""

        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    def chat(self, message: str, attachments: List = None) -> str:
        # 📝 Handle Document Upload
        if attachments:
            file_bytes, file_type = attachments
            return self.analyze_document(file_bytes, file_type)

        # 🌐 Handle Scholarship URL
        if "http" in message:
            return self.analyze_scholarship_url(message)

        # 🧠 Extract profile from message
        profile_data = self._extract_profile(message)
        if profile_data:
            self.user_profile.update(profile_data)

        # 🎓 Scholarships
        if "scholarship" in message.lower():
            return self.get_latest_scholarships("")

        # 🏫 University Suggestions
        if "university" in message.lower() or "suggest" in message.lower():
            return self._find_universities()

        # 💬 Default Chat
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You're a smart and helpful educational assistant."},
                *self.conversation_history[-4:],  # Keep context short
                {"role": "user", "content": message}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content
