import os
import json
import requests
from openai import OpenAI
from dotenv import load_dotenv
from typing import Dict, List, Optional, Tuple
import webbrowser
from datetime import datetime
import logging
from enum import Enum
import re
from fuzzywuzzy import fuzz

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class SearchTool(Enum):
    GOOGLE_SEARCH = "google_search"
    OPENAI_API = "openai_api"
    BROWSER = "web_browser"
    CACHE = "cache"

class EducationAgent:
    def __init__(self):
        self.user_profile: Dict = {
            "degree": None,
            "field_of_study": None,
            "country": None,
            "gpa": None,
            "budget": None,
            "target_year": datetime.now().year + 1,
            "preferences": {
                "university_size": None,
                "research_focus": None,
                "location_type": None
            }
        }
        self.memory_file = "memory.json"
        self._load_memory()
        self._init_tools()
        self.conversation_context = []
        self.default_budgets = {
            "UK": {
                "low": 15000,
                "medium": 25000,
                "high": 35000
            },
            "USA": {
                "low": 20000,
                "medium": 35000,
                "high": 50000
            },
            # Add other countries as needed
        }
        
    def _init_tools(self) -> None:
        """Initialize all external tools and APIs"""
        self.tools = {
            SearchTool.GOOGLE_SEARCH.value: {
                "api_key": os.getenv("GOOGLE_API_KEY"),
                "cx": os.getenv("GOOGLE_CX"),
                "endpoint": "https://www.googleapis.com/customsearch/v1",
                "active": bool(os.getenv("GOOGLE_API_KEY"))
            },
            SearchTool.OPENAI_API.value: {
                "active": True  # Always available
            },
            SearchTool.BROWSER.value: {
                "enabled": True
            },
            SearchTool.CACHE.value: {
                "predefined_results": self._load_predefined_results()
            }
        }

    def _load_predefined_results(self) -> Dict:
        """Load predefined university results for fallback"""
        return {
            "embedded_systems_uk": [
                {
                    "title": "Imperial College London - MSc in Embedded Systems",
                    "description": "1-year program focusing on embedded systems design and implementation. Requires 2:1 degree in relevant field.",
                    "url": "https://www.imperial.ac.uk/study/courses/postgraduate/embedded-systems/",
                    "cost": "£34,400",
                    "deadline": "Rolling admissions"
                },
                # Add more predefined entries
            ]
        }

    def _load_memory(self) -> None:
        """Load past user profiles and conversations from JSON file"""
        try:
            with open(self.memory_file, "r") as f:
                data = json.load(f)
                self.memory = data.get("memory", {})
                self.previous_searches = data.get("searches", [])
        except (FileNotFoundError, json.JSONDecodeError):
            self.memory = {}
            self.previous_searches = []

    def _save_memory(self) -> None:
        """Save current session to memory file"""
        data = {
            "memory": self.memory,
            "searches": self.previous_searches,
            "last_updated": datetime.now().isoformat()
        }
        with open(self.memory_file, "w") as f:
            json.dump(data, f, indent=2)

    def _handle_missing_budget(self) -> None:
        """Set default budget based on target country"""
        if not self.user_profile.get("budget") and self.user_profile.get("country"):
            country = self.user_profile["country"].lower()
            for key in self.default_budgets:
                if key.lower() in country:
                    self.user_profile["budget"] = self.default_budgets[key]["medium"]
                    return
        self.user_profile["budget"] = 20000  # Global default

    def _validate_profile(self) -> Tuple[bool, str]:
        """Validate user profile completeness"""
        required = ["degree", "field_of_study", "country", "gpa"]
        missing = [field for field in required if not self.user_profile.get(field)]
        
        if missing:
            return False, f"Missing required fields: {', '.join(missing)}"
        
        if not 0 <= float(self.user_profile["gpa"]) <= 4.0:
            return False, "GPA must be between 0.0 and 4.0"
            
        return True, "Profile is valid"

    def _search_universities(self, query: str) -> List[Dict]:
        """Search for universities using multiple sources with fallback"""
        results = []
        
        # Try Google Search first if available
        if self.tools[SearchTool.GOOGLE_SEARCH.value]["active"]:
            try:
                google_results = self._use_tool(
                    SearchTool.GOOGLE_SEARCH.value,
                    {"query": self._enhance_search_query(query), "num": 5}
                )
                if google_results:
                    results.extend(self._parse_google_results(google_results))
            except Exception as e:
                logger.error(f"Google search failed: {e}")
        
        # If no results from Google, try OpenAI API
        if not results and self.tools[SearchTool.OPENAI_API.value]["active"]:
            try:
                openai_results = self._use_tool(
                    SearchTool.OPENAI_API.value,
                    {"query": query, "profile": self.user_profile}
                )
                if openai_results:
                    results.extend(openai_results)
            except Exception as e:
                logger.error(f"OpenAI search failed: {e}")
        
        # If still no results, use predefined cache
        if not results:
            cache_key = f"{self.user_profile['field_of_study'].lower()}_{self.user_profile['country'].lower()}"
            cached = self.tools[SearchTool.CACHE.value]["predefined_results"].get(cache_key, [])
            results.extend(cached)
        
        return self._deduplicate_results(results)

    def _use_tool(self, tool_name: str, params: Dict) -> Optional[Dict]:
        """Execute external tool with proper error handling"""
        try:
            if tool_name == SearchTool.GOOGLE_SEARCH.value:
                res = requests.get(
                    self.tools[tool_name]["endpoint"],
                    params={
                        "key": self.tools[tool_name]["api_key"],
                        "cx": self.tools[tool_name]["cx"],
                        "q": params["query"],
                        "num": params.get("num", 3)
                    },
                    timeout=10
                )
                res.raise_for_status()
                return res.json().get("items", [])
                
            elif tool_name == SearchTool.OPENAI_API.value:
                return self._get_openai_recommendations(params["query"], params["profile"])
                
            elif tool_name == SearchTool.BROWSER.value:
                if params.get("url"):
                    webbrowser.open(params["url"])
                    return {"status": "opened_in_browser"}
                    
            return None
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {str(e)}")
            return None

    def _get_openai_recommendations(self, query: str, profile: Dict) -> List[Dict]:
        """Get university recommendations from OpenAI when other sources fail"""
        prompt = f"""
        Act as an expert education consultant. Recommend universities for:
        {query}
        
        Student Profile:
        {json.dumps(profile, indent=2)}
        
        Return JSON with:
        - title (string): University and program name
        - description (string): Key details
        - url (string): Official program URL if known
        - cost (string): Estimated tuition
        - deadline (string): Application deadline if known
        
        Include 5 best options matching the profile.
        """
        
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are a university recommendation engine."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.5
        )
        
        try:
            data = json.loads(response.choices[0].message.content)
            return data.get("recommendations", [])
        except json.JSONDecodeError:
            return []

    def process_input(self, user_input: str) -> str:
        """Main method to process user input and return response"""
        try:
            # Update conversation context
            self.conversation_context.append({"role": "user", "content": user_input})
            
            # Check if input contains profile updates
            if any(keyword in user_input.lower() for keyword in 
                  ["degree", "study", "country", "gpa", "budget", "preference"]):
                extracted = self._extract_profile_data(user_input)
                if extracted:
                    self.user_profile.update(extracted)
                    self._save_memory()
                    return "✅ Profile updated successfully!"
            
            # Handle university search requests
            if any(keyword in user_input.lower() for keyword in 
                  ["find", "search", "suggest", "recommend", "university"]):
                self._handle_missing_budget()
                valid, msg = self._validate_profile()
                if not valid:
                    return f"⚠️ {msg}"
                
                search_results = self._search_universities(user_input)
                if not search_results:
                    return "🔍 No matching universities found. Try adjusting your criteria."
                
                self.previous_searches.append({
                    "query": user_input,
                    "results": search_results,
                    "timestamp": datetime.now().isoformat()
                })
                self._save_memory()
                
                return self._format_search_results(search_results)
            
            # Default AI response for general queries
            return self._generate_ai_response(user_input, self.conversation_context)
            
        except Exception as e:
            logger.error(f"Error processing input: {e}")
            return "⚠️ An error occurred. Please try again later."

    def _format_search_results(self, results: List[Dict]) -> str:
        """Format search results for display with budget context"""
        response = []
        
        if not self.user_profile.get("budget"):
            response.append("ℹ️ Showing results across different budget ranges since none was specified:")
        
        for idx, uni in enumerate(results[:5], 1):
            entry = [
                f"{idx}. **{uni.get('title', 'Unknown University')}**",
                f"   - {uni.get('description', 'No description available')}"
            ]
            
            if uni.get("cost"):
                entry.append(f"   - Tuition: {uni['cost']}")
            if uni.get("url"):
                entry.append(f"   - [More info]({uni['url']})")
            
            response.append("\n".join(entry))
        
        response.append("\n💡 Tip: Specify your budget for more tailored recommendations.")
        return "\n\n".join(response)

# Additional helper methods would follow the same pattern as before
