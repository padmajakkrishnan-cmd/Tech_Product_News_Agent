"""Configuration for the food & habit tracker."""

import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    # Anthropic / Claude
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    # Vision + text parsing model. Sonnet is a good cost/quality balance.
    CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

    # Storage
    DB_PATH = os.getenv("FOODTRACKER_DB", "foodtracker.db")

    # Timezone label is informational only; the browser sends local dates.
    TIMEZONE = os.getenv("TIMEZONE", "local")

    # Default daily/weekly goals. These seed the editable goals on first run;
    # afterwards they are read from the database so the user can change them.
    DEFAULT_GOALS = {
        "wake_time": os.getenv("GOAL_WAKE_TIME", "06:30"),          # HH:MM, wake by
        "calorie_target": int(os.getenv("GOAL_CALORIES", "2000")),  # kcal/day
        "protein_target": int(os.getenv("GOAL_PROTEIN", "120")),    # grams/day
        "walk_after_lunch": 1,                                       # 1 = expected daily
        "workouts_per_week": int(os.getenv("GOAL_WORKOUTS", "4")),  # sessions/week
        "water_target": int(os.getenv("GOAL_WATER", "8")),          # glasses/day
        "sleep_target_hours": float(os.getenv("GOAL_SLEEP", "7.5")), # hours/night
    }


# Recognised habit types. Free-form habits still get stored under "other".
HABIT_TYPES = {
    "wake_time": "Wake-up time",
    "sleep_time": "Bedtime / sleep start",
    "sleep_hours": "Hours slept",
    "walk_after_lunch": "Walk after lunch",
    "workout": "Workout / exercise",
    "water": "Water intake",
    "steps": "Steps",
    "meditation": "Meditation / mindfulness",
    "other": "Other habit",
}
