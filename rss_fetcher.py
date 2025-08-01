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
