"""Render bulletin HTML from compose() output."""
from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader('templates'), autoescape=True)


def render_bulletin(week_of: str, assembled_html: str, quote_a: str,
                    quote_b: str, graphic_url: str, graphic_caption: str,
                    article_count: int, total_word_count: int) -> str:
    tpl = env.get_template('bulletin.html')
    formatted = datetime.fromisoformat(week_of).strftime('%B %-d, %Y')
    return tpl.render(
        week_of=week_of, formatted_date=formatted, assembled_html=assembled_html,
        quote_a=quote_a, quote_b=quote_b, graphic_url=graphic_url,
        graphic_caption=graphic_caption, article_count=article_count,
        total_word_count=total_word_count,
        generated_at=datetime.utcnow().isoformat(timespec='seconds'),
    )


def save_archive(week_of: str, html: str, base_dir: str = '/app/data/bulletins') -> Path:
    out = Path(base_dir) / f'{week_of}.html'
    out.write_text(html, encoding='utf-8')
    return out
