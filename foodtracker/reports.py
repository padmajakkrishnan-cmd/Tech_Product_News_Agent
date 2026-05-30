"""Daily and weekly report generation.

Macro totals and discipline scoring are computed deterministically in Python;
Claude is used only to turn those numbers into friendly insights/narrative.
"""

import datetime as dt
import json
import logging

import anthropic

from foodtracker import db
from foodtracker.config import Config

logger = logging.getLogger(__name__)


# ------------------------------------------------------------- aggregation

def macro_totals(foods: list[dict]) -> dict:
    """Sum macros across a list of food rows."""
    totals = {"calories": 0.0, "protein_g": 0.0, "carbs_g": 0.0,
              "fat_g": 0.0, "fiber_g": 0.0}
    for f in foods:
        for k in totals:
            totals[k] += float(f.get(k) or 0)
    return {k: round(v, 1) for k, v in totals.items()}


def _habit_index(habits: list[dict]) -> dict:
    """Group habit rows by type for quick lookup."""
    idx: dict[str, list[dict]] = {}
    for h in habits:
        idx.setdefault(h["habit_type"], []).append(h)
    return idx


def _parse_time(value: str):
    """'06:30' -> minutes since midnight, or None."""
    try:
        hh, mm = value.split(":")
        return int(hh) * 60 + int(mm)
    except (ValueError, AttributeError):
        return None


# ------------------------------------------------------------- daily report

def daily_report(log_date: str) -> dict:
    foods = db.get_foods(log_date)
    habits = db.get_habits(log_date)
    goals = db.get_goals()
    totals = macro_totals(foods)

    cal_target = goals.get("calorie_target", 2000)
    pro_target = goals.get("protein_target", 120)

    macro_progress = {
        "calories": {
            "value": totals["calories"],
            "target": cal_target,
            "pct": round(100 * totals["calories"] / cal_target) if cal_target else 0,
        },
        "protein_g": {
            "value": totals["protein_g"],
            "target": pro_target,
            "pct": round(100 * totals["protein_g"] / pro_target) if pro_target else 0,
        },
    }

    return {
        "date": log_date,
        "foods": foods,
        "habits": habits,
        "totals": totals,
        "macro_progress": macro_progress,
        "goals": goals,
        "insights": _daily_insights(log_date, foods, habits, totals, goals),
    }


def _daily_insights(log_date, foods, habits, totals, goals) -> str:
    """Ask Claude for short, friendly insights on the day. Degrades gracefully."""
    if not foods and not habits:
        return "No entries logged yet today. Log a meal or habit to see insights."
    if not Config.ANTHROPIC_API_KEY:
        return "(Set ANTHROPIC_API_KEY to get AI insights.)"

    payload = {
        "date": log_date,
        "macro_totals": totals,
        "goals": goals,
        "foods": [
            {"name": f["name"], "quantity": f["quantity"], "meal": f["meal"],
             "calories": f["calories"], "protein_g": f["protein_g"]}
            for f in foods
        ],
        "habits": [
            {"type": h["habit_type"], "value": h["value"], "detail": h["detail"]}
            for h in habits
        ],
    }
    system = (
        "You are a supportive nutrition and lifestyle coach. Given a day's "
        "logged food macros, goals, and habits, write 3-5 short bullet insights. "
        "Be specific and encouraging: comment on macro balance vs goals, protein "
        "intake, and which target habits (wake time, walk after lunch, workout, "
        "water, sleep) were done or missed. End with one concrete tip for tomorrow. "
        "Output plain text bullets starting with '- '. No preamble."
    )
    try:
        client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model=Config.CLAUDE_MODEL,
            max_tokens=600,
            system=system,
            messages=[{"role": "user", "content": json.dumps(payload)}],
        )
        return msg.content[0].text.strip()
    except Exception as exc:  # noqa: BLE001 - insights are best-effort
        logger.warning("Daily insight generation failed: %s", exc)
        return "(Could not generate AI insights right now.)"


# ------------------------------------------------------------- weekly report

def week_bounds(any_date: str) -> tuple[str, str]:
    """Return (monday, sunday) ISO dates for the week containing any_date."""
    d = dt.date.fromisoformat(any_date)
    monday = d - dt.timedelta(days=d.weekday())
    sunday = monday + dt.timedelta(days=6)
    return monday.isoformat(), sunday.isoformat()


def weekly_report(any_date: str) -> dict:
    start, end = week_bounds(any_date)
    foods = db.get_foods_range(start, end)
    habits = db.get_habits_range(start, end)
    goals = db.get_goals()

    # Per-day breakdown
    days = [(dt.date.fromisoformat(start) + dt.timedelta(days=i)).isoformat()
            for i in range(7)]
    foods_by_day = {d: [] for d in days}
    habits_by_day = {d: [] for d in days}
    for f in foods:
        foods_by_day.setdefault(f["log_date"], []).append(f)
    for h in habits:
        habits_by_day.setdefault(h["log_date"], []).append(h)

    daily = []
    for d in days:
        daily.append({
            "date": d,
            "weekday": dt.date.fromisoformat(d).strftime("%a"),
            "totals": macro_totals(foods_by_day.get(d, [])),
            "habit_index": _habit_index(habits_by_day.get(d, [])),
        })

    scorecard = _discipline_scorecard(days, foods_by_day, habits_by_day, goals)

    return {
        "start": start,
        "end": end,
        "goals": goals,
        "daily": daily,
        "scorecard": scorecard,
        "narrative": _weekly_narrative(start, end, scorecard, goals),
    }


