def test_archives_page_loads(page):
    page.goto('http://192.168.86.204:28813/archives')
    assert 'Archive' in page.title() or 'Whipple' in page.title()


def test_sources_page_loads(page):
    page.goto('http://192.168.86.204:28813/sources')
    assert 'Sources' in page.title() or 'Whipple' in page.title()


def test_health_page_renders_metrics(page):
    page.goto('http://192.168.86.204:28813/health')
    assert page.locator('text=Article counts').count() > 0


def test_manual_requires_phrase(page):
    page.goto('http://192.168.86.204:28813/manual')
    assert page.locator('text=Trigger phrase').count() > 0


def test_rss_returns_xml(page):
    response = page.request.get('http://192.168.86.204:28813/rss')
    assert response.status == 200
    assert 'rss' in response.headers.get('content-type', '').lower() or            '<rss' in response.text()
