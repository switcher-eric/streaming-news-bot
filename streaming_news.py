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
        "name": "TOS.gg",
        "url": "https://tos.gg/rss/",
        "icon": "📺"
    },
    {
        "name": "Streaming Media",
        "url": "http://feeds.infotoday.com/StreamingMediaMagazine-FeaturedNews",
        "icon": "🎬"
    },
    {
        "name": "Streaming Media Blog",
        "url": "http://feeds.infotoday.com/Streaming-Media-Blog",
        "icon": "🎬"
    },
    {
        "name": "Newsshooter",
        "url": "https://www.newsshooter.com/feed/",
        "icon": "📷"
    },
]
# Keywords that indicate streaming-relevant content (case-insensitive)
STREAMING_KEYWORDS = [
    # Core live streaming terms
    "live stream", "livestream", "live video", "going live", "broadcast live",
    "live production", "live event",
    
    # Platforms
    "twitch", "youtube live", "tiktok live", "instagram live", "facebook live",
    "kick.com",
    
    # Live streaming features
    "super chat", "channel points", "raids", "gifted sub", "bits",
    "stream alerts", "stream overlay",
    
    # Creator/streamer terms
    "streamer", "streamers", "vtuber",
    
    # Live streaming tech & gear
    "obs studio", "streamlabs", "vmix", "ecamm", "wirecast", "xsplit",
    "stream deck", "capture card", "elgato", "encoder", "rtmp", "ndi",
    "streaming software", "multicam", "live switcher", "atem",
    "ptz camera", "broadcast camera", "switcher studio", "video switcher"
    
    # Industry terms
    "creator fund", "partner program", "live commerce", "live shopping",
    "simulcast", "multistream",
]

# Keywords to boost priority
HIGH_PRIORITY_KEYWORDS = [
    "live stream", "livestream", "twitch", "youtube live", "tiktok live",
    "streamer", "obs studio", "going live", "stream deck", "capture card",
    "elgato", "atem", "vmix", "live production",
]

# Keywords to exclude (reduces noise)
EXCLUDE_KEYWORDS = [
    # Streaming devices
    "fire stick", "firestick", "fire tv", "roku", "chromecast", "apple tv",
    "streaming box", "streaming stick", "streaming device", "set-top box",
    "4k streaming", "8k streaming", "tv stick",
    
    # VOD services
    "netflix", "disney+", "disney plus", "hulu", "amazon prime video",
    "hbo max", "paramount+", "peacock", "apple tv+", "max",
    "movie stream", "binge watch", "streaming service",
    
    # Music streaming
    "spotify", "apple music", "amazon music", "tidal", "deezer",
    "music streaming", "audio stream", "podcast",
    
    # AI/Tech noise
    "anthropic", "openai", "chatgpt", "vibe coding", "venture capital",
    "series a", "series b", "funding round", "ipo", "acquisition",
    "cryptocurrency", "crypto", "bitcoin", "VC", "blockchain", "nft",
    
    # Gaming (not streaming)
    "game pass", "cloud gaming", "geforce now", "xbox", "playstation",
    
    # General tech
    "smartphone", "iphone", "android", "laptop", "tablet",
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
    """Post a header followed by each article as a separate Slack message"""
    if not articles:
        print("No new articles to post")
        return
    
    # Sort by relevance score
    articles = sorted(articles, key=lambda x: x["score"], reverse=True)
    articles = articles[:10]  # Limit to 10 articles per update
    
    # Post header message first
    header_payload = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📺 Live Streaming News Update",
                    "emoji": True
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"*{len(articles)} new stories* • {datetime.now().strftime('%B %d, %Y at %I:%M %p')} • React with 👍 or reply in thread to discuss"
                    }
                ]
            },
            {"type": "divider"}
        ]
    }
    
    response = requests.post(
        webhook_url,
        json=header_payload,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code != 200:
        print(f"Failed to post header: {response.status_code}")
        return
    
    # Post each article as a separate message
    for article in articles:
        payload = {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{article['icon']} *<{article['link']}|{article['title']}>*\n_{article['source']}_\n{article['summary']}"
                    }
                }
            ]
        }
        
        response = requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            print(f"Posted: {article['title']}")
        else:
            print(f"Failed to post: {response.status_code} - {response.text}")
    
    print(f"Successfully posted {len(articles)} articles to Slack")

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
