#!/usr/bin/env python3
"""
Daily AI News Agent
Fetches AI/tech news, analyzes it with Claude, and emails a daily briefing.

Usage:
    python main.py              # Run once immediately
    python main.py --schedule   # Run on a daily schedule
"""

import argparse
import logging
import sys
import time

import schedule

from src.agent import run_daily_briefing
from src.config import Config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Daily AI News Agent")
    parser.add_argument(
        "--schedule",
        action="store_true",
        help=f"Run on a daily schedule at {Config.SEND_TIME}",
    )
    args = parser.parse_args()

    if args.schedule:
        logger.info("Scheduling daily briefing at %s", Config.SEND_TIME)
        schedule.every().day.at(Config.SEND_TIME).do(run_daily_briefing)

        # Also run once immediately on startup
        logger.info("Running initial briefing now...")
        run_daily_briefing()

        logger.info("Scheduler running. Press Ctrl+C to stop.")
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)
        except KeyboardInterrupt:
            logger.info("Scheduler stopped.")
    else:
        run_daily_briefing()


if __name__ == "__main__":
    main()
