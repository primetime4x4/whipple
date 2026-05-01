"""select() stage - heuristic ranking + top N per section."""
from datetime import datetime, timedelta
from sqlalchemy import select as sa_select
from whipple.models import Article, Source
from whipple.pipeline import scrape as scrape_mod
from config import SECTION_QUOTAS


def _score(article: Article, source: Source, now: datetime) -> float:
    # Recency: 0..1, newer = higher (decays over 7 days)
    if article.published_at:
        age_hours = (now - article.published_at).total_seconds() / 3600
        recency = max(0.0, 1.0 - age_hours / (7 * 24))
    else:
        # Use scraped_at as fallback
        age_hours = (now - article.scraped_at).total_seconds() / 3600
        recency = max(0.0, 1.0 - age_hours / (7 * 24))

    return recency * source.weight


def _diversity_penalty(article: Article, already_selected: list) -> float:
    """Penalize titles that share many words with already-selected article in same section."""
    if not article.title:
        return 1.0
    a_words = set(article.title.lower().split())
    for sel in already_selected:
        if not sel.title:
            continue
        s_words = set(sel.title.lower().split())
        overlap = len(a_words & s_words)
        if overlap >= 3 and overlap / max(len(a_words), 1) > 0.5:
            return 0.5  # heavy penalty for near-duplicate
    return 1.0


def select(session) -> dict:
    """Run selection for current week. Sets SELECTED / SKIPPED states."""
    week = scrape_mod.current_sunday_ct()
    now = datetime.utcnow()

    counts = {section: 0 for section in SECTION_QUOTAS}

    for section, quota in SECTION_QUOTAS.items():
        candidates = session.execute(
            sa_select(Article, Source).join(Source).where(
                Article.state == 'CLASSIFIED',
                Article.section == section,
                Article.week_of == week,
            )
        ).all()

        # Score
        scored = [(art, src, _score(art, src, now)) for art, src in candidates]
        scored.sort(key=lambda x: x[2], reverse=True)

        selected = []
        for art, src, base_score in scored:
            penalty = _diversity_penalty(art, selected)
            final = base_score * penalty
            art.score = final
            if len(selected) < quota and penalty == 1.0:
                selected.append(art)
                art.state = 'SELECTED'
                counts[section] += 1
            else:
                art.state = 'SKIPPED'

    session.commit()
    return {'selected_by_section': counts, 'total_selected': sum(counts.values())}
