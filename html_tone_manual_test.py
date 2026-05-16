import argparse
from pathlib import Path

from html_tone_colorizer import colorize_html_file
from tone_analysis import analyze_text_tone, analyze_text_tones


def main() -> int:
    parser = argparse.ArgumentParser(description="Colorize paragraphs in a local HTML file using tone scoring.")
    parser.add_argument("html_file", nargs="?", default="test.html", help="Path to the input HTML file")
    parser.add_argument("--output", default=None, help="Optional output HTML path. Defaults to in-place overwrite.")
    parser.add_argument("--model", default=None, help="Optional Groq model override for this run.")
    args = parser.parse_args()

    html_path = Path(args.html_file)
    if not html_path.exists():
        print(f"Input file not found: {html_path}")
        return 1

    analyzer = None
    batch_analyzer = None
    if args.model:
        analyzer = lambda text: analyze_text_tone(text, model=args.model)
        batch_analyzer = lambda texts: analyze_text_tones(texts, model=args.model)

    result = colorize_html_file(
        html_path,
        output_path=args.output,
        analyzer=analyzer,
        batch_analyzer=batch_analyzer,
    )
    print(
        f"Paragraph tones written to: {result.output_path} "
        f"(scored: {result.scored_paragraphs}/{result.total_paragraphs}, failed: {result.failed_paragraphs})"
    )
    if result.total_paragraphs > 0 and result.scored_paragraphs == 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