def _discipline_scorecard(days, foods_by_day, habits_by_day, goals) -> dict:
    """Compute adherence to each goal across the week -> a 0-100 discipline score."""
    wake_target = _parse_time(goals.get("wake_time", "06:30")) or (6 * 60 + 30)
    cal_target = goals.get("calorie_target", 2000)
    pro_target = goals.get("protein_target", 120)
    workouts_goal = goals.get("workouts_per_week", 4)
    water_goal = goals.get("water_target", 8)
    days_with_logs = [d for d in days if foods_by_day.get(d) or habits_by_day.get(d)]
    n_logged = max(len(days_with_logs), 1)

    # --- Wake-up adherence: days woken at/before target ---
    wake_hits, wake_days = 0, 0
    for d in days_with_logs:
        for h in habits_by_day.get(d, []):
            if h["habit_type"] == "wake_time":
                wake_days += 1
                mins = _parse_time(h["value"])
                if mins is not None and mins <= wake_target + 1:
                    wake_hits += 1
                break
    wake_rate = (wake_hits / wake_days) if wake_days else 0

    # --- Walk after lunch: days it was done ---
    walk_days = sum(
        1 for d in days_with_logs
        if any(h["habit_type"] == "walk_after_lunch" for h in habits_by_day.get(d, []))
    )
    walk_rate = walk_days / n_logged

    # --- Workouts: count distinct days with a workout vs weekly goal ---
    workout_days = sum(
        1 for d in days
        if any(h["habit_type"] == "workout" for h in habits_by_day.get(d, []))
    )
    workout_rate = min(workout_days / workouts_goal, 1.0) if workouts_goal else 0

    # --- Calories within +/-15% of target ---
    cal_hits = 0
    for d in days_with_logs:
        cals = macro_totals(foods_by_day.get(d, []))["calories"]
        if cals and abs(cals - cal_target) <= 0.15 * cal_target:
            cal_hits += 1
    cal_rate = cal_hits / n_logged

    # --- Protein target met ---
    pro_hits = 0
    for d in days_with_logs:
        pro = macro_totals(foods_by_day.get(d, []))["protein_g"]
        if pro >= 0.9 * pro_target:
            pro_hits += 1
    pro_rate = pro_hits / n_logged

    # --- Water target met ---
    water_hits = 0
    for d in days_with_logs:
        total_water = sum(
            (h["numeric"] or 0) for h in habits_by_day.get(d, [])
            if h["habit_type"] == "water"
        )
        if total_water >= water_goal:
            water_hits += 1
    water_rate = water_hits / n_logged

    components = [
        {"label": "Wake-up on time", "rate": wake_rate, "weight": 20,
         "detail": f"{wake_hits}/{wake_days or n_logged} days by {goals.get('wake_time')}"},
        {"label": "Walk after lunch", "rate": walk_rate, "weight": 15,
         "detail": f"{walk_days}/{n_logged} days"},
        {"label": "Workouts", "rate": workout_rate, "weight": 20,
         "detail": f"{workout_days}/{workouts_goal} sessions"},
        {"label": "Calorie target", "rate": cal_rate, "weight": 20,
         "detail": f"{cal_hits}/{n_logged} days within 15% of {cal_target}"},
        {"label": "Protein target", "rate": pro_rate, "weight": 15,
         "detail": f"{pro_hits}/{n_logged} days >= {pro_target}g"},
        {"label": "Hydration", "rate": water_rate, "weight": 10,
         "detail": f"{water_hits}/{n_logged} days >= {water_goal} glasses"},
    ]

    score = round(sum(c["rate"] * c["weight"] for c in components))
    for c in components:
        c["pct"] = round(c["rate"] * 100)

    if score >= 85:
        grade, label = "A", "Excellent discipline"
    elif score >= 70:
        grade, label = "B", "Solid week"
    elif score >= 55:
        grade, label = "C", "Mixed — room to improve"
    elif score >= 40:
        grade, label = "D", "Inconsistent"
    else:
        grade, label = "F", "Tough week — reset and restart"

    return {
        "score": score,
        "grade": grade,
        "label": label,
        "days_logged": len(days_with_logs),
        "components": components,
    }


def _weekly_narrative(start, end, scorecard, goals) -> str:
    if scorecard["days_logged"] == 0:
        return "No data logged this week yet."
    if not Config.ANTHROPIC_API_KEY:
        return "(Set ANTHROPIC_API_KEY to get an AI weekly summary.)"
    payload = {"week": f"{start} to {end}", "scorecard": scorecard, "goals": goals}
    system = (
        "You are a supportive habit coach. Given a weekly discipline scorecard "
        "(overall score, grade, and per-habit adherence), write a short narrative "
        "of 4-6 sentences: celebrate the wins, name the 1-2 weakest habits, and "
        "give 2 concrete, encouraging suggestions for next week. Plain prose, no lists."
    )
    try:
        client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model=Config.CLAUDE_MODEL,
            max_tokens=500,
            system=system,
            messages=[{"role": "user", "content": json.dumps(payload)}],
        )
        return msg.content[0].text.strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Weekly narrative generation failed: %s", exc)
        return "(Could not generate AI summary right now.)"
