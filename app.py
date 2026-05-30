"""Entry point for the Food & Habit Tracker web app.

Usage:
    pip install -r foodtracker/requirements.txt
    cp foodtracker/.env.example .env   # add your ANTHROPIC_API_KEY
    python app.py                      # then open http://localhost:8000

For auto-reload during development:
    uvicorn foodtracker.server:app --reload
"""

import os

import uvicorn


def main():
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    print(f"\n  🥗  Food & Habit Tracker running at http://localhost:{port}\n")
    uvicorn.run("foodtracker.server:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
