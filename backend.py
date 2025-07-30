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
    UNIVERSITY_API = "university_api"
    BROWSER = "web_browser"

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
        
    def _init_tools(self) -> None:
        """Initialize all external tools and APIs"""
        self.tools = {
            SearchTool.GOOGLE_SEARCH.value: {
                "api_key": os.getenv("GOOGLE_API_KEY"),
                "cx": os.getenv("GOOGLE_CX"),
                "endpoint": "https://www.googleapis.com/customsearch/v1",
                "active": bool(os.getenv("GOOGLE_API_KEY"))
            },
            SearchTool.UNIVERSITY_API.value: {
                "endpoint": "https://api.university-data.com/v1",
                "api_key": os.getenv("UNIVERSITY_API_KEY"),
                "active": False  # Set to True if you have access
            },
            SearchTool.BROWSER.value: {
                "enabled": True
            }
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

    def _validate_profile(self) -> Tuple[bool, str]:
        """Validate user profile completeness"""
        required = ["degree", "field_of_study", "country", "gpa", "budget"]
        missing = [field for field in required if not self.user_profile.get(field)]
        
        if missing:
            return False, f"Missing required fields: {', '.join(missing)}"
        
        if not 0 <= float(self.user_profile["gpa"]) <= 4.0:
            return False, "GPA must be between 0.0 and 4.0"
            
        return True, "Profile is valid"

    def _enhance_search_query(self, raw_query: str) -> str:
        """Use AI to enhance search queries for better results"""
        prompt = f"""
        As an expert education researcher, optimize this search query for finding university programs:
        Original query: {raw_query}
        
        Consider:
        - The student's profile: {json.dumps(self.user_profile)}
        - Current academic trends
        - Official university website terminology
        
        Return ONLY the enhanced search query string.
        """
        
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are a search query optimization expert."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=100
        )
        return response.choices[0].message.content.strip()

    def _search_universities(self, query: str) -> List[Dict]:
        """Search for universities using multiple sources"""
        results = []
        
        # 1. Try Google Custom Search
        if self.tools[SearchTool.GOOGLE_SEARCH.value]["active"]:
            try:
                google_results = self._use_tool(
                    SearchTool.GOOGLE_SEARCH.value,
                    {"query": self._enhance_search_query(query), "num": 5}
                )
                results.extend(self._parse_google_results(google_results))
            except Exception as e:
                logger.error(f"Google search failed: {e}")
        
        # 2. Try University API if available
        if self.tools[SearchTool.UNIVERSITY_API.value]["active"]:
            try:
                api_results = self._use_tool(
                    SearchTool.UNIVERSITY_API.value,
                    {"query": query, "filters": self.user_profile}
                )
                results.extend(api_results)
            except Exception as e:
                logger.error(f"University API failed: {e}")
        
        return self._deduplicate_results(results)

    def _parse_google_results(self, results: List[Dict]) -> List[Dict]:
        """Extract structured university data from Google results"""
        parsed = []
        for item in results:
            if not self._is_relevant_result(item.get("link", "")):
                continue
                
            parsed.append({
                "title": item.get("title", ""),
                "description": item.get("snippet", ""),
                "url": item.get("link", ""),
                "source": "google",
                "relevance": self._calculate_relevance(item)
            })
        return sorted(parsed, key=lambda x: x["relevance"], reverse=True)

    def _is_relevant_result(self, url: str) -> bool:
        """Check if URL appears to be from a legitimate university"""
        edu_patterns = [
            r"\.edu$",
            r"ac\.uk$",
            r"univ-",
            r"university",
            r"college",
            r"\.ac\."
        ]
        return any(re.search(pattern, url.lower()) for pattern in edu_patterns)

    def _calculate_relevance(self, result_item: Dict) -> float:
        """Calculate relevance score for search results"""
        title = result_item.get("title", "").lower()
        desc = result_item.get("snippet", "").lower()
        
        # Check for degree match
        degree_score = fuzz.partial_ratio(
            self.user_profile["degree"].lower(),
            f"{title} {desc}"
        ) / 100.0
        
        # Check for field of study match
        field_score = fuzz.partial_ratio(
            self.user_profile["field_of_study"].lower(),
            f"{title} {desc}"
        ) / 100.0 if self.user_profile["field_of_study"] else 0.5
        
        # Check for country match
        country_score = fuzz.partial_ratio(
            self.user_profile["country"].lower(),
            f"{title} {desc}"
        ) / 100.0
        
        return (degree_score * 0.4) + (field_score * 0.3) + (country_score * 0.3)

    def _deduplicate_results(self, results: List[Dict]) -> List[Dict]:
        """Remove duplicate results from different sources"""
        seen_urls = set()
        unique_results = []
        
        for result in sorted(results, key=lambda x: x.get("relevance", 0), reverse=True):
            if result["url"] not in seen_urls:
                seen_urls.add(result["url"])
                unique_results.append(result)
                
        return unique_results[:10]  # Return top 10 results

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
                
            elif tool_name == SearchTool.UNIVERSITY_API.value:
                # Implementation for university API would go here
                pass
                
            elif tool_name == SearchTool.BROWSER.value:
                if params.get("url"):
                    webbrowser.open(params["url"])
                    return {"status": "opened_in_browser"}
                    
            return None
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {str(e)}")
            return None

    def _generate_ai_response(self, prompt: str, context: List[Dict]) -> str:
        """Generate AI response with proper context handling"""
        messages = [
            {
                "role": "system",
                "content": """You are an expert education consultant with deep knowledge of global universities. 
                Your responses should be:
                - Accurate and factual
                - Personalized to the student's profile
                - Clear and concise
                - Include specific recommendations when possible"""
            }
        ]
        
        # Add conversation history
        messages.extend(context[-6:])  # Keep last 6 messages for context
        
        # Add current prompt
        messages.append({"role": "user", "content": prompt})
        
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        
        return response.choices[0].message.content

    def _extract_profile_data(self, text: str) -> Dict:
        """Use AI to extract profile data from unstructured text"""
        prompt = f"""
        Extract education profile details from this text:
        {text}
        
        Possible fields to extract:
        - degree (Bachelor's, Master's, PhD, etc.)
        - field_of_study
        - country
        - gpa (convert to 4.0 scale if needed)
        - budget (convert to USD if needed)
        - preferences (university_size, research_focus, location_type)
        
        Return ONLY a JSON object with the extracted fields.
        """
        
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are a profile data extraction expert."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        
        try:
            return json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            return {}

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
                valid, msg = self._validate_profile()
                if not valid:
                    return f"⚠️ {msg}. Please complete your profile first."
                
                search_results = self._search_universities(user_input)
                if not search_results:
                    return "🔍 No matching universities found. Try adjusting your criteria."
                
                self.previous_searches.append({
                    "query": user_input,
                    "results": search_results,
                    "timestamp": datetime.now().isoformat()
                })
                self._save_memory()
                
                formatted = self._format_search_results(search_results)
                return formatted
            
            # Default AI response for general queries
            return self._generate_ai_response(user_input, self.conversation_context)
            
        except Exception as e:
            logger.error(f"Error processing input: {e}")
            return "⚠️ An error occurred. Please try again later."

    def _format_search_results(self, results: List[Dict]) -> str:
        """Format search results for display"""
        formatted = ["Here are some university programs that match your criteria:"]
        
        for idx, uni in enumerate(results[:5], 1):  # Show top 5 results
            formatted.append(
                f"{idx}. **{uni.get('title', 'Unknown University')}**\n"
                f"   - {uni.get('description', 'No description available')}\n"
                f"   - [More info]({uni.get('url', '#')})"
            )
            
        formatted.append("\nWould you like me to provide more details about any of these?")
        return "\n\n".join(formatted)
