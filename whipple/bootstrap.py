"""One-time bootstrap: mine Whipple archive + seed modern sources.

    docker compose exec whipple python -m whipple.bootstrap
"""
import json
import sys
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from whipple.db import get_session
from whipple.models import Source
from whipple.services.archive_miner import mine_archive

HEADERS = {'User-Agent': 'Whipple-Bot/0.1 (personal-use)'}


def _try_rss_discovery(domain: str):
    """Look for <link rel='alternate' type='application/rss+xml'> on homepage."""
    try:
        r = requests.get(f'https://{domain}', timeout=10, headers=HEADERS)
        soup = BeautifulSoup(r.text, 'html5lib')
        link = soup.find('link', {'rel': 'alternate', 'type': 'application/rss+xml'})
        if link and link.get('href'):
            href = link.get('href')
            if href.startswith('/'):
                href = f'https://{domain}{href}'
            return href
    except Exception:
        pass
    return None


def main():
    session = get_session()

    # Step 1: modern seed
    modern_path = '/app/seeds/modern_sources.json'
    with open(modern_path) as f:
        modern = json.load(f)

    added_modern = 0
    for entry in modern:
        exists = session.query(Source).filter_by(url=entry['url']).first()
        if not exists:
            session.add(Source(
                name=entry['name'], url=entry['url'],
                source_type=entry['source_type'],
                section_hint=entry.get('section_hint'),
                weight=entry.get('weight', 1.0),
                active=0, origin='modern',
            ))
            added_modern += 1
    session.commit()
    print(f'Added {added_modern} modern sources.')

    # Step 2: mine Whipple archive
    print('Mining Whipple archive (this takes ~5 minutes)...')
    counter = mine_archive(sample_size=30)
    top_domains = [d for d, n in counter.most_common(60)
                   if not d.startswith('cite:') and n >= 3]

    added_whipple = 0
    for domain in top_domains:
        rss_url = _try_rss_discovery(domain)
        url = rss_url or f'https://{domain}'
        source_type = 'rss' if rss_url else 'scraper'
        exists = session.query(Source).filter_by(url=url).first()
        if not exists:
            session.add(Source(
                name=domain, url=url, source_type=source_type,
                weight=1.0, active=0, origin='whipple-archive',
                notes=f'Cited {counter[domain]} times in sampled Whipple bulletins.',
            ))
            added_whipple += 1

    session.commit()
    print(f'Added {added_whipple} Whipple-archive sources.')
    print(f'Total sources in DB: {session.query(Source).count()}')
    print('All sources are inactive by default. Enable via /sources UI.')


if __name__ == '__main__':
    sys.exit(main() or 0)
