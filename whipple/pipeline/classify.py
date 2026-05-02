"""classify() stage - Gemini Flash assigns each SCRAPED article to a section."""
from datetime import datetime
from sqlalchemy import select
from whipple.models import Article
from whipple.services.gemini import GeminiClient, GeminiRateLimitExceeded
from whipple.prompts.classify import render_classify_prompt
from whipple.pipeline import scrape as scrape_mod
from whipple.models import SECTIONS

VALID_SECTIONS_OR_IRRELEVANT = set(SECTIONS) | {'irrelevant'}


def classify(session, batch_size: int = 10, gemini: GeminiClient = None) -> dict:
    """Classify a batch of SCRAPED articles. Returns counts."""
    if gemini is None:
        gemini = GeminiClient()

    week = scrape_mod.current_sunday_ct()
    arts = session.execute(
        select(Article).where(
            Article.state == 'SCRAPED',
            Article.week_of == week,
        ).limit(batch_size)
    ).scalars().all()

    classified = 0
    irrelevant = 0
    failed = 0

    for art in arts:
        try:
            prompt = render_classify_prompt(art.title, art.raw_content)
            resp = gemini.call(model='gemini-2.5-flash-lite', prompt=prompt,
                              stage='classify', article_id=art.id)
            section_raw = resp.strip().lower()
            if section_raw not in VALID_SECTIONS_OR_IRRELEVANT:
                # fallback: model returned something weird
                art.state = 'FAILED'
                art.error_message = f'classify returned unrecognized section: {section_raw[:80]}'
                failed += 1
                continue

            if section_raw == 'irrelevant':
                art.state = 'IRRELEVANT'
                irrelevant += 1
            else:
                art.state = 'CLASSIFIED'
                art.section = section_raw
                art.classified_at = datetime.utcnow()
                classified += 1
        except GeminiRateLimitExceeded:
            break  # bail batch, next tick retries
        except Exception as e:
            art.state = 'FAILED'
            art.error_message = str(e)[:255]
            failed += 1

    session.commit()
    return {'classified': classified, 'irrelevant': irrelevant, 'failed': failed}
