"""compose() stage - single big Gemini Pro call assembles full bulletin."""
import json
from datetime import datetime
from sqlalchemy import select as sa_select
from whipple.models import Article, Bulletin, Source
from whipple.services.gemini import GeminiClient
from whipple.services.render import render_bulletin, save_archive
from whipple.prompts.compose import render_compose_prompt
from whipple.pipeline import scrape as scrape_mod


def compose(session, gemini: GeminiClient = None) -> dict:
    """Compose bulletin from all SUMMARIZED articles for current week."""
    if gemini is None:
        gemini = GeminiClient()

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
    corpus = []
    for art, src in rows:
        summaries_by_section.setdefault(art.section, []).append(art.summary_text)
        corpus.append({'url': art.url, 'title': art.title or '',
                       'content': (art.raw_content or '')[:1500]})

    prompt = render_compose_prompt(week, summaries_by_section, corpus)
    raw = gemini.call(model='gemini-1.5-pro', prompt=prompt, stage='compose')

    # Strip code fences if Gemini added them
    raw = raw.strip()
    if raw.startswith('```'):
        raw = raw.split(chr(10), 1)[1].rsplit('```', 1)[0].strip()

    parsed = json.loads(raw)

    # Compute counts
    article_count = sum(len(v) for v in summaries_by_section.values())
    total_words = sum(len((s or '').split()) for s in
                      [a.summary_text for a, _ in rows])

    html = render_bulletin(
        week_of=week,
        assembled_html=parsed.get('html', ''),
        quote_a=parsed.get('quote_a'),
        quote_b=parsed.get('quote_b'),
        graphic_url=parsed.get('graphic_url'),
        graphic_caption=parsed.get('graphic_caption'),
        article_count=article_count,
        total_word_count=total_words,
    )

    bulletin = Bulletin(
        week_of=week, status='COMPOSED', generated_at=datetime.utcnow(),
        html_content=html, quote_a=parsed.get('quote_a'),
        quote_b=parsed.get('quote_b'), graphic_url=parsed.get('graphic_url'),
        graphic_caption=parsed.get('graphic_caption'),
        article_count=article_count, total_word_count=total_words,
    )
    session.add(bulletin); session.flush()

    for art, _ in rows:
        art.state = 'COMPOSED'
        art.bulletin_id = bulletin.id

    session.commit()
    save_archive(week, html)
    return {'composed': article_count, 'bulletin_id': bulletin.id}
