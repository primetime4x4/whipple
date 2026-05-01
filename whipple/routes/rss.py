"""/rss - past bulletins as RSS feed."""
from datetime import datetime
from flask import Blueprint, Response
from whipple.db import get_session
from whipple.models import Bulletin

bp = Blueprint('rss', __name__)


@bp.route('/rss')
def feed():
    s = get_session()
    bulletins = s.query(Bulletin).filter_by(status='SENT').order_by(
        Bulletin.sent_at.desc()).limit(20).all()
    items = []
    for b in bulletins:
        items.append(f"""<item>
<title>Energy Bulletin Weekly - {b.week_of}</title>
<link>http://192.168.86.204:28813/archives/{b.week_of}</link>
<pubDate>{b.sent_at.strftime('%a, %d %b %Y %H:%M:%S +0000') if b.sent_at else ''}</pubDate>
<description><![CDATA[{b.html_content[:1000]}...]]></description>
<guid>{b.week_of}</guid>
</item>""")
    body = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<title>Whipple Report</title>
<link>http://192.168.86.204:28813/</link>
<description>Personal weekly energy bulletin recreation</description>
{''.join(items)}
</channel></rss>"""
    return Response(body, mimetype='application/rss+xml')
