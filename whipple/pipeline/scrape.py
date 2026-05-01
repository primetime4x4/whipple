"""scrape() stage - pull RSS + scrape sources, dedupe by URL."""
from datetime import datetime, timedelta
from typing import Optional
import feedparser
import requests
from bs4 import BeautifulSoup
from sqlalchemy import select
from whipple.models import Article, Source


def current_sunday_ct() -> str:
    """Returns YYYY-MM-DD of upcoming Sunday in America/Chicago.
    Articles scraped Saturday 11pm CT belong to upcoming Sunday's bulletin."""
    import zoneinfo
    now_ct = datetime.now(zoneinfo.ZoneInfo('America/Chicago'))
    days_until_sunday = (6 - now_ct.weekday()) % 7
    if days_until_sunday == 0 and now_ct.hour >= 21:
        days_until_sunday = 7
    sunday = now_ct.date() + timedelta(days=days_until_sunday)
    return sunday.isoformat()


def _scrape_rss(source: Source) -> list[dict]:
    feed = feedparser.parse(source.url)
    items = []
    for entry in feed.entries[:50]:
        items.append({
            'url': entry.get('link'),
            'title': entry.get('title'),
            'content': entry.get('summary', '') + '\n' + entry.get('description', ''),
            'published_at': _parse_published(entry),
        })
    return [i for i in items if i['url']]


def _parse_published(entry) -> Optional[datetime]:
    if hasattr(entry, 'published_parsed') and entry.published_parsed:
        return datetime(*entry.published_parsed[:6])
    return None


def _scrape_html(source: Source) -> list[dict]:
    """Per-source HTML scraper using selector_config JSON."""
    import json as jsonlib
    if not source.selector_config:
        return []
    config = jsonlib.loads(source.selector_config)
    r = requests.get(source.url, timeout=15, headers={'User-Agent': 'Whipple-Bot/0.1'})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'html5lib')
    items = []
    for el in soup.select(config['item_selector']):
        link = el.select_one(config['link_selector'])
        title = el.select_one(config['title_selector'])
        if link and title:
            items.append({
                'url': link.get('href'),
                'title': title.get_text(strip=True),
                'content': '',
                'published_at': None,
            })
    return items


def scrape(session) -> dict:
    """Run scrape over all active sources. Returns counts."""
    active = session.execute(
        select(Source).where(Source.active == 1)
    ).scalars().all()

    week_of = current_sunday_ct()
    inserted = 0
    failed_sources = 0

    for source in active:
        try:
            if source.source_type == 'rss':
                items = _scrape_rss(source)
            elif source.source_type == 'scraper':
                items = _scrape_html(source)
            else:
                continue

            for item in items:
                exists = session.execute(
                    select(Article).where(Article.url == item['url'])
                ).scalar_one_or_none()
                if not exists:
                    session.add(Article(
                        source_id=source.id, url=item['url'], title=item['title'],
                        published_at=item['published_at'], week_of=week_of,
                        raw_content=item['content'], state='SCRAPED',
                    ))
                    inserted += 1

            source.last_checked_at = datetime.utcnow()
            source.last_success_at = datetime.utcnow()
            source.consecutive_failures = 0
        except Exception as e:
            source.last_checked_at = datetime.utcnow()
            source.consecutive_failures += 1
            if source.consecutive_failures >= 3:
                source.active = 0
            failed_sources += 1

    session.commit()
    return {'inserted': inserted, 'failed_sources': failed_sources}
