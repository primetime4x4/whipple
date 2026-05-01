"""Rate limiter behavior."""
from datetime import datetime, timedelta
import pytest
from whipple.models import GeminiCall
from whipple.services.gemini import GeminiClient, GeminiRateLimitExceeded


def test_rate_limit_blocks_at_rpm_threshold(session, monkeypatch):
    # Insert 14 recent gemini_calls
    now = datetime.utcnow()
    for i in range(14):
        session.add(GeminiCall(stage='classify', model='flash',
                               called_at=now - timedelta(seconds=i*2)))
    session.commit()

    client = GeminiClient(api_key='dummy')
    monkeypatch.setattr('whipple.services.gemini.get_session', lambda: session)

    with pytest.raises(GeminiRateLimitExceeded):
        client._check_rate_limits(session)


def test_rate_limit_passes_below_threshold(session, monkeypatch):
    # Insert 5 recent gemini_calls (below 14 RPM)
    now = datetime.utcnow()
    for i in range(5):
        session.add(GeminiCall(stage='classify', model='flash',
                               called_at=now - timedelta(seconds=i*2)))
    session.commit()

    client = GeminiClient(api_key='dummy')
    client._check_rate_limits(session)  # should not raise
