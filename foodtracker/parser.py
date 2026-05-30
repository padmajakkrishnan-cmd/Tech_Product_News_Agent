"""Claude-powered extraction of structured food & habit logs.

Takes free-form input (typed text, voice transcript, or a meal photo) and
returns structured food items (with estimated macros) and habit entries.
"""

import base64
import json
import logging
import re

import anthropic

from foodtracker.config import Config

logger = logging.getLogger(__name__)


PARSE_SYSTEM_PROMPT = """\
You are a meticulous nutrition and lifestyle-logging assistant. The user
describes, in natural language, what they ate and/or lifestyle habits they did
(waking up, sleeping, walking after lunch, workouts, water, steps, meditation).

Extract EVERYTHING mentioned into a single JSON object with this exact shape:

{
  "foods": [
    {
      "name": "scrambled eggs",
      "quantity": "2 eggs",
      "meal": "breakfast",          // breakfast | lunch | dinner | snack (best guess)
      "calories": 180,              // kcal, your best nutrition estimate for the quantity
      "protein_g": 12,
      "carbs_g": 2,
      "fat_g": 14,
      "fiber_g": 0
    }
  ],
  "habits": [
    {
      "habit_type": "wake_time",    // one of: wake_time, sleep_time, sleep_hours,
                                    //   walk_after_lunch, workout, water, steps,
                                    //   meditation, other
      "value": "06:30",            // normalised: time as HH:MM (24h), counts/amounts as a number, yes/no as "yes"
      "detail": "Woke up at 6:30am",
      "numeric": 6.5               // optional number for aggregation (e.g. hours, glasses, minutes, steps). null if N/A
    }
  ]
}

Rules:
- Estimate macros realistically for the stated quantity using standard nutrition
  knowledge. If quantity is vague, assume one typical serving and note it.
- For "walk after lunch", set value "yes" and put duration (minutes) in numeric if given.
- For "workout", detail should describe it (e.g. "30 min strength training");
  put duration in minutes in numeric if available.
- Times must be 24h HH:MM. "6:30am" -> "06:30", "10pm" -> "22:00".
- If the user only mentions food, return an empty habits array, and vice-versa.
- Do not invent items that were not mentioned.
- Return ONLY valid JSON. No markdown fences, no commentary.
"""


VISION_SYSTEM_PROMPT = """\
You are a nutrition vision assistant. You are shown a photo of a meal or food.
Identify each distinct food/drink item visible and estimate its portion and macros.

Return ONLY a JSON object of this exact shape (no markdown, no commentary):

{
  "foods": [
    {
      "name": "grilled chicken breast",
      "quantity": "approx 150g",
      "meal": "lunch",            // best guess from context, default "snack"
      "calories": 250,
      "protein_g": 46,
      "carbs_g": 0,
      "fat_g": 6,
      "fiber_g": 0
    }
  ],
  "note": "Short note on assumptions, e.g. portion sizes estimated from plate size."
}

Estimate portions from visual cues (plate size, utensils). Be realistic.
If the image clearly contains no food, return {"foods": [], "note": "No food detected"}.
"""


def _client():
    if not Config.ANTHROPIC_API_KEY:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Add it to your .env file."
        )
    return anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)


def _extract_json(text: str) -> dict:
    """Parse JSON, tolerating accidental markdown fences or surrounding prose."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise


def parse_text(text: str) -> dict:
    """Parse a typed message or voice transcript into foods + habits."""
    client = _client()
    logger.info("Parsing text log (%d chars)", len(text))
    message = client.messages.create(
        model=Config.CLAUDE_MODEL,
        max_tokens=2000,
        system=PARSE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text}],
    )
    result = _extract_json(message.content[0].text)
    result.setdefault("foods", [])
    result.setdefault("habits", [])
    return result


def parse_image(image_bytes: bytes, media_type: str, hint: str = "") -> dict:
    """Analyse a meal photo and return foods + an assumptions note."""
    client = _client()
    b64 = base64.standard_b64encode(image_bytes).decode("ascii")
    logger.info("Analysing meal photo (%d bytes, %s)", len(image_bytes), media_type)

    content = [
        {
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": b64},
        },
        {
            "type": "text",
            "text": (
                f"Analyse this meal photo. Context from the user: {hint}"
                if hint
                else "Analyse this meal photo and estimate the macros."
            ),
        },
    ]

    message = client.messages.create(
        model=Config.CLAUDE_MODEL,
        max_tokens=2000,
        system=VISION_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
    )
    result = _extract_json(message.content[0].text)
    result.setdefault("foods", [])
    result.setdefault("habits", [])
    return result
