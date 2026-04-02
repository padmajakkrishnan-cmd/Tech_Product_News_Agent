# Daily AI News Agent

An automated agent that fetches the latest AI and tech news, analyzes it with Claude, and emails you a daily briefing covering:

1. **Latest AI News** — Top stories on AI business, technology, research, and policy
2. **Company Moves** — What big tech and emerging AI startups are doing
3. **Top 20 Products** — B2C and B2B products with the highest AI disruption potential

## Architecture

```
NewsAPI + RSS Feeds → News Fetcher → Claude Analysis → HTML Email → SMTP
```

| Module | Description |
|---|---|
| `src/news_fetcher.py` | Pulls articles from NewsAPI and 5 curated RSS feeds |
| `src/analyzer.py` | Sends articles to Claude for structured analysis |
| `src/emailer.py` | Renders an HTML email with Jinja2 and sends via SMTP |
| `src/agent.py` | Orchestrates the full pipeline |
| `main.py` | CLI entry point with optional daily scheduler |

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in:

| Variable | Where to get it |
|---|---|
| `NEWSAPI_KEY` | Free key from [newsapi.org](https://newsapi.org) |
| `ANTHROPIC_API_KEY` | From [console.anthropic.com](https://console.anthropic.com) |
| `SMTP_USER` / `SMTP_PASSWORD` | Your email provider (Gmail: use [App Passwords](https://myaccount.google.com/apppasswords)) |
| `EMAIL_FROM` / `EMAIL_TO` | Sender and recipient email addresses |

### 3. Run

```bash
# Run once immediately
python main.py

# Run on a daily schedule (default 8:00 AM)
python main.py --schedule
```

The `--schedule` flag runs the briefing immediately on startup, then again every day at the time specified by `SEND_TIME` in your `.env`.

## Customization

- **RSS feeds**: Edit `Config.RSS_FEEDS` in `src/config.py`
- **Search queries**: Edit `Config.NEWS_QUERIES` in `src/config.py`
- **Email template**: Edit `templates/email.html`
- **Schedule time**: Set `SEND_TIME` in `.env` (24h format, e.g. `08:00`)
