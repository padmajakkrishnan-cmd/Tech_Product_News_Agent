"""Formats the briefing as HTML and sends it via SMTP."""

import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from jinja2 import Template

from src.config import Config

logger = logging.getLogger(__name__)

TEMPLATE_PATH = Path(__file__).parent.parent / "templates" / "email.html"


def render_email(briefing: dict) -> str:
    """Render the briefing dict into an HTML email body."""
    template_str = TEMPLATE_PATH.read_text()
    template = Template(template_str)

    html = template.render(
        date=datetime.now().strftime("%A, %B %d, %Y"),
        ai_news=briefing.get("ai_news", []),
        company_moves=briefing.get("company_moves", []),
        products_to_watch=briefing.get("products_to_watch", []),
    )
    return html


def send_email(briefing: dict) -> None:
    """Render and send the daily briefing email."""
    html_body = render_email(briefing)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Daily AI Briefing - {datetime.now().strftime('%b %d, %Y')}"
    msg["From"] = Config.EMAIL_FROM
    msg["To"] = Config.EMAIL_TO

    # Plain-text fallback
    plain = _html_to_plain(briefing)
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    logger.info("Sending email to %s via %s:%s", Config.EMAIL_TO, Config.SMTP_HOST, Config.SMTP_PORT)

    with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT) as server:
        server.starttls()
        server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
        server.sendmail(Config.EMAIL_FROM, Config.EMAIL_TO.split(","), msg.as_string())

    logger.info("Email sent successfully.")


def _html_to_plain(briefing: dict) -> str:
    """Build a simple plain-text version of the briefing."""
    lines = [f"DAILY AI BRIEFING - {datetime.now().strftime('%A, %B %d, %Y')}", "=" * 50, ""]

    lines.append("LATEST AI NEWS")
    lines.append("-" * 30)
    for item in briefing.get("ai_news", []):
        lines.append(f"* [{item.get('category', '')}] {item['headline']}")
        lines.append(f"  {item['summary']}")
        if item.get("url"):
            lines.append(f"  {item['url']}")
        lines.append("")

    lines.append("WHAT AI COMPANIES ARE DOING")
    lines.append("-" * 30)
    for item in briefing.get("company_moves", []):
        tag = "Big Tech" if item.get("type") == "big_tech" else "Startup"
        lines.append(f"* [{tag}] {item['company']}")
        lines.append(f"  {item['activity']}")
        lines.append(f"  Why it matters: {item['significance']}")
        lines.append("")

    lines.append("TOP 20 PRODUCTS POISED FOR AI DISRUPTION")
    lines.append("-" * 30)
    for item in briefing.get("products_to_watch", []):
        lines.append(f"{item['rank']}. {item['product']} ({item['company']}) [{item['segment']}]")
        lines.append(f"   Now: {item['current_state']}")
        lines.append(f"   AI potential: {item['ai_disruption_potential']}")
        lines.append("")

    return "\n".join(lines)
