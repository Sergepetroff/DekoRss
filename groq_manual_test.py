import argparse
import json
import sys

from tone_analysis import analyze_text_tone


def main():
    parser = argparse.ArgumentParser(description="Manual GroQ tone scoring for a paragraph.")
    parser.add_argument("text", help="Paragraph text to evaluate")
    parser.add_argument("--model", default=None, help="Optional GroQ model override")
    args = parser.parse_args()

    result = analyze_text_tone(args.text, model=args.model or "llama-3.1-8b-instant")
    if result is None:
        print("Tone analysis unavailable (missing API key, empty text, or API error).")
        return 1

    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
