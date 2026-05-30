# 🥗 Food & Habit Tracker

A personal web app to log your **food intake** and **lifestyle habits** (wake-up
time, walk after lunch, workouts, water, sleep…) using **voice, typing, or a
photo** — and get **daily macro reports**, AI insights, and a **weekly
discipline score**.

Powered by Claude (Anthropic) for natural-language parsing and meal-photo
analysis. Storage is a local SQLite file, so your data stays on your machine.

## Features

- **Three ways to log**
  - ⌨️ **Type** what you ate / did in plain English
  - 🎤 **Speak** it — the browser's speech-to-text fills the box, then Claude parses it
  - 📷 **Photo** of your meal — Claude vision identifies foods and estimates macros
- **Daily dashboard** — calories, protein, carbs, fat, fiber vs. your goals, plus
  AI insights on your day and which target habits you hit or missed
- **Weekly report** — a 0–100 **discipline score** with a letter grade, per-habit
  adherence bars, a per-day calorie strip, and a coach's narrative
- **Editable goals** — wake time, calorie & protein targets, workouts/week, water, sleep

## Quick start

```bash
# from the repository root
pip install -r foodtracker/requirements.txt
cp foodtracker/.env.example .env      # then edit .env and add your ANTHROPIC_API_KEY
python app.py                         # starts on http://localhost:8000
```

Open **http://localhost:8000** in your browser (Chrome/Edge recommended for voice).

> Tip: open it on your phone (same Wi-Fi, visit `http://<your-computer-ip>:8000`)
> to use the camera and microphone naturally.

## How logging works

Just describe your day naturally, e.g.:

> "Woke up at 6:30, had 2 boiled eggs and a bowl of oatmeal for breakfast,
> walked 15 minutes after lunch, did a 30 minute run, drank 6 glasses of water."

Claude extracts each **food item** (with estimated calories/protein/carbs/fat/fiber)
and each **habit** (wake time, walk after lunch, workout, water…) and stores them
under the selected date. You can delete any entry with the ✕ button.

## The weekly discipline score

Each goal contributes a weighted share of the 100-point score:

| Habit | Weight | Counts as a "hit" when… |
|-------|:------:|--------------------------|
| Wake-up on time | 20 | you woke at/before your target time |
| Workouts | 20 | sessions logged vs. your weekly goal |
| Calorie target | 20 | day's calories within ±15% of target |
| Walk after lunch | 15 | a walk-after-lunch is logged |
| Protein target | 15 | day's protein ≥ 90% of target |
| Hydration | 10 | water ≥ your daily glass goal |

Grades: **A** ≥85 · **B** ≥70 · **C** ≥55 · **D** ≥40 · **F** below.

## Project layout

```
app.py                     # run the server: python app.py
foodtracker/
  server.py                # FastAPI routes (pages + JSON API)
  parser.py                # Claude text + vision parsing
  reports.py               # macro aggregation, insights, discipline scoring
  db.py                    # SQLite storage
  config.py                # settings, default goals, habit types
  templates/               # Jinja2 HTML (today, weekly, goals)
  static/                  # style.css, app.js (voice + photo capture)
```

## API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/log/text` | Parse typed/voice text → store foods & habits |
| `POST` | `/api/log/photo` | Analyse a meal photo → store foods |
| `GET`  | `/api/daily?date=YYYY-MM-DD` | Daily report JSON |
| `GET`  | `/api/weekly?date=YYYY-MM-DD` | Weekly report JSON |
| `DELETE` | `/api/food/{id}` · `/api/habit/{id}` | Delete an entry |

## Notes

- Macro and portion numbers are **AI estimates** — great for trends and awareness,
  not a substitute for precise measurement.
- Voice uses the browser's built-in Web Speech API (no extra key). It works best in
  Chrome/Edge; if unsupported, typing and photo still work.
