"""
Streaming News Bot for Switcher Studio
Monitors live streaming industry news and posts to Slack

Run manually: python streaming_news.py
Runs automatically via GitHub Actions on schedule
"""

import feedparser
import requests
import json
import os
import re
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

# =============================================================================
# CONFIGURATION
# =============================================================================

# RSS Feeds to monitor
RSS_FEEDS = [
    {
        "name": "YouTube Blog",
        "url": "https://blog.youtube/rss/",
        "icon": "🔴"
    },
    {
        "name": "TikTok Newsroom", 
        "url": "https://newsroom.tiktok.com/rss/",
        "icon": "🎵"
    },
    {
        "name": "Twitch Blog",
        "url": "https://blog.twitch.tv/en/rss/",
        "icon": "💜"
    },
    {
        "name": "TOS.gg",
        "url": "https://tos.gg/rss/",
        "icon": "📺"
    },
    {
        "name": "The Verge - Tech",
        "url": "https://www.theverge.com/rss/index.xml",
        "icon": "📰"
    },
    {
        "name": "TechCrunch",
        "url": "https://techcrunch.com/feed/",
        "icon": "💚"
    }
]

# Keywords that indicate streaming-relevant content (case-insensitive)
STREAMING_KEYWORDS = [
    # Core streaming terms
    "live stream", "livestream", "streaming", "broadcast", "going live",
    
    # Platforms
    "twitch", "youtube live", "tiktok live", "instagram live", "facebook live",
    "kick", "rumble", "dlive",
    
    # Features
    "monetization", "super chat", "subscription", "bits", "gifted sub",
    "channel points", "raids", "hosts", "clips", "vod",
    
    # Creator economy
    "creator", "streamer", "content creator", "influencer",
    
    # Tech
    "obs", "streamlabs", "encoder", "rtmp", "webrtc", "low latency",
    "multicam", "switcher", "live production",
    
    # Business
    "creator fund", "partner program", "affiliate", "creator economy"
]

# Keywords to boost priority (very relevant to live streaming)
HIGH_PRIORITY_KEYWORDS = [
    "live stream", "livestream", "twitch", "youtube live", "tiktok live",
    "streaming feature", "creator monetization", "going live", "live video"
]

# Keywords to exclude (reduces noise)
EXCLUDE_KEYWORDS = [
    "netflix", "disney+", "hulu", "amazon prime video", "apple tv+",
    "movie stream", "music streaming", "spotify", "audio stream"
]

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_slack_webhook():
    """Get Slack webhook URL from environment variable"""
    webhook = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook:
        raise ValueError(
            "SLACK_WEBHOOK_URL environment variable not set. "
            "Add it to your GitHub repository secrets."
        )
    return webhook


def get_posted_ids_file():
    """Get path to file tracking posted article IDs"""
    return Path(__file__).parent / "posted_ids.json"


def load_posted_ids():
    """Load set of already-posted article IDs"""
    filepath = get_posted_ids_file()
    if filepath.exists():
        with open(filepath, "r") as f:
            data = json.load(f)
            # Clean up old entries (older than 30 days)
            cutoff = (datetime.now() - timedelta(days=30)).isoformat()
            return {k: v for k, v in data.items() if v > cutoff}
    return {}


def save_posted_ids(posted_ids):
    """Save set of posted article IDs"""
    filepath = get_posted_ids_file()
    with open(filepath, "w") as f:
        json.dump(posted_ids, f, indent=2)


def generate_article_id(article):
    """Generate unique ID for an article"""
    unique_string = f"{article.get('link', '')}{article.get('title', '')}"
    return hashlib.md5(unique_string.encode()).hexdigest()


