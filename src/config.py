import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # News API
    NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")

    # Anthropic
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

    # Email
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    EMAIL_FROM = os.getenv("EMAIL_FROM", "")
    EMAIL_TO = os.getenv("EMAIL_TO", "")

    # Schedule
    SEND_TIME = os.getenv("SEND_TIME", "08:00")

    # RSS feeds for AI/tech news
    RSS_FEEDS = [
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        "https://feeds.arstechnica.com/arstechnica/technology-lab",
        "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        "https://blog.google/technology/ai/rss/",
        "https://openai.com/blog/rss.xml",
    ]

    # Search queries for NewsAPI
    NEWS_QUERIES = [
        "artificial intelligence business",
        "AI startups funding",
        "generative AI products",
        "AI agents technology",
        "large language models",
    ]
