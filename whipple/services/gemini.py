"""Gemini API wrapper with rate limiting + retry + call logging."""
import time
from datetime import datetime, timedelta
from typing import Optional
import google.genai as genai
from sqlalchemy import func, select
from whipple.db import get_session
from whipple.models import GeminiCall
from config import GEMINI_API_KEY, GEMINI_RPM_LIMIT, GEMINI_RPD_LIMIT


class GeminiRateLimitExceeded(Exception):
    pass


class GeminiClient:
    def __init__(self, api_key: str = None):
        self.client = genai.Client(api_key=api_key or GEMINI_API_KEY)

    def _check_rate_limits(self, session) -> None:
        """Raise GeminiRateLimitExceeded if RPM or RPD breached."""
        now = datetime.utcnow()
        rpm = session.execute(
            select(func.count()).select_from(GeminiCall).where(
                GeminiCall.called_at > now - timedelta(minutes=1)
            )
        ).scalar()
        rpd = session.execute(
            select(func.count()).select_from(GeminiCall).where(
                GeminiCall.called_at > now - timedelta(days=1)
            )
        ).scalar()
        if rpm >= GEMINI_RPM_LIMIT:
            raise GeminiRateLimitExceeded(f'RPM limit hit: {rpm}/{GEMINI_RPM_LIMIT}')
        if rpd >= GEMINI_RPD_LIMIT:
            raise GeminiRateLimitExceeded(f'RPD limit hit: {rpd}/{GEMINI_RPD_LIMIT}')

    def _log_call(self, session, stage: str, model: str, input_tokens: int,
                  output_tokens: int, latency_ms: int, article_id: Optional[int] = None,
                  bulletin_id: Optional[int] = None, success: bool = True,
                  error_message: Optional[str] = None) -> None:
        session.add(GeminiCall(
            stage=stage, model=model, input_tokens=input_tokens,
            output_tokens=output_tokens, latency_ms=latency_ms,
            article_id=article_id, bulletin_id=bulletin_id,
            success=1 if success else 0, error_message=error_message,
        ))
        session.commit()

    def call(self, model: str, prompt: str, stage: str,
             article_id: Optional[int] = None, bulletin_id: Optional[int] = None,
             max_retries: int = 3) -> str:
        """Call Gemini with rate-limit guard + retry. Returns text response."""
        session = get_session()
        try:
            self._check_rate_limits(session)
        except GeminiRateLimitExceeded:
            raise

        last_exc = None
        for attempt in range(max_retries):
            try:
                start = time.time()
                resp = self.client.models.generate_content(model=model, contents=prompt)
                latency = int((time.time() - start) * 1000)
                text = resp.text
                input_tokens = resp.usage_metadata.prompt_token_count if hasattr(resp, 'usage_metadata') else 0
                output_tokens = resp.usage_metadata.candidates_token_count if hasattr(resp, 'usage_metadata') else 0
                self._log_call(session, stage, model, input_tokens, output_tokens,
                               latency, article_id, bulletin_id, True)
                return text
            except Exception as e:
                last_exc = e
                if attempt < max_retries - 1:
                    time.sleep(2 ** (attempt + 1))  # 2, 8, 32

        # all retries exhausted
        self._log_call(session, stage, model, 0, 0, 0, article_id, bulletin_id,
                       False, str(last_exc))
        raise last_exc
