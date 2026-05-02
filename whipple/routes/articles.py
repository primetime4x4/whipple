"""/articles - browse scraped articles with filters."""
from flask import Blueprint, render_template, request
from sqlalchemy import desc, or_

from whipple.db import get_session
from whipple.models import Article, Source, ARTICLE_STATES

bp = Blueprint('articles', __name__)


@bp.route('/articles')
def list_articles():
    s = get_session()

    state = (request.args.get('state') or '').strip().upper()
    week = (request.args.get('week') or '').strip()
    source_id = request.args.get('source_id', type=int)
    search = (request.args.get('q') or '').strip()
    limit = request.args.get('limit', default=200, type=int)
    limit = max(10, min(limit, 1000))

    q = s.query(Article).join(Source, Article.source_id == Source.id)
    if state and state in ARTICLE_STATES:
        q = q.filter(Article.state == state)
    if week:
        q = q.filter(Article.week_of == week)
    if source_id:
        q = q.filter(Article.source_id == source_id)
    if search:
        like = f'%{search}%'
        q = q.filter(or_(Article.title.ilike(like), Article.summary_text.ilike(like)))

    articles = q.order_by(desc(Article.scraped_at)).limit(limit).all()

    weeks = [r[0] for r in s.query(Article.week_of).distinct().order_by(desc(Article.week_of)).limit(20).all()]
    sources = s.query(Source).order_by(Source.name).all()

    total = q.order_by(None).count()

    return render_template(
        'articles.html',
        articles=articles,
        weeks=weeks,
        sources=sources,
        states=ARTICLE_STATES,
        filter_state=state,
        filter_week=week,
        filter_source_id=source_id,
        filter_search=search,
        showing=len(articles),
        total=total,
        limit=limit,
    )
