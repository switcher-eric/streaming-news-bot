# 🔴 Streaming News Bot for Switcher Studio

Automatically monitors live streaming industry news and posts updates to your Slack channel.

## What it does

- Checks RSS feeds from YouTube Blog, TikTok Newsroom, Twitch Blog, TOS.gg, The Verge, and TechCrunch
- Filters for articles relevant to live streaming (using keyword matching)
- Posts new articles to your Slack channel every 6 hours
- Tracks which articles have been posted to avoid duplicates
- **100% free** using GitHub Actions

## Sample Slack Message

![Slack Preview](https://via.placeholder.com/400x300?text=Streaming+News+Update)

```
🔴 Live Streaming News Update
3 new stories | April 14, 2026 at 9:00 AM
────────────────────────────────
🎵 TikTok Partners with Cameo for New Monetization
TikTok Newsroom
TikTok and Cameo today announced a new partnership that will transform how creators connect with fans...

💜 Twitch Introduces Auto-Unsubscribe Feature  
Twitch Blog
Viewers will automatically get unsubscribed from a streamer if they do not stream for a month...
────────────────────────────────
💡 Powered by Switcher Studio News Bot
```

---

## Setup Instructions (10 minutes)

### Step 1: Create a Slack Webhook

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click **Create New App** → **From scratch**
3. Name it "Streaming News Bot" and select your workspace
4. Click **Incoming Webhooks** in the left sidebar
5. Toggle **Activate Incoming Webhooks** to ON
6. Click **Add New Webhook to Workspace**
7. Select the channel where you want news posted (e.g., `#streaming-news`)
8. Copy the Webhook URL (looks like `https://hooks.slack.com/services/T00000000/B00000000/XXXXXXX`)

### Step 2: Create GitHub Repository

1. Go to [github.com/new](https://github.com/new)
2. Name it `streaming-news-bot` (can be private)
3. Click **Create repository**

### Step 3: Upload the Bot Files

Upload these files to your repository:
```
streaming-news-bot/
├── .github/
│   └── workflows/
│       └── streaming-news.yml
├── streaming_news.py
├── requirements.txt
├── posted_ids.json
└── README.md
```

**Option A: Upload via GitHub UI**
1. Click "Add file" → "Upload files"
2. Drag all the files in
3. Click "Commit changes"

**Option B: Use Git**
```bash
git clone https://github.com/YOUR_USERNAME/streaming-news-bot.git
cd streaming-news-bot
# Copy all files here
git add .
git commit -m "Initial commit"
git push
```

### Step 4: Add Slack Webhook Secret

1. In your GitHub repo, go to **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Name: `SLACK_WEBHOOK_URL`
4. Value: Paste your Slack webhook URL from Step 1
5. Click **Add secret**

### Step 5: Enable GitHub Actions

1. Go to the **Actions** tab in your repo
2. You should see "Streaming News Bot" workflow
3. Click **Enable workflow** if prompted

### Step 6: Test It

1. Go to **Actions** → **Streaming News Bot**
2. Click **Run workflow** → **Run workflow**
3. Wait ~1 minute for it to complete
4. Check your Slack channel!

---

## Customization

### Change the schedule

Edit `.github/workflows/streaming-news.yml`:

```yaml
schedule:
  - cron: '0 */6 * * *'  # Every 6 hours
  # - cron: '0 9 * * *'  # Daily at 9 AM UTC
  # - cron: '0 9,17 * * 1-5'  # 9 AM and 5 PM UTC, weekdays only
```

### Add more RSS feeds

Edit `streaming_news.py` and add to the `RSS_FEEDS` list:

```python
{
    "name": "Your Feed Name",
    "url": "https://example.com/rss/",
    "icon": "📺"
}
```

### Adjust keyword filters

Edit the `STREAMING_KEYWORDS`, `HIGH_PRIORITY_KEYWORDS`, and `EXCLUDE_KEYWORDS` lists in `streaming_news.py`.

---

## Troubleshooting

**No messages in Slack?**
- Check that your webhook URL is correct in GitHub Secrets
- Look at the Actions log for errors
- The bot only posts NEW articles — if all current articles were already posted, nothing will be sent

**Too many irrelevant articles?**
- Add terms to `EXCLUDE_KEYWORDS` in `streaming_news.py`
- Remove noisy feeds from `RSS_FEEDS`

**Want to reset and re-post everything?**
- Delete the contents of `posted_ids.json` (make it just `{}`)
- Commit and push the change

---

## Cost

**$0** — GitHub Actions gives you 2,000 minutes/month free for private repos (unlimited for public repos). This bot uses ~1 minute per run × 4 runs/day = ~120 minutes/month.

---

## License

MIT — do whatever you want with it.

Built for [Switcher Studio](https://www.switcherstudio.com/) 🎬
