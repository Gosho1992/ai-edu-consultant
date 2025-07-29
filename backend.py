import os
import json
import requests
from openai import OpenAI
from dotenv import load_dotenv
from typing import Dict, List, Optional
import webbrowser
from datetime import datetime

# Load environment variables
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Tool configurations
TOOLS = {
    "google_search": {
        "api_key": os.getenv("GOOGLE_API_KEY"),
        "cx": os.getenv("GOOGLE_CX"),
        "endpoint": "https://www.googleapis.com/customsearch/v1"
    },
    "web_browser": {
        "enabled": True  # For opening URLs
    }
}

class EducationAgent:
    def __init__(self):
        self.user_profile: Dict = {}
        self.memory_file = "memory.json"
        self.required_fields = [
            "degree", "field_of_study", "country", 
            "gpa", "budget", "target_year"
        ]
        self._load_memory()

    def _load_memory(self) -> None:
        """Load past user profiles from a JSON file."""
        try:
            with open(self.memory_file, "r") as f:
                self.memory = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.memory = {}

    def _save_memory(self) -> None:
        """Save the current session to memory."""
        timestamp = datetime.now().isoformat()
        self.memory[timestamp] = self.user_profile
        with open(self.memory_file, "w") as f:
            json.dump(self.memory, f)

    def _orchestrate_task(self, task: str) -> List[Dict]:
    """
    Break down a task into subtasks using GPT-4-turbo.
    Example: "Find PhD programs in Germany" → [Search, Filter, Recommend]
    """
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "You are a task decomposition expert."},
            {"role": "user", "content": f"Break this task into steps: {task}"}
        ],
        temperature=0.3
    )

    try:
        parsed = json.loads(response.choices[0].message.content)
        return parsed.get("steps", [])
    except Exception:
        return []

    def _use_tool(self, tool_name: str, params: Dict) -> Optional[Dict]:
        """Execute a tool (Google Search, browser, etc.)."""
        if tool_name == "google_search":
            query = params.get("query", "")
            res = requests.get(
                TOOLS["google_search"]["endpoint"],
                params={
                    "key": TOOLS["google_search"]["api_key"],
                    "cx": TOOLS["google_search"]["cx"],
                    "q": query,
                    "num": 3  # Limit results for demo
                }
            )
            return res.json().get("items", [])
        elif tool_name == "web_browser":
            if params.get("url"):
                webbrowser.open(params["url"])
                return {"status": "opened_in_browser"}
        return None

    def _confirm_action(self, action: str) -> bool:
        """For critical actions (e.g., opening URLs)."""
        # In Streamlit, use `st.checkbox` or buttons instead
        return True  # Placeholder for backend-only logic

    def process_input(self, user_input: str) -> str:
        """
        Main method for Streamlit integration.
        Handles user input and returns AI response.
        """
        # Case 1: User sends a profile update (e.g., "My GPA is 3.8")
        if any(field in user_input.lower() for field in self.required_fields):
            self._update_profile(user_input)
            return "✅ Profile updated!"

        # Case 2: User requests a task (e.g., "Find Master's programs in France")
        if "find" in user_input.lower() or "search" in user_input.lower():
            if not self.user_profile:
                return "⚠️ Please set your profile first (degree, country, etc.)."
            
            task = f"Find {self.user_profile.get('degree', '')} programs in {self.user_profile.get('country', '')}"
            steps = self._orchestrate_task(task)
            
            # Execute the first step (e.g., Google Search)
            if steps and steps[0]["tool"] == "google_search":
                results = self._use_tool("google_search", {"query": steps[0]["query"]})
                return self._format_results(results)
            
            return "🔍 No results found."

        # Case 3: General advice (e.g., "What scholarships are available?")
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are an education consultant."},
                {"role": "user", "content": user_input}
            ]
        )
        return response.choices[0].message.content

    def _update_profile(self, user_input: str) -> None:
        """Extract profile fields from user input using GPT."""
        prompt = f"""
        Extract the following fields from this input: {user_input}
        Fields: {', '.join(self.required_fields)}
        Return JSON with only the extracted fields.
        """
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are a profile data extractor."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        extracted = json.loads(response.choices[0].message.content)
        self.user_profile.update(extracted)
        self._save_memory()

    def _format_results(self, search_results: List[Dict]) -> str:
        """Format Google Search results for Streamlit."""
        if not search_results:
            return "🔍 No results found."
        
        formatted = []
        for idx, item in enumerate(search_results[:3], 1):
            formatted.append(
                f"{idx}. **{item.get('title', 'No title')}**\n"
                f"   - {item.get('snippet', 'No description')}\n"
                f"   - [Link]({item.get('link', '#')})"
            )
        return "\n\n".join(formatted)
