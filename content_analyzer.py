import requests
from bs4 import BeautifulSoup

def analyze_url_content(url: str) -> str:
    """Fetch and clean webpage content"""
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'footer']):
            element.decompose()
            
        return soup.get_text(separator='\n', strip=True)
    except Exception as e:
        return f"⚠️ Error analyzing URL: {str(e)}"