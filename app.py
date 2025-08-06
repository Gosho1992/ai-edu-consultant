import streamlit as st
from backend import EducationAgent

# Set up the app
st.set_page_config(page_title="EduBot", page_icon="🎓")

# Initialize the agent
if "agent" not in st.session_state:
    st.session_state.agent = EducationAgent()
    st.session_state.messages = [
        {"role": "assistant", "content": "Hi! I'm your education consultant. Tell me about your academic goals."}
    ]

# Title and description
st.title("🎓 EduBot - AI Education Consultant")
st.caption("A ChatGPT-like interface for university guidance")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask me about universities or scholarships..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get AI response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = st.session_state.agent.chat(prompt)
        st.markdown(response)
        
        # 👇 Optional footer for scholarship answers
        if "scholarship" in prompt.lower():
            st.markdown(
                """
                <div style="margin-top: 1rem; font-size: 0.85rem; color: gray;">
                📌 <em>Scholarship summaries are sourced via public RSS feeds from ScholarshipsCorner and ScholarshipUnion. For complete details, always refer to the original websites.</em>
                </div>
                """, unsafe_allow_html=True
            )
    
    # Add AI response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})

backend: import os
import json
import requests
from openai import OpenAI
from dotenv import load_dotenv
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime

# Import the RSS fetcher
from rss_fetcher import fetch_rss_scholarships

# Load environment variables
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class EducationAgent:
    def __init__(self):
        self.user_profile = {
            "degree": None,
            "field_of_study": None,
            "country": None,
            "gpa": None,
            "budget": None
        }
        self.conversation_history = []

    def _extract_profile(self, message: str) -> Dict:
        """Extract profile information from natural language"""
        prompt = f"""
        Extract education profile details from this message:
        {message}
        
        Possible fields:
        - degree (Bachelor's, Master's, PhD)
        - field_of_study
        - country
        - gpa (convert to 4.0 scale)
        - budget (convert to USD)
        
        Return JSON with any found fields.
        """

        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)

    def _find_universities(self) -> str:
        """Find universities based on current profile"""
        if not all([self.user_profile["degree"], 
                    self.user_profile["field_of_study"], 
                    self.user_profile["country"]]):
            return "Please specify your degree, field of study, and target country first."

        prompt = f"""
        Recommend 5 universities for:
        - Degree: {self.user_profile["degree"]}
        - Field: {self.user_profile["field_of_study"]}
        - Country: {self.user_profile["country"]}
        - GPA: {self.user_profile.get("gpa", "Not specified")}
        - Budget: {self.user_profile.get("budget", "Not specified")} USD/year

        Format each as:
        1. [University Name] - [Program Name]
           • Key features
           • Estimated cost
           • [Admissions link]
        """

        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content

    def get_latest_scholarships(self, topic: str = "") -> str:
        """Fetch and return latest scholarships (without showing source)"""
        all_items = fetch_rss_scholarships()

        # Optional keyword filtering
        if topic:
            filtered = [item for item in all_items if topic.lower() in item["title"].lower()]
            items = filtered[:5] if filtered else all_items[:3]
        else:
            items = all_items[:5]

        if not items:
            return "❌ No recent scholarships found."

        response_lines = ["🎓 **Latest Scholarships**:\n"]
        for idx, s in enumerate(items, 1):
            response_lines.append(
                f"{idx}. **{s['title']}**\n"
                f"   - 📅 Deadline: {s['published']}\n"
                f"   - {s['summary']}\n"
                f"   - 🔗 [View Details]({s['link']})\n"
            )

        return "\n".join(response_lines)

    def chat(self, message: str) -> str:
        """Process user message and return response"""
        self.conversation_history.append({"role": "user", "content": message})

        # Extract profile info
        profile_data = self._extract_profile(message)
        if profile_data:
            self.user_profile.update(profile_data)

        # Scholarships
        if "latest scholarships" in message.lower():
            return self.get_latest_scholarships()
        if "electronics scholarships" in message.lower():
            return self.get_latest_scholarships("electronics")

        # Universities
        if "university" in message.lower() or "suggest" in message.lower():
            return self._find_universities()

        # General response
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You're an education consultant. Be concise and helpful."},
                *self.conversation_history[-6:]
            ],
            temperature=0.7
        )
        return response.choices[0].message.content

# rss_fetcher.py

import feedparser
import json
from datetime import datetime

def fetch_rss_scholarships():
    feeds = {
        "ScholarshipsCorner": "https://scholarshipscorner.website/feed/",
        "ScholarshipUnion": "https://scholarshipunion.com/feed/"
    }

    all_scholarships = []

    for source, url in feeds.items():
        feed = feedparser.parse(url)
        for entry in feed.entries[:5]:  # Get top 5 posts
            scholarship = {
                "source": source,
                "title": entry.title,
                "link": entry.link,
                "published": entry.get("published", "N/A"),
                "summary": entry.get("summary", "")[:250] + "..."
            }
            all_scholarships.append(scholarship)

    return all_scholarships


# Optional: preview output in terminal
if __name__ == "__main__":
    data = fetch_rss_scholarships()
    print(json.dumps(data, indent=2))
