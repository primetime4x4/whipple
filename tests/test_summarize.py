from datetime import datetime
from unittest.mock import MagicMock
from whipple.models import Source, Article
from whipple.pipeline.summarize import summarize
from whipple.pipeline import scrape as scrape_mod


def test_summarize_advances_state_and_stores_text(session, monkeypatch):
    monkeypatch.setattr(scrape_mod, 'current_sunday_ct', lambda: '2099-01-04')
    src = Source(name='Reuters', url='https://r.com', source_type='rss', active=1, weight=1.0)
    session.add(src); session.commit()

    a = Article(source_id=src.id, url='https://r.com/x', title='Oil rises',
                raw_content='Crude oil rose 2% on Tuesday...', week_of='2099-01-04',
                state='SELECTED', section='energy_prices')
    session.add(a); session.commit()

    fake_gemini = MagicMock()
    fake_gemini.call.return_value = 'Crude oil rose 2% on Tuesday on supply concerns. (Reuters)'

    r = summarize(session, gemini=fake_gemini)
    session.refresh(a)
    assert r['summarized'] == 1
    assert a.state == 'SUMMARIZED'
    assert 'Crude oil rose' in a.summary_text
    assert a.summarized_at is not None


def test_summarize_uses_flash_for_briefs(session, monkeypatch):
    monkeypatch.setattr(scrape_mod, 'current_sunday_ct', lambda: '2099-01-04')
    src = Source(name='X', url='https://x.com', source_type='rss', active=1)
    session.add(src); session.commit()
    a = Article(source_id=src.id, url='https://x.com/x', title='Brief story',
                raw_content='content', week_of='2099-01-04',
                state='SELECTED', section='briefs')
    session.add(a); session.commit()

    fake_gemini = MagicMock()
    fake_gemini.call.return_value = '**Test.** Sentence. (X)'

    summarize(session, gemini=fake_gemini)
    call_kwargs = fake_gemini.call.call_args.kwargs
    assert call_kwargs['model'] == 'gemini-2.5-flash-lite'


def test_summarize_uses_pro_for_narrative(session, monkeypatch):
    monkeypatch.setattr(scrape_mod, 'current_sunday_ct', lambda: '2099-01-04')
    src = Source(name='X', url='https://x.com', source_type='rss', active=1)
    session.add(src); session.commit()
    a = Article(source_id=src.id, url='https://x.com/y', title='Narrative',
                raw_content='content', week_of='2099-01-04',
                state='SELECTED', section='climate')
    session.add(a); session.commit()

    fake_gemini = MagicMock()
    fake_gemini.call.return_value = 'Narrative paragraph here.'

    summarize(session, gemini=fake_gemini)
    call_kwargs = fake_gemini.call.call_args.kwargs
    assert call_kwargs['model'] == 'gemini-2.5-flash'
