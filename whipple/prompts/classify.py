"""Classifier prompt for Gemini Flash."""
CLASSIFY_PROMPT = """You classify energy/climate/geopolitics news articles into one of the
sections of an Energy Bulletin Weekly digest.

Sections (return EXACTLY one of these slugs, lowercase):
- energy_prices       (oil, gas, coal, electricity, fuel, supply/demand, market reports)
- geopolitical        (sanctions, conflicts, OPEC, trade, energy diplomacy)
- climate             (climate science, IPCC, weather extremes, attribution, climate policy)
- global_economy      (macroeconomics, inflation, central banks - only when energy-related)
- renewables          (solar, wind, batteries, storage, EVs, hydrogen, grid tech)
- briefs              (any of the above but the article is short/single-fact, fit for a one-liner)
- irrelevant          (NOT energy/climate/geopolitics; e.g., entertainment, sports, unrelated tech)

Article title: {title}
Article first 500 chars: {content_preview}

Return ONLY the section slug. No explanation, no quotes, no extra text."""


def render_classify_prompt(title: str, content_preview: str) -> str:
    return CLASSIFY_PROMPT.format(title=title or '(no title)',
                                   content_preview=(content_preview or '')[:500])