def is_streaming_relevant(title, summary=""):
    """Check if article is relevant to live streaming"""
    text = f"{title} {summary}".lower()
    
    # Exclude if matches exclusion keywords
    for keyword in EXCLUDE_KEYWORDS:
        if keyword.lower() in text:
            return False, 0
    
    # Check for streaming keywords
    score = 0
    matched_keywords = []
    
    for keyword in STREAMING_KEYWORDS:
        if keyword.lower() in text:
            score += 1
            matched_keywords.append(keyword)
    
    # Boost score for high-priority keywords
    for keyword in HIGH_PRIORITY_KEYWORDS:
        if keyword.lower() in text:
            score += 2
    
    # Need at least 1 keyword match to be relevant
    is_relevant = score >= 1
    
    return is_relevant, score


def clean_html(text):
    """Remove HTML tags from text"""
    clean = re.sub(r'<[^>]+>', '', text)
    clean = re.sub(r'\s+', ' ', clean)
    return clean.strip()


def truncate(text, max_length=200):
    """Truncate text to max length with ellipsis"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3].rsplit(' ', 1)[0] + "..."


# =============================================================================
# MAIN FUNCTIONS
# =============================================================================

def fetch_feed(feed_config):
    """Fetch and parse an RSS feed"""
    try:
        feed = feedparser.parse(feed_config["url"])
        articles = []
        
        for entry in feed.entries[:20]:  # Check last 20 entries
            title = entry.get("title", "")
            link = entry.get("link", "")
            summary = clean_html(entry.get("summary", entry.get("description", "")))
            published = entry.get("published", entry.get("updated", ""))
            
            # Check relevance
            is_relevant, score = is_streaming_relevant(title, summary)
            
            if is_relevant:
                articles.append({
                    "title": title,
                    "link": link,
                    "summary": truncate(summary),
                    "published": published,
                    "source": feed_config["name"],
                    "icon": feed_config["icon"],
                    "score": score
                })
        
        return articles
    
    except Exception as e:
        print(f"Error fetching {feed_config['name']}: {e}")
        return []


def post_to_slack(articles, webhook_url):
    """Post articles to Slack"""
    if not articles:
        print("No new articles to post")
        return
    
    # Sort by relevance score
    articles = sorted(articles, key=lambda x: x["score"], reverse=True)
    
    # Build Slack message
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🔴 Live Streaming News Update",
                "emoji": True
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"*{len(articles)} new stories* | {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
                }
            ]
        },
        {"type": "divider"}
    ]
    
    for article in articles[:10]:  # Limit to 10 articles per update
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{article['icon']} *<{article['link']}|{article['title']}>*\n_{article['source']}_\n{article['summary']}"
            }
        })
        blocks.append({"type": "divider"})
    
    # Add footer
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn", 
                "text": "💡 _Powered by Switcher Studio News Bot_ | Reply in thread to discuss"
            }
        ]
    })
    
    payload = {"blocks": blocks}
    
    response = requests.post(
        webhook_url,
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        print(f"Successfully posted {len(articles)} articles to Slack")
    else:
        print(f"Failed to post to Slack: {response.status_code} - {response.text}")


def main():
    """Main function"""
    print(f"Starting streaming news check at {datetime.now()}")
    
    # Load previously posted IDs
    posted_ids = load_posted_ids()
    
    # Fetch all feeds
    all_articles = []
    for feed in RSS_FEEDS:
        print(f"Checking {feed['name']}...")
        articles = fetch_feed(feed)
        all_articles.extend(articles)
    
    print(f"Found {len(all_articles)} relevant articles total")
    
    # Filter out already-posted articles
    new_articles = []
    for article in all_articles:
        article_id = generate_article_id(article)
        if article_id not in posted_ids:
            new_articles.append(article)
            posted_ids[article_id] = datetime.now().isoformat()
    
    print(f"Found {len(new_articles)} NEW articles")
    
    # Post to Slack if there are new articles
    if new_articles:
        webhook_url = get_slack_webhook()
        post_to_slack(new_articles, webhook_url)
    else:
        print("No new streaming news to report")
    
    # Save updated posted IDs
    save_posted_ids(posted_ids)
    
    print("Done!")


if __name__ == "__main__":
    main()
