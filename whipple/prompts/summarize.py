"""Summarize prompt for Gemini."""
from .voice_guide import VOICE_GUIDE

SUMMARIZE_NARRATIVE_PROMPT = """{voice_guide}

You are summarizing one news article for the "{section_display}" section of the
Energy Bulletin Weekly. Target length: 50-200 words (one paragraph, 3-8 sentences).

Title: {title}
Source: {source_name}
URL: {url}
Article content (truncated):
---
{content}
---

Write the summary paragraph. End with " ({source_name})" if not already attributed inline.
Do not start with "This article" or "The article". Lead with the most consequential fact.
Output ONLY the summary paragraph. No headers, no markdown."""


SUMMARIZE_BRIEF_PROMPT = """{voice_guide}

You are summarizing one news article for the "The Briefs" section of the Energy Bulletin
Weekly. Target length: 15-40 words (single sentence, optionally two).

Title: {title}
Source: {source_name}
URL: {url}
Article content (truncated):
---
{content}
---

Write a single brief in this exact format:
**[Subject or Location].** [One-sentence summary]. ({source_name})

Output ONLY the brief. No headers, no markdown beyond the bold."""


def render_summarize_prompt(title, source_name, url, content, section, section_display):
    template = SUMMARIZE_BRIEF_PROMPT if section == 'briefs' else SUMMARIZE_NARRATIVE_PROMPT
    return template.format(
        voice_guide=VOICE_GUIDE,
        title=title or '(no title)',
        source_name=source_name,
        url=url,
        content=(content or '')[:3000],
        section=section,
        section_display=section_display,
    )
