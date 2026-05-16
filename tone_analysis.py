import json
import os
import re
from urllib import request

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")


def clamp_tone_score(value) -> int:
    try:
        return max(0, min(2, int(value)))
    except (TypeError, ValueError):
        return 0


def analyze_text_tone(text: str, api_key: str | None = GROQ_API_KEY, model: str = GROQ_MODEL, timeout: int = 20):
    if not api_key or not text.strip():
        return None

    payload = {
        "model": model,
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Ты анализируешь тон текста. Верни только JSON без пояснений в формате: "
                    '{"pro_male": 0..2, "pro_female": 0..2}. '
                    "0 — нейтрально, 1 — умеренно, 2 — выраженно."
                ),
            },
            {"role": "user", "content": text[:4000]},
        ],
    }
    req = request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
        content = body["choices"][0]["message"]["content"]
        json_match = re.search(r"\{.*\}", content, flags=re.S)
        if not json_match:
            return None
        tone_data = json.loads(json_match.group(0))
        return {
            "pro_male": clamp_tone_score(tone_data.get("pro_male")),
            "pro_female": clamp_tone_score(tone_data.get("pro_female")),
        }
    except Exception as error:
        print(f"GroQ tone analysis failed: {error}")
        return None


def apply_tone_style(html: str, tone: dict | None) -> str:
    if not tone:
        return html
    difference = abs(tone["pro_male"] - tone["pro_female"])
    opacity = max(0.70, 1 - (difference * 0.15))
    tone_info = f"Tone score: M{tone['pro_male']}/F{tone['pro_female']}"
    return f'<div style="opacity:{opacity:.2f}"><p><strong>{tone_info}</strong></p>{html}</div>'
