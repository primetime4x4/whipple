"""compose() stage - assembles the bulletin from SUMMARIZED articles.

Pure deterministic: groups summaries by section, renders h2 + paragraphs,
returns. No LLM call. Earlier attempts to keep an LLM in compose (full
bulletin generation, then just quote extraction) hit timeouts on gemma3:4b
and ate Gemini quota. The summaries already have source attribution and
inline links from the summarize stage, so deterministic stitching is enough
to produce a complete bulletin.

Quotes of the Week and Graphic of the Week sections are skipped for now;
they can be added later via heuristic extraction from raw_content (regex
for quoted sentences, regex for first <img>) without an LLM call.
"""
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

    article_count = sum(len(v) for v in summaries_by_section.values())
    total_words = sum(len((s or '').split()) for s in
                      [a.summary_text for a, _ in rows])

    html = render_bulletin(
        week_of=week,
        assembled_html=assembled_html,
        quote_a=None,
        quote_b=None,
        graphic_url=None,
        graphic_caption=None,
        article_count=article_count,
        total_word_count=total_words,
    )

    bulletin = Bulletin(
        week_of=week, status='COMPOSED', generated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        html_content=html,
        article_count=article_count, total_word_count=total_words,
    )
    session.add(bulletin); session.flush()

    for art, _ in rows:
        art.state = 'COMPOSED'
        art.bulletin_id = bulletin.id

    session.commit()
    save_archive(week, html)
    return {'composed': article_count, 'bulletin_id': bulletin.id}
