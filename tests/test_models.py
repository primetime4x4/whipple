"""Schema + state transition tests."""
from datetime import datetime
import pytest
from whipple.models import Source, Article, Bulletin, ARTICLE_STATES


def test_source_url_unique(session):
    s1 = Source(name="EIA", url="https://eia.gov", source_type="rss")
    s2 = Source(name="EIA dup", url="https://eia.gov", source_type="rss")
    session.add(s1); session.commit()
    session.add(s2)
    with pytest.raises(Exception):
        session.commit()


def test_article_url_unique(session):
    src = Source(name="S", url="https://s.com", source_type="rss")
    session.add(src); session.commit()
    a1 = Article(source_id=src.id, url="https://s.com/x", week_of="2026-05-03")
    a2 = Article(source_id=src.id, url="https://s.com/x", week_of="2026-05-03")
    session.add(a1); session.commit()
    session.add(a2)
    with pytest.raises(Exception):
        session.commit()


def test_article_default_state_scraped(session):
    src = Source(name="S", url="https://s.com", source_type="rss")
    session.add(src); session.commit()
    a = Article(source_id=src.id, url="https://s.com/x", week_of="2026-05-03")
    session.add(a); session.commit()
    assert a.state == "SCRAPED"


def test_article_invalid_state_rejected(session):
    src = Source(name="S", url="https://s.com", source_type="rss")
    session.add(src); session.commit()
    a = Article(source_id=src.id, url="https://s.com/x", week_of="2026-05-03", state="BOGUS")
    session.add(a)
    with pytest.raises(Exception):
        session.commit()


def test_source_default_inactive(session):
    s = Source(name="S", url="https://s.com", source_type="rss")
    session.add(s); session.commit()
    assert s.active == 0


def test_bulletin_week_of_unique(session):
    b1 = Bulletin(week_of="2026-05-03")
    b2 = Bulletin(week_of="2026-05-03")
    session.add(b1); session.commit()
    session.add(b2)
    with pytest.raises(Exception):
        session.commit()
