import json
import os
import re
import time
from urllib import error, request

from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")


def _extract_retry_delay(http_error: error.HTTPError, response_body: str) -> float:
    retry_after = http_error.headers.get("Retry-After") if http_error.headers else None
    if retry_after:
        try:
            return max(1.0, float(retry_after))
        except ValueError:
            pass

    message_match = re.search(r"try again in\s+(\d+(?:\.\d+)?)s", response_body, flags=re.I)
    if message_match:
        return max(1.0, float(message_match.group(1)))

    return 2.0


def clamp_tone_score(value) -> int:
    try:
        return max(0, min(2, int(value)))
    except (TypeError, ValueError):
        return 0


def _extract_json_payload(content: str, starts_with: str) -> str | None:
    if starts_with == "[":
        json_match = re.search(r"\[.*\]", content, flags=re.S)
    else:
        json_match = re.search(r"\{.*\}", content, flags=re.S)
    if not json_match:
        return None
    return json_match.group(0)


def _perform_groq_request(payload: dict, api_key: str, model: str, timeout: int, max_retries: int):
    req = request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "DekoRssToneTest/1.0",
        },
        method="POST",
    )

    for attempt in range(max_retries + 1):
        try:
            with request.urlopen(req, timeout=timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
            return body["choices"][0]["message"]["content"]
        except error.HTTPError as http_error:
            response_body = http_error.read().decode("utf-8", errors="replace")
            try:
                error_payload = json.loads(response_body)
                error_message = error_payload.get("error", {}).get("message") or response_body
            except json.JSONDecodeError:
                error_message = response_body

            if http_error.code == 429 and attempt < max_retries:
                retry_delay = _extract_retry_delay(http_error, error_message)
                print(
                    f"GroQ rate limit hit for model '{model}'. "
                    f"Retrying in {retry_delay:.1f}s ({attempt + 1}/{max_retries})..."
                )
                time.sleep(retry_delay)
                continue

            print(f"GroQ tone analysis failed ({http_error.code}) for model '{model}': {error_message}")
            return None
        except Exception as exc:
            print(f"GroQ tone analysis failed: {exc}")
            return None

    return None


def _chunk_texts(texts: list[str], max_items: int = 10, max_chars: int = 12000) -> list[list[str]]:
    chunks: list[list[str]] = []
    current_chunk: list[str] = []
    current_chars = 0

    for text in texts:
        trimmed = text[:4000]
        next_chars = current_chars + len(trimmed)
        if current_chunk and (len(current_chunk) >= max_items or next_chars > max_chars):
            chunks.append(current_chunk)
            current_chunk = []
            current_chars = 0
        current_chunk.append(trimmed)
        current_chars += len(trimmed)

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def analyze_text_tone(
    text: str,
    api_key: str | None = GROQ_API_KEY,
    model: str = GROQ_MODEL,
    timeout: int = 20,
    max_retries: int = 5,
):
    api_key = api_key.strip() if api_key else api_key
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
    content = _perform_groq_request(payload, api_key, model, timeout, max_retries)
    if not content:
        return None

    json_payload = _extract_json_payload(content, "{")
    if not json_payload:
        return None

    tone_data = json.loads(json_payload)
    return {
        "pro_male": clamp_tone_score(tone_data.get("pro_male")),
        "pro_female": clamp_tone_score(tone_data.get("pro_female")),
    }


def analyze_text_tones(
    texts: list[str],
    api_key: str | None = GROQ_API_KEY,
    model: str = GROQ_MODEL,
    timeout: int = 20,
    max_retries: int = 5,
) -> list[dict | None]:
    api_key = api_key.strip() if api_key else api_key
    normalized_texts = [text.strip() for text in texts]
    if not api_key:
        return [None for _ in normalized_texts]

    indexed_texts = [(index, text) for index, text in enumerate(normalized_texts) if text]
    results: list[dict | None] = [None for _ in normalized_texts]
    if not indexed_texts:
        return results

    chunk_map = _chunk_texts([text for _, text in indexed_texts])
    cursor = 0
    for chunk in chunk_map:
        chunk_pairs = indexed_texts[cursor: cursor + len(chunk)]
        cursor += len(chunk)
        prompt_lines = [f"[{index}] {text[:4000]}" for index, (_, text) in enumerate(chunk_pairs, start=1)]
        payload = {
            "model": model,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Ты анализируешь тон нескольких абзацев. "
                        "Верни только JSON-массив без пояснений. "
                        "Для каждого входного абзаца верни объект в том же порядке в формате "
                        '[{"pro_male": 0..2, "pro_female": 0..2}]. '
                        "Если текст нейтральный, используй 0."
                    ),
                },
                {"role": "user", "content": "\n\n".join(prompt_lines)},
            ],
        }
        content = _perform_groq_request(payload, api_key, model, timeout, max_retries)
        if not content:
            continue

        json_payload = _extract_json_payload(content, "[")
        if not json_payload:
            continue

        try:
            tone_items = json.loads(json_payload)
        except json.JSONDecodeError:
            continue

        for chunk_position, tone_item in enumerate(tone_items[: len(chunk_pairs)]):
            source_index = chunk_pairs[chunk_position][0]
            if not isinstance(tone_item, dict):
                continue
            results[source_index] = {
                "pro_male": clamp_tone_score(tone_item.get("pro_male")),
                "pro_female": clamp_tone_score(tone_item.get("pro_female")),
            }

    return results


def apply_tone_style(html: str, tone: dict | None) -> str:
    if not tone:
        return html
    difference = abs(tone["pro_male"] - tone["pro_female"])
    opacity = max(0.70, 1 - (difference * 0.15))
    tone_info = f"Tone score: M{tone['pro_male']}/F{tone['pro_female']}"
    return f'<div style="opacity:{opacity:.2f}"><p><strong>{tone_info}</strong></p>{html}</div>'
