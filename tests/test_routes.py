import pytest
from app import create_app


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv('WHIPPLE_DATA_DIR', str(tmp_path))
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


def test_health_json_returns_ok(client):
    r = client.get('/health.json')
    assert r.status_code == 200
    assert r.json == {'status': 'ok', 'service': 'whipple', 'version': '0.1.0'}


def test_health_html_renders(client):
    r = client.get('/health')
    assert r.status_code == 200
    assert b'Pipeline Health' in r.data
