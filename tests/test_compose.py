import json
from unittest.mock import MagicMock
from whipple.models import Source, Article, Bulletin
from whipple.pipeline.compose import compose
from whipple.pipeline import scrape as scrape_mod


def test_compose_creates_bulletin_and_advances_state(session, monkeypatch, tmp_path):
    monkeypatch.setattr(scrape_mod, 'current_sunday_ct', lambda: '2099-01-04')
    monkeypatch.setattr('whipple.services.render.save_archive',
                        lambda w, h, base_dir=str(tmp_path): tmp_path / f'{w}.html')

    src = Source(name='S', url='https://s.com', source_type='rss', active=1)
    session.add(src); session.commit()

    for i in range(3):
        a = Article(source_id=src.id, url=f'https://s.com/{i}', title=f'Story {i}',
                    raw_content='content', week_of='2099-01-04',
                    state='SUMMARIZED', section='energy_prices',
                    summary_text=f'Summary {i}.')
        session.add(a)
    session.commit()

    fake_gemini = MagicMock()
    fake_gemini.call.return_value = json.dumps({
        'quote_a': 'Q1', 'quote_b': 'Q2',
        'graphic_url': None, 'graphic_caption': None,
        'html': '<h2>Energy prices and production</h2><p>Story 0.</p><p>Story 1.</p><p>Story 2.</p>',
    })

    r = compose(session, gemini=fake_gemini)
    assert r['composed'] == 3
    bulletin = session.query(Bulletin).first()
    assert bulletin is not None
    assert bulletin.status == 'COMPOSED'
    assert 'Story 0' in bulletin.html_content
    assert bulletin.quote_a == 'Q1'

    composed_articles = session.query(Article).filter_by(state='COMPOSED').count()
    assert composed_articles == 3
