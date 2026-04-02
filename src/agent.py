"""Main agent: orchestrates fetching, analysis, and emailing."""

import logging

from src.news_fetcher import fetch_all_news
from src.analyzer import analyze_news
from src.emailer import send_email

logger = logging.getLogger(__name__)


def run_daily_briefing() -> None:
    """Execute the full daily briefing pipeline."""
    logger.info("=== Starting Daily AI Briefing ===")

    # Step 1: Fetch news
    logger.info("Step 1/3: Fetching news...")
    articles = fetch_all_news()
    if not articles:
        logger.warning("No articles fetched. Aborting.")
        return

    # Step 2: Analyze with Claude
    logger.info("Step 2/3: Analyzing with Claude...")
    briefing = analyze_news(articles)

    # Step 3: Send email
    logger.info("Step 3/3: Sending email...")
    send_email(briefing)

    logger.info("=== Daily AI Briefing Complete ===")
