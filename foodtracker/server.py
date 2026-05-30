"""FastAPI server for the food & habit tracker.

Run with:  uvicorn foodtracker.server:app --reload
or simply: python app.py
"""

import datetime as dt
import logging
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from foodtracker import db, parser, reports
from foodtracker.config import HABIT_TYPES

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("foodtracker")

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Food & Habit Tracker")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.on_event("startup")
def _startup():
    db.init_db()
    logger.info("Database ready at %s", db.Config.DB_PATH)


def _today() -> str:
    return dt.date.today().isoformat()


def _valid_date(value: str | None) -> str:
    if not value:
        return _today()
    try:
        dt.date.fromisoformat(value)
        return value
    except ValueError:
        return _today()


# ----------------------------------------------------------------- pages

@app.get("/", response_class=HTMLResponse)
def home(request: Request, date: str | None = None):
    log_date = _valid_date(date)
    report = reports.daily_report(log_date)
    return templates.TemplateResponse(
        request,
        "index.html",
        {"report": report, "date": log_date, "habit_types": HABIT_TYPES},
    )


@app.get("/weekly", response_class=HTMLResponse)
def weekly(request: Request, date: str | None = None):
    log_date = _valid_date(date)
    report = reports.weekly_report(log_date)
    return templates.TemplateResponse(
        request, "weekly.html", {"report": report, "date": log_date}
    )


@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    return templates.TemplateResponse(
        request, "settings.html", {"goals": db.get_goals()}
    )


# ----------------------------------------------------------------- logging API

@app.post("/api/log/text")
def log_text(text: str = Form(...), date: str = Form(None),
             source: str = Form("text")):
    """Parse a typed message or voice transcript and store the entries."""
    text = (text or "").strip()
    if not text:
        raise HTTPException(400, "Empty input")
    log_date = _valid_date(date)
    try:
        parsed = parser.parse_text(text)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Text parse failed")
        raise HTTPException(502, f"Could not parse input: {exc}")

    for item in parsed.get("foods", []):
        db.add_food(log_date, item, source, text)
    for item in parsed.get("habits", []):
        db.add_habit(log_date, item, source, text)

    return JSONResponse({
        "ok": True,
        "foods_added": len(parsed.get("foods", [])),
        "habits_added": len(parsed.get("habits", [])),
        "parsed": parsed,
    })


@app.post("/api/log/photo")
async def log_photo(photo: UploadFile = File(...), date: str = Form(None),
                    hint: str = Form("")):
    """Analyse a meal photo and store the detected foods."""
    log_date = _valid_date(date)
    image_bytes = await photo.read()
    if not image_bytes:
        raise HTTPException(400, "Empty image")
    media_type = photo.content_type or "image/jpeg"
    if media_type not in {"image/jpeg", "image/png", "image/webp", "image/gif"}:
        media_type = "image/jpeg"
    try:
        parsed = parser.parse_image(image_bytes, media_type, hint)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Photo parse failed")
        raise HTTPException(502, f"Could not analyse photo: {exc}")

    raw = f"[photo] {hint}".strip()
    for item in parsed.get("foods", []):
        db.add_food(log_date, item, "photo", raw)

    return JSONResponse({
        "ok": True,
        "foods_added": len(parsed.get("foods", [])),
        "note": parsed.get("note", ""),
        "parsed": parsed,
    })


@app.delete("/api/food/{food_id}")
def remove_food(food_id: int):
    db.delete_food(food_id)
    return {"ok": True}


@app.delete("/api/habit/{habit_id}")
def remove_habit(habit_id: int):
    db.delete_habit(habit_id)
    return {"ok": True}


# ----------------------------------------------------------------- report API

@app.get("/api/daily")
def api_daily(date: str | None = None):
    return reports.daily_report(_valid_date(date))


@app.get("/api/weekly")
def api_weekly(date: str | None = None):
    return reports.weekly_report(_valid_date(date))


# ----------------------------------------------------------------- settings API

@app.post("/settings")
def save_settings(
    wake_time: str = Form(...),
    calorie_target: int = Form(...),
    protein_target: int = Form(...),
    workouts_per_week: int = Form(...),
    water_target: int = Form(...),
    sleep_target_hours: float = Form(...),
):
    db.set_goals({
        "wake_time": wake_time,
        "calorie_target": calorie_target,
        "protein_target": protein_target,
        "workouts_per_week": workouts_per_week,
        "water_target": water_target,
        "sleep_target_hours": sleep_target_hours,
        "walk_after_lunch": 1,
    })
    return RedirectResponse("/settings", status_code=303)


@app.get("/health")
def health():
    return {"status": "ok"}
