"""Scrape stage tests."""
from pathlib import Path
import feedparser
import pytest
from whipple.models import Source, Article
from whipple.pipeline.scrape import scrape, current_sunday_ct, _scrape_rss


# Capture the real feedparser.parse before any monkeypatch can swap it out
_REAL_FEEDPARSER_PARSE = feedparser.parse


def test_current_sunday_ct_returns_iso_date():
    s = current_sunday_ct()
    assert len(s) == 10 and s[4] == '-' and s[7] == '-'


def test_scrape_rss_dedupes_on_url(session, monkeypatch):
    src = Source(name='Test', url='file://test', source_type='rss', active=1)
    session.add(src); session.commit()

    fixture = Path(__file__).parent / 'fixtures' / 'sample_rss.xml'

    def fake_parse(url):
        # Call the captured original, not the patched name (which would recurse)
        return _REAL_FEEDPARSER_PARSE(str(fixture))
    monkeypatch.setattr('whipple.pipeline.scrape.feedparser.parse', fake_parse)

    r1 = scrape(session)
    assert r1['inserted'] == 2

    # Second run: same URLs, no inserts
    r2 = scrape(session)
    assert r2['inserted'] == 0

    arts = session.query(Article).all()
    assert len(arts) == 2
    assert all(a.state == 'SCRAPED' for a in arts)


def test_scrape_increments_failures(session, monkeypatch):
    src = Source(name='Test', url='https://broken.example', source_type='rss',
                 active=1, consecutive_failures=0)
    session.add(src); session.commit()

    def fake_parse(url):
        raise ConnectionError('boom')
    monkeypatch.setattr('whipple.pipeline.scrape.feedparser.parse', fake_parse)

    scrape(session)
    session.refresh(src)
    assert src.consecutive_failures == 1
    assert src.active == 1  # not yet auto-deactivated

    scrape(session); scrape(session)
    session.refresh(src)
    assert src.consecutive_failures == 3
    assert src.active == 0  # auto-deactivated after 3
