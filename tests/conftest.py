"""Pytest fixtures: in-memory SQLite, mock Gemini, mock RSS."""
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from whipple.models import Base


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    s = Session()
    yield s
    s.close()


@pytest.fixture
def mock_gemini(monkeypatch):
    """Patch whipple.services.gemini.GeminiClient with a fake."""
    calls = []

    class FakeGemini:
        def __init__(self, *a, **kw): pass
        def classify(self, title, content):
            calls.append(("classify", title))
            return {"section": "energy_prices", "irrelevant": False, "tokens_in": 100, "tokens_out": 5}
        def summarize(self, article, section, target_words):
            calls.append(("summarize", article.id))
            return {"text": f"Mock summary for {article.title}", "tokens_in": 500, "tokens_out": 100}
        def compose(self, articles_by_section, voice_guide):
            calls.append(("compose", len(articles_by_section)))
            return {"html": "<html>mock bulletin</html>", "quote_a": "q1", "quote_b": "q2",
                    "tokens_in": 5000, "tokens_out": 9000}

    from whipple.services import gemini as gemini_mod
    monkeypatch.setattr(gemini_mod, "GeminiClient", FakeGemini)
    return calls
