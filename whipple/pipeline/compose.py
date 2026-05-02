"""compose() stage - assembles the bulletin from SUMMARIZED articles.

Pure deterministic: groups summaries by section, renders h2 + paragraphs,
returns. No LLM call. Earlier attempts to keep an LLM in compose (full
bulletin generation, then just quote extraction) hit timeouts on gemma3:4b
and ate Gemini quota. The summaries already have source attribution and
inline links from the summarize stage, so deterministic stitching is enough
to produce a complete bulletin.

Quotes of the Week are extracted heuristically: regex over each article's
raw_content for sentences containing quotation marks, pick the two longest
distinct quotes from different sources. No LLM call. Graphic of the Week
is still deferred (would need image-URL extraction + first-paragraph caption).
"""
import re
from datetime import datetime, timezone
from sqlalchemy import select as sa_select
from whipple.models import Article, Bulletin, Source
from whipple.services.gemini import GeminiClient
from whipple.services.render import render_bulletin, save_archive
from whipple.pipeline import scrape as scrape_mod
from config import SECTION_DISPLAY


SECTION_ORDER = [
    'energy_prices', 'geopolitical', 'climate', 'global_economy',
    'renewables', 'briefs',
]


# Quote extraction: match curly or straight double quotes wrapping prose-like
# strings 40-300 chars. raw_content is HTML, so we strip tags + URLs + entities
# first; then we pattern-match on the cleaned text and reject matches that look
# like attribute fragments or aren't sentence-shaped.
_QUOTE_RE = re.compile(r'[“"]([^“”"]{30,300})[”"]')
_HTML_TAG_RE = re.compile(r'<[^>]+>')
_URL_RE = re.compile(r'https?://\S+')
_ENTITY_RE = re.compile(r'&[a-z#0-9]+;', re.IGNORECASE)
_WHITESPACE_RE = re.compile(r'\s+')


def _clean_text(html: str) -> str:
    if not html:
        return ''
    text = _HTML_TAG_RE.sub(' ', html)
    text = _URL_RE.sub(' ', text)
    text = _ENTITY_RE.sub(' ', text)
    return _WHITESPACE_RE.sub(' ', text).strip()


def _is_prose_quote(text: str) -> bool:
    """Loose filter: must start with a letter, contain enough words, end with
    sentence-final punctuation, and not contain HTML/URL leakage."""
    if any(c in text for c in '<>{}/'):
        return False
    if text.count(' ') < 5:
        return False
    if not text[0].isalpha():
        return False
    if text[-1] not in '.!?,;':
        return False
    return True


def _extract_quotes(rows) -> tuple[str | None, str | None]:
    """Pick two striking quotes from the article corpus by length.

    For each article, strip raw_content to plain text, harvest double-quoted
    strings 40-300 chars, filter to prose-like ones, dedupe across sources,
    prefer different sources, return the two longest. (None, None) on no hit.
    """
    candidates = []  # (length, text, source_name)
    seen = set()
    for art, src in rows:
        clean = _clean_text(art.raw_content or '')
        for m in _QUOTE_RE.finditer(clean):
            text = m.group(1).strip()
            if text in seen or not _is_prose_quote(text):
                continue
            seen.add(text)
            candidates.append((len(text), text, src.name))
    if not candidates:
        return None, None
    candidates.sort(reverse=True)
    quote_a = candidates[0][1]
    a_src = candidates[0][2]
    quote_b = next((c[1] for c in candidates[1:] if c[2] != a_src), None)
    if quote_b is None and len(candidates) > 1:
        quote_b = candidates[1][1]
    return quote_a, quote_b


def _render_assembled_html(summaries_by_section: dict) -> str:
    """Build the bulletin body HTML deterministically from per-section summaries."""
    parts = []
    section_keys = [k for k in SECTION_ORDER if k in summaries_by_section]
    for k in summaries_by_section:
        if k not in section_keys:
            section_keys.append(k)

    for section in section_keys:
        items = summaries_by_section[section]
        if not items:
            continue
        display = SECTION_DISPLAY.get(section, section)
        parts.append(f'<h2>{display}</h2>')
        if section == 'briefs':
            parts.append('<ul class="briefs">')
            for s in items:
                parts.append(f'<li>{s}</li>')
            parts.append('</ul>')
        else:
            for s in items:
                parts.append(f'<p>{s}</p>')
    return '\n'.join(parts)


def compose(session, gemini: GeminiClient = None) -> dict:
    week = scrape_mod.current_sunday_ct()

    rows = session.execute(
        sa_select(Article, Source).join(Source).where(
            Article.state == 'SUMMARIZED',
            Article.week_of == week,
        )
    ).all()

    if not rows:
        return {'composed': 0, 'reason': 'no SUMMARIZED articles for current week'}

    summaries_by_section = {}
    for art, src in rows:
        summaries_by_section.setdefault(art.section, []).append(art.summary_text)

    assembled_html = _render_assembled_html(summaries_by_section)
    quote_a, quote_b = _extract_quotes(rows)

    article_count = sum(len(v) for v in summaries_by_section.values())
    total_words = sum(len((s or '').split()) for s in
                      [a.summary_text for a, _ in rows])

    html = render_bulletin(
        week_of=week,
        assembled_html=assembled_html,
        quote_a=quote_a,
        quote_b=quote_b,
        graphic_url=None,
        graphic_caption=None,
        article_count=article_count,
        total_word_count=total_words,
    )

    bulletin = Bulletin(
        week_of=week, status='COMPOSED', generated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        html_content=html,
        quote_a=quote_a, quote_b=quote_b,
        article_count=article_count, total_word_count=total_words,
    )
    session.add(bulletin); session.flush()

    for art, _ in rows:
        art.state = 'COMPOSED'
        art.bulletin_id = bulletin.id

    session.commit()
    save_archive(week, html)
    return {'composed': article_count, 'bulletin_id': bulletin.id}
