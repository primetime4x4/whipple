"""Sunday 9pm finalize - runs compose() + sends email."""
import sys
import requests
from datetime import datetime
from whipple.db import get_session
from whipple.models import Run, Bulletin
from whipple.pipeline.compose import compose
from whipple.pipeline.scrape import current_sunday_ct
from whipple.services.gemini import GeminiClient
from whipple.services.gmail import send_bulletin
from config import CORTEX_BASE_URL, CORTEX_API_KEY


def _notify(severity: str, title: str, body: str) -> None:
    if not CORTEX_BASE_URL or not CORTEX_API_KEY:
        return
    try:
        requests.post(
            f'{CORTEX_BASE_URL}/api/notify',
            headers={'X-API-Key': CORTEX_API_KEY},
            json={'severity': severity, 'title': title, 'body': body, 'source': 'whipple'},
            timeout=10,
        )
    except Exception:
        pass


def main():
    session = get_session()
    run = Run(mode='finalize', started_at=datetime.utcnow())
    session.add(run); session.commit()

    try:
        gemini = GeminiClient()
        r = compose(session, gemini=gemini)
        if r.get('composed', 0) == 0:
            run.success = 0
            run.error_message = r.get('reason', 'no articles to compose')
            _notify('warn', 'Whipple: nothing to send',
                    'No SUMMARIZED articles found for current week.')
            return 1

        # Send the bulletin
        week = current_sunday_ct()
        bulletin = session.query(Bulletin).filter_by(week_of=week).first()
        subject = f'Energy Bulletin Weekly - {datetime.fromisoformat(week).strftime(%B %-d, %Y)}'
        msg_id = send_bulletin(subject=subject, html=bulletin.html_content)

        bulletin.status = 'SENT'
        bulletin.sent_at = datetime.utcnow()
        run.articles_composed = r['composed']
        run.success = 1
        session.commit()

        _notify('info', 'Whipple bulletin sent',
                f'{r[composed]} articles, {bulletin.total_word_count} words. Gmail msg id: {msg_id}.')
    except Exception as e:
        run.success = 0
        run.error_message = str(e)[:500]
        _notify('warn', 'Whipple bulletin FAILED', str(e)[:500])
    finally:
        run.finished_at = datetime.utcnow()
        session.commit()
        session.close()

    return 0 if run.success else 1


if __name__ == '__main__':
    sys.exit(main())
