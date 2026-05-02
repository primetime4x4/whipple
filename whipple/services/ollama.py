"""Local Ollama backend used by classify, summarize, and compose stages."""
import json
import time
import urllib.error
import urllib.request

DEFAULT_MODEL = 'gemma3:4b'


class OllamaUnavailable(Exception):
    """Ollama is not reachable or returned an error."""


def call_ollama(prompt: str, model: str = DEFAULT_MODEL, timeout: int = 180,
                json_format: bool = False, num_ctx: int = 8192) -> tuple[str, int, int, int]:
    """Send a prompt to Ollama. Returns (text, input_tokens, output_tokens, latency_ms).

    Raises OllamaUnavailable if OLLAMA_URL is not set or the call fails.

    num_ctx caps the model's context window. classify/summarize prompts fit in
    8K, but compose feeds 40+ summaries plus per-article corpus excerpts and
    needs more. gemma3:4b supports up to 128K but each doubling of the window
    increases latency proportionally, so callers should bump only when they
    actually need it.
    """
    from config import OLLAMA_URL
    if not OLLAMA_URL:
        raise OllamaUnavailable('OLLAMA_URL not configured')

    body = {
        'model': model,
        'prompt': prompt,
        'stream': False,
        'options': {'temperature': 0.2, 'num_ctx': num_ctx},
    }
    if json_format:
        body['format'] = 'json'

    payload = json.dumps(body).encode()
    req = urllib.request.Request(
        f'{OLLAMA_URL.rstrip("/")}/api/generate',
        data=payload,
        headers={'Content-Type': 'application/json'},
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read())
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError) as e:
        raise OllamaUnavailable(f'{type(e).__name__}: {str(e)[:160]}')

    return (
        data.get('response', '').strip(),
        int(data.get('prompt_eval_count', 0)),
        int(data.get('eval_count', 0)),
        int((time.time() - t0) * 1000),
    )
