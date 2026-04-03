"""Fetches latest AI and tech news from NewsAPI and RSS feeds."""

import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

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


def _parse_rss_xml(text: str, feed_url: str) -> list[dict]:
    """Parse RSS/Atom XML and return a list of article dicts."""
    articles = []
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        logger.warning("Could not parse XML from %s", feed_url)
        return []

    # Detect Atom namespace
    ns = {"atom": "http://www.w3.org/2005/Atom"}

    # Try RSS 2.0 first (<channel><item>)
    channel = root.find("channel")
    if channel is not None:
        feed_title = (channel.findtext("title") or feed_url).strip()
        for item in channel.findall("item")[:10]:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            desc = (item.findtext("description") or "").strip()[:500]
            pub = (item.findtext("pubDate") or "").strip()
            articles.append(
                {
                    "title": title,
                    "description": desc,
                    "url": link,
                    "source": feed_title,
                    "published": pub,
                }
            )
    else:
        # Try Atom (<feed><entry>)
        feed_title_el = root.find("atom:title", ns) or root.find("title")
        feed_title = (feed_title_el.text if feed_title_el is not None else feed_url).strip()
        entries = root.findall("atom:entry", ns) or root.findall("entry")
        for entry in entries[:10]:
            title_el = entry.find("atom:title", ns) or entry.find("title")
            title = (title_el.text if title_el is not None else "").strip()

            link_el = entry.find("atom:link", ns) or entry.find("link")
            link = (link_el.get("href", "") if link_el is not None else "").strip()

            summary_el = entry.find("atom:summary", ns) or entry.find("summary")
            desc = (summary_el.text if summary_el is not None and summary_el.text else "")[:500]

            pub_el = (
                entry.find("atom:published", ns)
                or entry.find("atom:updated", ns)
                or entry.find("published")
                or entry.find("updated")
            )
            pub = (pub_el.text if pub_el is not None else "").strip()

            articles.append(
                {
                    "title": title,
                    "description": desc,
                    "url": link,
                    "source": feed_title,
                    "published": pub,
                }
            )

    return articles


def fetch_from_rss() -> list[dict]:
    """Fetch recent articles from curated RSS feeds."""
    articles = []

    for feed_url in Config.RSS_FEEDS:
        try:
            resp = requests.get(feed_url, timeout=15, headers={"User-Agent": "DailyAINewsAgent/1.0"})
            resp.raise_for_status()
            feed_articles = _parse_rss_xml(resp.text, feed_url)
            articles.extend(feed_articles)
            logger.info("Fetched %d articles from %s", len(feed_articles), feed_url)
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
