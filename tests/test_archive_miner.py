from pathlib import Path
from whipple.services.archive_miner import extract_sources_from_bulletin


def test_extract_sources_finds_domains_and_citations():
    fixture = Path(__file__).parent / 'fixtures' / 'sample_whipple_bulletin.html'
    if not fixture.exists():
        # Skip if fixture not present (download manually before running this test)
        import pytest
        pytest.skip('sample_whipple_bulletin.html fixture missing - download manually')
    html = fixture.read_text(encoding='utf-8')
    counter = extract_sources_from_bulletin(html)
    assert len(counter) > 0
    # Should find at least a few well-known sources
    domains = [k for k in counter if not k.startswith('cite:')]
    assert any('reuters' in d or 'bloomberg' in d or 'eia' in d for d in domains)
