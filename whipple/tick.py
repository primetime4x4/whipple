"""Main orchestrator - runs every cron tick."""
import sys
from datetime import datetime
from whipple.db import get_session
from whipple.models import Run, Article
from whipple.pipeline.scrape import scrape, current_sunday_ct
from whipple.pipeline.classify import classify
from whipple.pipeline.select import select
from whipple.pipeline.summarize import summarize
from whipple.services.gemini import GeminiClient


def _select_already_ran_for_week(session, week: str) -> bool:
    """Has select() already been called this week? Heuristic: any SELECTED|SKIPPED article."""
    from sqlalchemy import select as sa_select
    return session.execute(
        sa_select(Article).where(
            Article.week_of == week,
            Article.state.in_(['SELECTED', 'SKIPPED'])
        ).limit(1)
    ).scalar_one_or_none() is not None


def main():
    session = get_session()
    run = Run(mode='tick', started_at=datetime.utcnow())
    session.add(run); session.commit()

    try:
        gemini = GeminiClient()

        r1 = scrape(session)
        run.articles_scraped = r1['inserted']

        r2 = classify(session, batch_size=10, gemini=gemini)
        run.articles_classified = r2['classified']

        # Run select once per week, after Sunday 6am CT
        import zoneinfo
        now_ct = datetime.now(zoneinfo.ZoneInfo('America/Chicago'))
        week = current_sunday_ct()
        if now_ct.weekday() == 6 and now_ct.hour >= 6            and not _select_already_ran_for_week(session, week):
            r3 = select(session)
            run.articles_selected = r3['total_selected']

        r4 = summarize(session, batch_size=5, gemini=gemini)
        run.articles_summarized = r4['summarized']

        run.success = 1
    except Exception as e:
        run.success = 0
        run.error_message = str(e)[:500]
    finally:
        run.finished_at = datetime.utcnow()
        session.commit()
        _success = run.success  # capture before close() expires ORM attrs
        session.close()

    return 0 if _success else 1


if __name__ == '__main__':
    sys.exit(main())
