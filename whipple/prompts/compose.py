"""Compose prompt - single big call to assemble final bulletin."""
from .voice_guide import VOICE_GUIDE


COMPOSE_PROMPT = """{voice_guide}

You are assembling the final HTML bulletin for {week_of}. Below are pre-written
summaries grouped by section. Your job:

1. Order stories within each section by importance (most consequential first).
2. Add minimal connective transitions BETWEEN stories where natural - never invent facts.
3. Pick TWO "Quotes of the Week" from the most striking direct quotes embedded in the article corpus
   (search the raw_content fields below). Format as standalone blockquotes.
4. Pick ONE "Graphic of the Week" candidate (return the URL of an embedded chart/image from
   the article corpus, plus a one-line caption derived from the article that featured it).
   If no good candidate, return null for both.

Pre-written summaries by section:
{summaries_block}

Article corpus for quote/graphic extraction:
{corpus_block}

Return JSON with this exact structure:
{{
  "quote_a": "...",
  "quote_b": "...",
  "graphic_url": "https://..." or null,
  "graphic_caption": "..." or null,
  "html": "...full bulletin HTML..."
}}

The html field MUST contain ONLY the narrative sections in this order:
1. Energy prices and production
2. Geopolitical instability
3. Climate change
4. The global economy
5. Renewables and new technologies
6. The Briefs

Do NOT include a Quotes of the Week section or a Graphic of the Week section in the html
field - those are rendered separately by the wrapper template from quote_a/quote_b/graphic_url.
Including them in html will cause them to appear twice in the final bulletin.

Each narrative section is `<h2>` followed by paragraphs (one `<p>` per story).
The Briefs section is `<h2>The Briefs</h2>` followed by `<ul><li>` items.

Output ONLY the JSON. No markdown code fences, no surrounding text."""


def render_compose_prompt(week_of, summaries_by_section, corpus):
    sb = []
    for section, items in summaries_by_section.items():
        sb.append(f"\n## {section}\n")
        for item in items:
            sb.append(f"- {item}\n")
    summaries_block = ''.join(sb)

    cb = []
    for art in corpus:
        cb.append(f"\nURL: {art['url']}\nTitle: {art['title']}\nContent: {art['content'][:1500]}\n")
    corpus_block = ''.join(cb)

    return COMPOSE_PROMPT.format(
        voice_guide=VOICE_GUIDE,
        week_of=week_of,
        summaries_block=summaries_block,
        corpus_block=corpus_block,
    )
