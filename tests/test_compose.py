"""compose() is fully deterministic since 2026-05-02 - no LLM call.

Earlier versions made one giant Gemini call producing JSON {html, quote_a,
quote_b, graphic_url, ...} but that hit timeouts on local Ollama and burned
scarce free-tier Gemini quota. The summaries already carry source attribution
and inline links from the summarize stage, so compose just groups them by
section and renders h2 + paragraphs (or ul/li for briefs). Quotes of the Week
are extracted heuristically via regex over raw_content.
"""
from whipple.models import Source, Article, Bulletin
from whipple.pipeline.compose import compose, _extract_quotes, _is_prose_quote
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

    r = compose(session)
    assert r['composed'] == 3
    bulletin = session.query(Bulletin).first()
    assert bulletin is not None
    assert bulletin.status == 'COMPOSED'
    # Deterministic compose stitches summaries verbatim under section h2
    assert 'Summary 0' in bulletin.html_content
    assert 'Summary 1' in bulletin.html_content
    assert 'Summary 2' in bulletin.html_content
    assert 'Energy prices and production' in bulletin.html_content

    composed_articles = session.query(Article).filter_by(state='COMPOSED').count()
    assert composed_articles == 3


def test_compose_extracts_prose_quotes_from_raw_content(session, monkeypatch, tmp_path):
    """Quotes of the Week heuristic: regex over cleaned raw_content."""
    monkeypatch.setattr(scrape_mod, 'current_sunday_ct', lambda: '2099-01-04')
    monkeypatch.setattr('whipple.services.render.save_archive',
                        lambda w, h, base_dir=str(tmp_path): tmp_path / f'{w}.html')

    src = Source(name='S', url='https://s.com', source_type='rss', active=1)
    session.add(src); session.commit()

    a = Article(
        source_id=src.id, url='https://s.com/quoted', title='Big news',
        raw_content='The official said, "We will not yield on this point under any circumstance." '
                    'It marked a turning point in the negotiations.',
        week_of='2099-01-04', state='SUMMARIZED', section='geopolitical',
        summary_text='A major statement was made.',
    )
    session.add(a); session.commit()

    compose(session)
    bulletin = session.query(Bulletin).first()
    assert bulletin is not None
    assert bulletin.quote_a is not None
    assert 'will not yield' in bulletin.quote_a


def test_extract_quotes_filters_html_attribute_fragments(session):
    """Junk inside HTML attributes should not survive the prose filter."""
    src = Source(name='S', url='https://s.com', source_type='rss', active=1)
    session.add(src); session.commit()
    a = Article(
        source_id=src.id, url='https://s.com/x', title='x',
        raw_content='<a href="https://example.com" class="external">example</a>',
        week_of='2099-01-04', state='SUMMARIZED', section='climate',
        summary_text='Something.',
    )
    session.add(a); session.commit()
    quote_a, quote_b = _extract_quotes([(a, src)])
    assert quote_a is None
    assert quote_b is None


def test_is_prose_quote_rejects_short_fragments():
    assert not _is_prose_quote('foo')
    assert not _is_prose_quote('comprehensive legislative package')  # 3 spaces
    assert not _is_prose_quote('<href="x">link</a>')
    assert _is_prose_quote('We will not yield on this point under any circumstance.')
