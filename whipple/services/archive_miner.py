"""Mine resilience.org Whipple bulletin archive for source list."""
import re
from collections import Counter
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

WHIPPLE_AUTHOR_URL = 'https://www.resilience.org/contributors/tom-whipple/'
HEADERS = {'User-Agent': 'Whipple-Bot/0.1 (personal-use)'}


def _fetch(url: str) -> BeautifulSoup:
    r = requests.get(url, timeout=20, headers=HEADERS)
    r.raise_for_status()
    return BeautifulSoup(r.text, 'html5lib')


def list_bulletins(sample_size: int = 30) -> list:
    """Get URLs of N sampled bulletins from Whipple's resilience.org page."""
    soup = _fetch(WHIPPLE_AUTHOR_URL)
    bulletins = []
    for a in soup.select('a'):
        href = a.get('href', '')
        if 'energy-bulletin-weekly' in href and href.startswith('http'):
            bulletins.append(href)
    # Dedupe + sample
    bulletins = list(dict.fromkeys(bulletins))
    if len(bulletins) <= sample_size:
        return bulletins
    step = len(bulletins) // sample_size
    return [bulletins[i*step] for i in range(sample_size)]


def extract_sources_from_bulletin(html: str) -> Counter:
    """Return Counter of citation patterns found in one bulletin."""
    soup = BeautifulSoup(html, 'html5lib')
    counter = Counter()

    # External link domains
    for a in soup.select('article a, .entry-content a'):
        href = a.get('href', '')
        if href.startswith('http'):
            try:
                domain = urlparse(href).netloc.lower().replace('www.', '')
                if domain and 'resilience.org' not in domain:
                    counter[domain] += 1
            except Exception:
                pass

    # Parenthetical citations like (Reuters), (EIA), (Bloomberg)
    text = soup.get_text()
    for m in re.finditer(r'\(([A-Z][\w\s&.\']{1,40})\)', text):
        cite = m.group(1).strip()
        if 5 <= len(cite) <= 30 and not any(c.isdigit() for c in cite):
            counter[f'cite:{cite}'] += 1

    return counter


def mine_archive(sample_size: int = 30) -> Counter:
    """Mine ~N bulletins, return aggregated citation counter."""
    urls = list_bulletins(sample_size=sample_size)
    total = Counter()
    for url in urls:
        try:
            soup = _fetch(url)
            total.update(extract_sources_from_bulletin(str(soup)))
        except Exception:
            continue
    return total
