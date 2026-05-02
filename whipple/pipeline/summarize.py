"""summarize() stage - Gemini writes the per-article paragraph."""
from datetime import datetime
from sqlalchemy import select as sa_select
from whipple.models import Article, Source
from whipple.services.gemini import GeminiClient, GeminiRateLimitExceeded
from whipple.prompts.summarize import render_summarize_prompt
from whipple.pipeline import scrape as scrape_mod
from config import SECTION_DISPLAY


def _linkify_source(text: str, source_name: str, article_url: str) -> str:
    """Wrap the trailing source attribution in an anchor tag.

    Gemini is instructed to end summaries with " (Source Name)". We replace
    the last occurrence of that token with a hyperlinked version pointing
    to the article URL, so the bulletin renders Tom Whipple-style "(Source)"
    citations as clickable links. If the model never inlined the
    attribution, we append a linked one.
    """
    if not article_url or not source_name:
        return text
    linked = f'<a href="{article_url}" target="_blank" rel="noopener">{source_name}</a>'
    tag = f'({source_name})'
    if tag in text:
        head, _, tail = text.rpartition(tag)
        return f'{head}({linked}){tail}'
    return f'{text} ({linked})'


def summarize(session, batch_size: int = 5, gemini: GeminiClient = None) -> dict:
    if gemini is None:
        gemini = GeminiClient()

    week = scrape_mod.current_sunday_ct()
    rows = session.execute(
        sa_select(Article, Source).join(Source).where(
            Article.state == 'SELECTED',
            Article.week_of == week,
        ).limit(batch_size)
    ).all()

    summarized = 0
    failed = 0

    for art, src in rows:
        try:
            section_display = SECTION_DISPLAY.get(art.section, art.section)
            prompt = render_summarize_prompt(
                title=art.title, source_name=src.name, url=art.url,
                content=art.raw_content, section=art.section,
                section_display=section_display,
            )
            # Briefs use Flash; narrative sections use Pro
            model = 'gemini-2.5-flash-lite' if art.section == 'briefs' else 'gemini-2.5-flash'
            text = gemini.call(model=model, prompt=prompt, stage='summarize',
                               article_id=art.id)
            text = text.strip()
            text = _linkify_source(text, src.name, art.url)
            art.summary_text = text
            art.state = 'SUMMARIZED'
            art.summarized_at = datetime.utcnow()
            summarized += 1
        except GeminiRateLimitExceeded:
            break
        except Exception as e:
            art.state = 'FAILED'
            art.error_message = str(e)[:255]
            failed += 1

    session.commit()
    return {'summarized': summarized, 'failed': failed}
