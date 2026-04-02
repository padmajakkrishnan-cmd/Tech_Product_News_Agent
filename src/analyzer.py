"""Uses Claude to analyze news and produce a structured daily briefing."""

import json
import logging

import anthropic

from src.config import Config

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a senior technology analyst who produces a daily AI news briefing.
You will receive a batch of recent news articles about AI and technology.

Produce a structured JSON response with exactly three sections:

{
  "ai_news": [
    {
      "headline": "...",
      "summary": "2-3 sentence summary of the news",
      "source": "source name",
      "url": "article url",
      "category": "business | technology | research | policy"
    }
  ],
  "company_moves": [
    {
      "company": "Company Name",
      "type": "big_tech | startup",
      "activity": "2-3 sentence description of what they are doing",
      "significance": "Why this matters in 1 sentence",
      "source_url": "url if available"
    }
  ],
  "products_to_watch": [
    {
      "rank": 1,
      "product": "Product Name",
      "company": "Company Name",
      "segment": "B2C | B2B",
      "current_state": "Brief description of the product today",
      "ai_disruption_potential": "How AI could transform this product",
      "source_url": "url if available"
    }
  ]
}

Rules:
- ai_news: Pick the top 10-15 most impactful stories. Cover both business and technology angles.
- company_moves: Cover both big tech (Google, Microsoft, Meta, Apple, Amazon, NVIDIA, etc.)
  AND emerging AI startups (Anthropic, OpenAI, Mistral, Cohere, Perplexity, etc.).
  Include 8-12 entries.
- products_to_watch: List exactly 20 products ranked by AI disruption potential.
  Mix B2C and B2B. Think broadly — SaaS, developer tools, consumer apps,
  enterprise platforms, hardware, etc. Focus on products where AI evolution
  could cause significant transformation.
- Be specific and factual. Only include information supported by the provided articles.
- For products_to_watch, you may also use your general knowledge of the tech landscape
  to identify products even if not directly mentioned in today's articles.
- Return ONLY valid JSON, no markdown fences or extra text.
"""


def analyze_news(articles: list[dict]) -> dict:
    """Send articles to Claude for analysis and return structured briefing."""
    client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)

    # Prepare article summaries for the prompt
    article_texts = []
    for i, art in enumerate(articles[:80], 1):  # cap to avoid token limits
        article_texts.append(
            f"[{i}] {art['title']}\n"
            f"Source: {art['source']}\n"
            f"URL: {art['url']}\n"
            f"Published: {art['published']}\n"
            f"Summary: {art['description']}\n"
        )

    user_message = (
        "Here are today's collected AI and technology news articles:\n\n"
        + "\n---\n".join(article_texts)
        + "\n\nPlease analyze these and produce the daily briefing JSON."
    )

    logger.info("Sending %d articles to Claude for analysis...", len(article_texts))

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    response_text = message.content[0].text

    try:
        briefing = json.loads(response_text)
    except json.JSONDecodeError:
        # Try to extract JSON from response if wrapped in text
        import re
        json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if json_match:
            briefing = json.loads(json_match.group())
        else:
            logger.error("Failed to parse Claude response as JSON")
            raise

    logger.info(
        "Analysis complete: %d news, %d company moves, %d products",
        len(briefing.get("ai_news", [])),
        len(briefing.get("company_moves", [])),
        len(briefing.get("products_to_watch", [])),
    )
    return briefing
