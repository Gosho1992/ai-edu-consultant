# services/university_api.py

import requests

def search_universities_by_country(country: str, name: str = "") -> list:
    """
    Fetch university list using Hipolabs API.
    """
    try:
        params = {"country": country}
        if name:
            params["name"] = name
        response = requests.get("http://universities.hipolabs.com/search", params=params)
        response.raise_for_status()
        return response.json()[:5]  # Return top 5 results
    except Exception as e:
        return [{"error": str(e)}]
