from datetime import datetime, timedelta
from whipple.models import Source, Article
from whipple.pipeline.select import select
from whipple.pipeline import scrape as scrape_mod


def test_select_picks_top_n_per_section(session, monkeypatch):
    monkeypatch.setattr(scrape_mod, 'current_sunday_ct', lambda: '2099-01-04')
    src = Source(name='S', url='https://s.com', source_type='rss', active=1, weight=1.0)
    session.add(src); session.commit()

    # 15 candidates in energy_prices (quota = 10)
    for i in range(15):
        a = Article(source_id=src.id, url=f'https://s.com/{i}', title=f'Story {i}',
                    state='CLASSIFIED', section='energy_prices', week_of='2099-01-04',
                    published_at=datetime.utcnow() - timedelta(hours=i))
        session.add(a)
    session.commit()

    r = select(session)
    assert r['selected_by_section']['energy_prices'] == 10
    selected = session.query(Article).filter_by(state='SELECTED').count()
    skipped = session.query(Article).filter_by(state='SKIPPED').count()
    assert selected == 10
    assert skipped == 5


def test_select_respects_recency_for_ordering(session, monkeypatch):
    monkeypatch.setattr(scrape_mod, 'current_sunday_ct', lambda: '2099-01-04')
    src = Source(name='S', url='https://s.com', source_type='rss', active=1, weight=1.0)
    session.add(src); session.commit()

    old = Article(source_id=src.id, url='https://s.com/old', title='Old story',
                  state='CLASSIFIED', section='climate', week_of='2099-01-04',
                  published_at=datetime.utcnow() - timedelta(days=6))
    new = Article(source_id=src.id, url='https://s.com/new', title='New story',
                  state='CLASSIFIED', section='climate', week_of='2099-01-04',
                  published_at=datetime.utcnow() - timedelta(hours=2))
    session.add_all([old, new]); session.commit()

    select(session)
    session.refresh(new); session.refresh(old)
    assert new.score > old.score


def test_select_diversity_penalty_drops_near_duplicate(session, monkeypatch):
    monkeypatch.setattr(scrape_mod, 'current_sunday_ct', lambda: '2099-01-04')
    src = Source(name='S', url='https://s.com', source_type='rss', active=1, weight=1.0)
    session.add(src); session.commit()

    a = Article(source_id=src.id, url='https://s.com/a',
                title='Saudi Aramco profits surge in Q1',
                state='CLASSIFIED', section='energy_prices', week_of='2099-01-04',
                published_at=datetime.utcnow())
    b = Article(source_id=src.id, url='https://s.com/b',
                title='Saudi Aramco profits surge in Q1 report',
                state='CLASSIFIED', section='energy_prices', week_of='2099-01-04',
                published_at=datetime.utcnow())
    session.add_all([a, b]); session.commit()

    select(session)
    states = sorted([session.query(Article).get(a.id).state,
                     session.query(Article).get(b.id).state])
    assert 'SELECTED' in states
    assert 'SKIPPED' in states  # one of them gets penalty-skipped
