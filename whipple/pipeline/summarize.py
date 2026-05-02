"""summarize() stage - writes the per-article paragraph.

Default backend: local Ollama (gemma3:4b) when OLLAMA_URL is set. Falls back to
Gemini on network failure. Whipple's free-tier Gemini quota cannot cover the
40-50 summarize calls a typical bulletin needs.
"""
from datetime import datetime
from sqlalchemy import select as sa_select
from whipple.models import Article, Source, GeminiCall
from whipple.services.gemini import GeminiClient, GeminiRateLimitExceeded
from whipple.services.ollama import call_ollama, OllamaUnavailable
from whipple.prompts.summarize import render_summarize_prompt
from whipple.pipeline import scrape as scrape_mod
from config import SECTION_DISPLAY


def _linkify_source(text: str, source_name: str, article_url: str) -> str:
    """Wrap the trailing source attribution in an anchor tag."""
    if not article_url or not source_name:
        return text
    linked = f'<a href="{article_url}" target="_blank" rel="noopener">{source_name}</a>'
    tag = f'({source_name})'
    if tag in text:
        head, _, tail = text.rpartition(tag)
        return f'{head}({linked}){tail}'
    return f'{text} ({linked})'


def _log_ollama(session, stage, model, in_tok, out_tok, latency, article_id, success, err=None):
    session.add(GeminiCall(
        stage=stage, model=model,
        input_tokens=in_tok, output_tokens=out_tok, latency_ms=latency,
        article_id=article_id, success=1 if success else 0, error_message=err,
    ))
    session.commit()


def summarize(session, batch_size: int = 5, gemini: GeminiClient = None) -> dict:
    if gemini is None:
        gemini = GeminiClient()

    week = scrape_mod.current_sunday_ct()
    rows = session.execute(
        sa_select(Article, Source).join(Source).where(
            Article.state == 'SELECTED',
            Article.week_of == week,
        ).limit(batch_size)
    ).all()

    summarized = 0
    failed = 0
    ollama_calls = 0
    gemini_calls = 0

    for art, src in rows:
        try:
            section_display = SECTION_DISPLAY.get(art.section, art.section)
            prompt = render_summarize_prompt(
                title=art.title, source_name=src.name, url=art.url,
                content=art.raw_content, section=art.section,
                section_display=section_display,
            )
            text = None

            # Try Ollama first
            try:
                text, in_tok, out_tok, latency = call_ollama(prompt)
                ollama_calls += 1
                _log_ollama(session, 'summarize', 'gemma3:4b', in_tok, out_tok, latency, art.id, True)
            except OllamaUnavailable as e:
                _log_ollama(session, 'summarize', 'gemma3:4b', 0, 0, 0, art.id, False, str(e)[:120])

            # Fall back to Gemini if Ollama unreachable
            if text is None:
                model = 'gemini-2.5-flash-lite' if art.section == 'briefs' else 'gemini-2.5-flash'
                text = gemini.call(model=model, prompt=prompt, stage='summarize',
                                   article_id=art.id)
                gemini_calls += 1

            text = text.strip()
            text = _linkify_source(text, src.name, art.url)
            art.summary_text = text
            art.state = 'SUMMARIZED'
            art.summarized_at = datetime.utcnow()
            summarized += 1
        except GeminiRateLimitExceeded:
            break
        except Exception as e:
            art.state = 'FAILED'
            art.error_message = str(e)[:255]
            failed += 1

    session.commit()
    return {
        'summarized': summarized,
        'failed': failed,
        'ollama_calls': ollama_calls,
        'gemini_calls': gemini_calls,
    }
