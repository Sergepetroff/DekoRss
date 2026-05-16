from __future__ import annotations

import re
from dataclasses import dataclass
from html import escape
from html import unescape
from pathlib import Path
from typing import Callable

from tone_analysis import analyze_text_tone, analyze_text_tones


ToneAnalyzer = Callable[[str], dict | None]
ToneBatchAnalyzer = Callable[[list[str]], list[dict | None]]
MISSING_TONE = object()
PARAGRAPH_RE = re.compile(r"<p\b(?P<attrs>[^>]*)>(?P<inner>.*?)</p>", flags=re.I | re.S)
TONE_BADGE_RE = re.compile(
    r"\s*<span\b[^>]*class=(['\"])"
    r"[^'\"]*\btone-badge\b[^'\"]*\1[^>]*>.*?</span>\s*",
    flags=re.I | re.S,
)
HTML_TAG_RE = re.compile(r"<[^>]+>")


@dataclass(slots=True)
class ColorizeResult:
    output_path: Path
    total_paragraphs: int
    scored_paragraphs: int
    failed_paragraphs: int


@dataclass(slots=True)
class ParagraphEntry:
    attrs: str
    inner_html: str
    text: str


def read_html_file(file_path: str | Path) -> str:
    path = Path(file_path)
    for encoding in ("utf-8", "cp1251", "utf-8-sig"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def write_html_file(file_path: str | Path, html: str) -> None:
    Path(file_path).write_text(html, encoding="utf-8")


def _paragraph_style(tone: dict | None) -> tuple[str, str]:
    base_style = "padding:10px 12px;margin:10px 0;border-radius:8px;"
    if not tone:
        return (
            base_style + "background:#f3f4f6;border-left:4px solid #9ca3af;",
            "Tone unavailable",
        )

    tone_value = tone["tone"]
    intensity = abs(tone_value)
    if tone_value > 0:
        color_map = {1: ("#dbeafe", "#2563eb"), 2: ("#bfdbfe", "#1d4ed8")}
        background, border = color_map.get(intensity, ("#eff6ff", "#60a5fa"))
    elif tone_value < 0:
        color_map = {1: ("#fce7f3", "#db2777"), 2: ("#fbcfe8", "#be185d")}
        background, border = color_map.get(intensity, ("#fdf2f8", "#f472b6"))
    else:
        background, border = ("#fef3c7", "#d97706")

    label = f"Tone {tone_value:+d}"
    return (base_style + f"background:{background};border-left:4px solid {border};", label)


def _strip_html_tags(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    return " ".join(unescape(text).split())


def _remove_attr(attrs: str, attr_name: str) -> str:
    pattern = re.compile(rf"\s+{attr_name}\s*=\s*(?:\"[^\"]*\"|'[^']*')", flags=re.I)
    return pattern.sub("", attrs)


def _build_paragraph_attrs(attrs: str, style: str, tone: dict | None) -> str:
    cleaned_attrs = attrs
    for attr_name in ("style", "data-tone"):
        cleaned_attrs = _remove_attr(cleaned_attrs, attr_name)

    cleaned_attrs = cleaned_attrs.strip()
    parts: list[str] = []
    if cleaned_attrs:
        parts.append(cleaned_attrs)
    parts.append(f'style="{style}"')
    if tone:
        parts.append(f'data-tone="{tone["tone"]}"')
    else:
        parts.append('data-tone=""')
    return " " + " ".join(parts)


def _split_plain_text_paragraphs(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []

    paragraphs = [chunk.strip() for chunk in re.split(r"\n\s*\n+", normalized) if chunk.strip()]
    if paragraphs:
        return paragraphs

    return [line.strip() for line in normalized.split("\n") if line.strip()]


def _build_badge_html(label: str) -> str:
    badge_style = (
        "display:inline-block;margin-right:8px;padding:2px 8px;"
        "border-radius:999px;background:rgba(255,255,255,0.72);font-size:12px;font-weight:700;"
    )
    return f'<span class="tone-badge" style="{badge_style}">{label}</span> '


def _render_raw_paragraph(entry: ParagraphEntry) -> str:
    return f"<p{entry.attrs}>{entry.inner_html}</p>" if entry.attrs else f"<p>{entry.inner_html}</p>"


def _render_colored_paragraph(inner_html: str, tone: dict | None, attrs: str = "") -> str:
    paragraph_style, label = _paragraph_style(tone)
    paragraph_attrs = _build_paragraph_attrs(attrs, paragraph_style, tone)
    return f"<p{paragraph_attrs}>{_build_badge_html(label)}{inner_html}</p>"


def _render_document(paragraphs_html: list[str]) -> str:
    return (
        "<!DOCTYPE html>\n"
        '<html lang="ru">\n'
        "<head>\n"
        '  <meta charset="utf-8">\n'
        '  <title>Tone Colored Text</title>\n'
        "</head>\n"
        '  <body style="font-family:Segoe UI, sans-serif;max-width:900px;margin:32px auto;padding:0 16px;">\n'
        f"{'\n'.join(paragraphs_html)}\n"
        "  </body>\n"
        "</html>\n"
    )


def _chunk_entries(entries: list[ParagraphEntry], max_items: int = 8, max_chars: int = 12000) -> list[list[ParagraphEntry]]:
    chunks: list[list[ParagraphEntry]] = []
    current_chunk: list[ParagraphEntry] = []
    current_chars = 0

    for entry in entries:
        entry_chars = min(len(entry.text), 4000)
        if current_chunk and (len(current_chunk) >= max_items or current_chars + entry_chars > max_chars):
            chunks.append(current_chunk)
            current_chunk = []
            current_chars = 0
        current_chunk.append(entry)
        current_chars += entry_chars

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def _extract_plain_text_entries(text: str) -> list[ParagraphEntry]:
    return [
        ParagraphEntry(attrs="", inner_html=escape(paragraph_text), text=paragraph_text)
        for paragraph_text in _split_plain_text_paragraphs(text)
    ]


def _extract_html_entries(html: str) -> list[ParagraphEntry]:
    entries: list[ParagraphEntry] = []
    for match in PARAGRAPH_RE.finditer(html):
        inner_html = TONE_BADGE_RE.sub("", match.group("inner"))
        text = _strip_html_tags(inner_html)
        if not text:
            continue
        entries.append(ParagraphEntry(attrs=match.group("attrs"), inner_html=inner_html, text=text))
    return entries


def _resolve_tones(
    texts: list[str],
    analyzer: ToneAnalyzer | None = None,
    batch_analyzer: ToneBatchAnalyzer | None = None,
) -> list[dict | None]:
    if analyzer is not None:
        return [analyzer(text) for text in texts]
    if batch_analyzer is not None:
        return batch_analyzer(texts)
    return analyze_text_tones(texts)


def _render_plain_text_with_tones(entries: list[ParagraphEntry], tones: list[dict | None | object]) -> str:
    paragraphs_html: list[str] = []
    for entry, tone in zip(entries, tones):
        if tone is MISSING_TONE:
            paragraphs_html.append(_render_raw_paragraph(entry))
            continue
        paragraphs_html.append(_render_colored_paragraph(entry.inner_html, tone))
    return _render_document(paragraphs_html)


def _render_html_with_tones(html: str, tones: list[dict | None | object]) -> str:
    tone_iter = iter(tones)

    def replace_paragraph(match: re.Match[str]) -> str:
        attrs = match.group("attrs")
        inner_html = TONE_BADGE_RE.sub("", match.group("inner"))
        text = _strip_html_tags(inner_html)
        if not text:
            return match.group(0)

        tone = next(tone_iter, MISSING_TONE)
        if tone is MISSING_TONE:
            return f"<p{attrs}>{inner_html}</p>" if attrs else f"<p>{inner_html}</p>"
        return _render_colored_paragraph(inner_html, tone, attrs)

    return PARAGRAPH_RE.sub(replace_paragraph, html)


def colorize_paragraphs(
    html: str,
    analyzer: ToneAnalyzer | None = None,
    batch_analyzer: ToneBatchAnalyzer | None = None,
) -> str:
    if not PARAGRAPH_RE.search(html):
        if HTML_TAG_RE.search(html):
            return html
        entries = _extract_plain_text_entries(html)
        tones = _resolve_tones([entry.text for entry in entries], analyzer=analyzer, batch_analyzer=batch_analyzer)
        return _render_plain_text_with_tones(entries, list(tones))

    entries = _extract_html_entries(html)
    tones = _resolve_tones([entry.text for entry in entries], analyzer=analyzer, batch_analyzer=batch_analyzer)
    return _render_html_with_tones(html, list(tones))


def colorize_html_file(
    input_path: str | Path,
    output_path: str | Path | None = None,
    analyzer: ToneAnalyzer | None = None,
    batch_analyzer: ToneBatchAnalyzer | None = None,
) -> ColorizeResult:
    html = read_html_file(input_path)
    target_path = Path(output_path) if output_path else Path(input_path)
    is_html_input = bool(PARAGRAPH_RE.search(html))
    entries = _extract_html_entries(html) if is_html_input else _extract_plain_text_entries(html)
    tones: list[dict | None | object] = [MISSING_TONE for _ in entries]

    if not entries:
        write_html_file(target_path, html)
        return ColorizeResult(
            output_path=target_path,
            total_paragraphs=0,
            scored_paragraphs=0,
            failed_paragraphs=0,
        )

    chunks = _chunk_entries(entries)
    offset = 0
    for chunk in chunks:
        chunk_texts = [entry.text for entry in chunk]
        chunk_tones = _resolve_tones(chunk_texts, analyzer=analyzer, batch_analyzer=batch_analyzer)
        for index, tone in enumerate(chunk_tones):
            tones[offset + index] = tone
        offset += len(chunk)

        checkpoint_html = (
            _render_html_with_tones(html, tones)
            if is_html_input
            else _render_plain_text_with_tones(entries, tones)
        )
        write_html_file(target_path, checkpoint_html)

    scored_paragraphs = sum(1 for tone in tones if tone is not MISSING_TONE and tone is not None)
    failed_paragraphs = sum(1 for tone in tones if tone is None)
    return ColorizeResult(
        output_path=target_path,
        total_paragraphs=len(entries),
        scored_paragraphs=scored_paragraphs,
        failed_paragraphs=failed_paragraphs,
    )
