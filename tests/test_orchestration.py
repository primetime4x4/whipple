from unittest.mock import patch, MagicMock
from whipple.models import Source, Article, Run


def test_tick_logs_run_with_counts(session, monkeypatch):
    monkeypatch.setattr('whipple.tick.get_session', lambda: session)
    monkeypatch.setattr('whipple.tick.scrape', lambda s: {'inserted': 3})
    monkeypatch.setattr('whipple.tick.classify', lambda s, batch_size, gemini: {'classified': 2})
    monkeypatch.setattr('whipple.tick.summarize', lambda s, batch_size, gemini: {'summarized': 1})
    monkeypatch.setattr('whipple.tick.GeminiClient', lambda: MagicMock())

    from whipple.tick import main
    rc = main()
    runs = session.query(Run).all()
    assert len(runs) == 1
    assert runs[0].mode == 'tick'
    assert runs[0].articles_scraped == 3
    assert runs[0].articles_classified == 2
    assert runs[0].success == 1
