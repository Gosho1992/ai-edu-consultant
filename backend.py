import os
import json
import requests
from openai import OpenAI
from dotenv import load_dotenv
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime

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
    
    def chat(self, message: str) -> str:
        """Process user message and return response"""
        # Add to conversation history
        self.conversation_history.append({"role": "user", "content": message})
        
        # Extract any profile information
        profile_data = self._extract_profile(message)
        if profile_data:
            self.user_profile.update(profile_data)
        
        # Handle university search requests
        if "university" in message.lower() or "suggest" in message.lower():
            return self._find_universities()
        
        # Default general response
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You're an education consultant. Be concise and helpful."},
                *self.conversation_history[-6:]  # Last 3 exchanges
            ],
            temperature=0.7
        )
        return response.choices[0].message.content
