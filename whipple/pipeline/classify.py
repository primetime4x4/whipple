"""classify() stage - assigns each SCRAPED article to a section.

Default backend: local Ollama (gemma3:4b) when OLLAMA_URL is set in config.
Falls back to Gemini when Ollama is unreachable. Local backend is preferred
because Whipple has many articles per week (>100 typical) and Gemini's
free-tier daily quota for flash-lite is too tight to cover them all.
"""
import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from sqlalchemy import select
from whipple.models import Article, GeminiCall
from whipple.services.gemini import GeminiClient, GeminiRateLimitExceeded
from whipple.prompts.classify import render_classify_prompt
from whipple.pipeline import scrape as scrape_mod
from whipple.models import SECTIONS

VALID_SECTIONS_OR_IRRELEVANT = set(SECTIONS) | {'irrelevant'}

OLLAMA_MODEL = 'gemma3:4b'


def _call_ollama(url: str, prompt: str, timeout: int = 90) -> tuple[str, int, int, int]:
    """Call Ollama's generate endpoint. Returns (text, input_tok, output_tok, latency_ms).

    Raises urllib.error.URLError on network failure (caller should fall back).
    """
    payload = json.dumps({
        'model': OLLAMA_MODEL,
        'prompt': prompt,
        'stream': False,
        'options': {'temperature': 0.1},
    }).encode()
    req = urllib.request.Request(
        f'{url.rstrip("/")}/api/generate',
        data=payload,
        headers={'Content-Type': 'application/json'},
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read())
    latency = int((time.time() - t0) * 1000)
    return (
        data.get('response', '').strip(),
        int(data.get('prompt_eval_count', 0)),
        int(data.get('eval_count', 0)),
        latency,
    )


def _log_ollama_call(session, article_id: int, input_tok: int, output_tok: int,
                     latency: int, success: bool, error_msg: str = None):
    """Log Ollama calls to GeminiCall table for unified usage tracking.

    Reuses the GeminiCall table since the call shape is identical and we
    do not need a separate ledger for the local model.
    """
    call = GeminiCall(
        stage='classify',
        model=OLLAMA_MODEL,
        input_tokens=input_tok,
        output_tokens=output_tok,
        latency_ms=latency,
        article_id=article_id,
        success=1 if success else 0,
        error_message=error_msg,
    )
    session.add(call)
    session.commit()


def _parse_section(raw: str) -> str:
    """Extract the first plausible section slug from model output.

    Local 4b models sometimes wrap the answer in backticks or add trailing
    punctuation. We strip those before validating.
    """
    s = raw.lower().strip()
    if not s:
        return ''
    first = s.split()[0]
    return first.strip('`.,\'"').strip()


def classify(session, batch_size: int = 10, gemini: GeminiClient = None) -> dict:
    """Classify a batch of SCRAPED articles. Returns counts."""
    from config import OLLAMA_URL  # imported here so config can be patched in tests

    if gemini is None:
        gemini = GeminiClient()

    week = scrape_mod.current_sunday_ct()
    arts = session.execute(
        select(Article).where(
            Article.state == 'SCRAPED',
            Article.week_of == week,
        ).limit(batch_size)
    ).scalars().all()

    classified = 0
    irrelevant = 0
    failed = 0
    ollama_calls = 0
    gemini_calls = 0

    for art in arts:
        prompt = render_classify_prompt(art.title, art.raw_content)
        section_raw = None
        used_backend = None

        # Try Ollama first if configured
        if OLLAMA_URL:
            try:
                resp, in_tok, out_tok, latency = _call_ollama(OLLAMA_URL, prompt)
                section_raw = _parse_section(resp)
                used_backend = 'ollama'
                ollama_calls += 1
                _log_ollama_call(session, art.id, in_tok, out_tok, latency, True)
            except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError) as e:
                # Ollama unreachable - log the failure and fall back to Gemini
                _log_ollama_call(session, art.id, 0, 0, 0, False, f'ollama unreachable: {str(e)[:120]}')
                section_raw = None  # trigger Gemini fallback below

        if section_raw is None:
            # Either OLLAMA_URL not set, or Ollama failed - use Gemini
            try:
                resp = gemini.call(model='gemini-2.5-flash-lite', prompt=prompt,
                                   stage='classify', article_id=art.id)
                section_raw = _parse_section(resp)
                used_backend = 'gemini'
                gemini_calls += 1
            except GeminiRateLimitExceeded:
                break  # bail batch, next tick retries
            except Exception as e:
                art.state = 'FAILED'
                art.error_message = str(e)[:255]
                failed += 1
                continue

        # Validate and apply section
        if section_raw not in VALID_SECTIONS_OR_IRRELEVANT:
            art.state = 'FAILED'
            art.error_message = f'classify ({used_backend}) returned unrecognized section: {section_raw[:80]}'
            failed += 1
            continue

        if section_raw == 'irrelevant':
            art.state = 'IRRELEVANT'
            irrelevant += 1
        else:
            art.state = 'CLASSIFIED'
            art.section = section_raw
            art.classified_at = datetime.now(timezone.utc).replace(tzinfo=None)
            classified += 1

    session.commit()
    return {
        'classified': classified,
        'irrelevant': irrelevant,
        'failed': failed,
        'ollama_calls': ollama_calls,
        'gemini_calls': gemini_calls,
    }
