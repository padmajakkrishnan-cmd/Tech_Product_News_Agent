"""Fetches latest AI and tech news from NewsAPI and RSS feeds."""

import logging
from datetime import datetime, timedelta

import feedparser
import requests

from src.config import Config

logger = logging.getLogger(__name__)


def fetch_from_newsapi() -> list[dict]:
    """Fetch recent AI news articles from NewsAPI."""
    if not Config.NEWSAPI_KEY:
        logger.warning("NEWSAPI_KEY not set — skipping NewsAPI.")
        return []

    articles = []
    yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")

    for query in Config.NEWS_QUERIES:
        try:
            resp = requests.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q": query,
                    "from": yesterday,
                    "sortBy": "relevancy",
                    "language": "en",
                    "pageSize": 10,
                    "apiKey": Config.NEWSAPI_KEY,
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            for art in data.get("articles", []):
                articles.append(
                    {
                        "title": art.get("title", ""),
                        "description": art.get("description", ""),
                        "url": art.get("url", ""),
                        "source": art.get("source", {}).get("name", ""),
                        "published": art.get("publishedAt", ""),
                    }
                )
        except Exception:
            logger.exception("NewsAPI fetch failed for query: %s", query)

    # Deduplicate by URL
    seen = set()
    unique = []
    for a in articles:
        if a["url"] not in seen:
            seen.add(a["url"])
            unique.append(a)
    return unique


def fetch_from_rss() -> list[dict]:
    """Fetch recent articles from curated RSS feeds."""
    articles = []
    yesterday = datetime.utcnow() - timedelta(days=2)  # wider window for RSS

    for feed_url in Config.RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:10]:
                published = entry.get("published_parsed") or entry.get("updated_parsed")
                if published:
                    pub_dt = datetime(*published[:6])
                    if pub_dt < yesterday:
                        continue

                articles.append(
                    {
                        "title": entry.get("title", ""),
                        "description": entry.get("summary", "")[:500],
                        "url": entry.get("link", ""),
                        "source": feed.feed.get("title", feed_url),
                        "published": entry.get("published", ""),
                    }
                )
        except Exception:
            logger.exception("RSS fetch failed for: %s", feed_url)

    return articles


def fetch_all_news() -> list[dict]:
    """Fetch and combine news from all sources."""
    newsapi_articles = fetch_from_newsapi()
    rss_articles = fetch_from_rss()

    all_articles = newsapi_articles + rss_articles
    logger.info(
        "Fetched %d articles (%d NewsAPI, %d RSS)",
        len(all_articles),
        len(newsapi_articles),
        len(rss_articles),
    )
    return all_articles
