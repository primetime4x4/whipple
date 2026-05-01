"""Mine resilience.org Whipple bulletin archive for source list.

Uses the resilience.org WordPress sitemap (https://www.resilience.org/sitemap.xml)
to enumerate ALL energy-bulletin-weekly posts, then filters to bulletins
published on or before WHIPPLE_PRE_DECLINE_CUTOFF.

Why the cutoff: Tom Whipple was diagnosed with cancer in late 2022 and the
quality/style of his bulletins declined after that. Per Dillon, only pre-cutoff
bulletins are representative of the editorial voice we're recreating.
"""
import re
from collections import Counter
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

SITEMAP_INDEX = 'https://www.resilience.org/sitemap.xml'
WHIPPLE_PRE_DECLINE_CUTOFF = '2022-09-30'  # last bulletin before cancer decline
HEADERS = {'User-Agent': 'Whipple-Bot/0.1 (personal-use)'}


def _fetch(url):
    r = requests.get(url, timeout=20, headers=HEADERS)
    r.raise_for_status()
    return BeautifulSoup(r.text, 'html5lib')


def list_bulletins(sample_size=30):
    """Enumerate Whipple bulletins via sitemap, filter by date, sample evenly.

    Returns a list of bulletin URLs sampled across the available date range
    (oldest to newest among pre-cutoff bulletins).
    """
    # Walk sitemap index -> sub-sitemaps -> energy-bulletin-weekly URLs
    r = requests.get(SITEMAP_INDEX, timeout=15, headers=HEADERS)
    r.raise_for_status()
    sub_sitemaps = re.findall(
        r'<loc>([^<]+post-sitemap[^<]*\.xml)</loc>', r.text
    )

    bulletins = []
    for s in sub_sitemaps:
        try:
            r = requests.get(s, timeout=15, headers=HEADERS)
            r.raise_for_status()
            for u in re.findall(r'<loc>([^<]+)</loc>', r.text):
                if 'energy-bulletin-weekly' not in u:
                    continue
                m = re.search(r'/stories/(\d{4}-\d{2}-\d{2})/', u)
                if m and m.group(1) <= WHIPPLE_PRE_DECLINE_CUTOFF:
                    bulletins.append((m.group(1), u))
        except Exception:
            continue

    bulletins = sorted(set(bulletins))
    if len(bulletins) <= sample_size:
        return [u for _, u in bulletins]
    # Even sampling across the FULL range, including both endpoints.
    # The naive `step = len // sample_size` loses the tail; this walks the
    # full index space.
    n = len(bulletins)
    indices = sorted({int(round(i * (n - 1) / (sample_size - 1)))
                      for i in range(sample_size)})
    return [bulletins[i][1] for i in indices]


def extract_sources_from_bulletin(html):
    """Return Counter of citation patterns found in one bulletin."""
    soup = BeautifulSoup(html, 'html5lib')
    counter = Counter()

    for a in soup.select('article a, .entry-content a'):
        href = a.get('href', '')
        if href.startswith('http'):
            try:
                domain = urlparse(href).netloc.lower().replace('www.', '')
                if domain and 'resilience.org' not in domain:
                    counter[domain] += 1
            except Exception:
                pass

    text = soup.get_text()
    for m in re.finditer(r'\(([A-Z][\w\s&.\']{1,40})\)', text):
        cite = m.group(1).strip()
        if 5 <= len(cite) <= 30 and not any(c.isdigit() for c in cite):
            counter['cite:' + cite] += 1

    return counter


def mine_archive(sample_size=30):
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
