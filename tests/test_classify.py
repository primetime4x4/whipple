from datetime import datetime
import pytest
from unittest.mock import MagicMock
from whipple.models import Source, Article
from whipple.pipeline.classify import classify
from whipple.pipeline import scrape as scrape_mod


def _make_article(session, title, state='SCRAPED', week='2099-01-04'):
    src = session.query(Source).first()
    if not src:
        src = Source(name='S', url='https://s.com', source_type='rss', active=1)
        session.add(src); session.commit()
    a = Article(source_id=src.id, url=f'https://s.com/{title.replace(" ","-")}',
                title=title, raw_content='content', week_of=week, state=state)
    session.add(a); session.commit()
    return a


def test_classify_advances_state_and_assigns_section(session, monkeypatch):
    monkeypatch.setattr(scrape_mod, 'current_sunday_ct', lambda: '2099-01-04')
    a = _make_article(session, 'Oil up')
    fake_gemini = MagicMock()
    fake_gemini.call.return_value = 'energy_prices'

    r = classify(session, gemini=fake_gemini)
    session.refresh(a)
    assert r['classified'] == 1
    assert a.state == 'CLASSIFIED'
    assert a.section == 'energy_prices'
    assert a.classified_at is not None


def test_classify_marks_irrelevant(session, monkeypatch):
    monkeypatch.setattr(scrape_mod, 'current_sunday_ct', lambda: '2099-01-04')
    a = _make_article(session, 'Sports recap')
    fake_gemini = MagicMock()
    fake_gemini.call.return_value = 'irrelevant'

    r = classify(session, gemini=fake_gemini)
    session.refresh(a)
    assert r['irrelevant'] == 1
    assert a.state == 'IRRELEVANT'


def test_classify_fails_on_garbage_response(session, monkeypatch):
    monkeypatch.setattr(scrape_mod, 'current_sunday_ct', lambda: '2099-01-04')
    a = _make_article(session, 'Test')
    fake_gemini = MagicMock()
    fake_gemini.call.return_value = 'BANANA'  # not a valid section

    r = classify(session, gemini=fake_gemini)
    session.refresh(a)
    assert r['failed'] == 1
    assert a.state == 'FAILED'


def test_classify_respects_batch_size(session, monkeypatch):
    monkeypatch.setattr(scrape_mod, 'current_sunday_ct', lambda: '2099-01-04')
    for i in range(15):
        _make_article(session, f'Story {i}')

    fake_gemini = MagicMock()
    fake_gemini.call.return_value = 'energy_prices'

    classify(session, batch_size=5, gemini=fake_gemini)
    classified = session.query(Article).filter_by(state='CLASSIFIED').count()
    scraped = session.query(Article).filter_by(state='SCRAPED').count()
    assert classified == 5
    assert scraped == 10
