"""/health route - pipeline status dashboard."""
from datetime import datetime, timedelta
from flask import Blueprint, render_template
from sqlalchemy import func, select
from whipple.db import get_session
from whipple.models import Article, Run, GeminiCall, Source
from config import GEMINI_RPM_LIMIT, GEMINI_RPD_LIMIT

bp = Blueprint('health', __name__)


@bp.route('/health')
def health():
    s = get_session()
    now = datetime.utcnow()
    last_24h = now - timedelta(days=1)
    last_min = now - timedelta(minutes=1)

    # Article counts by state for current week
    counts = dict(s.execute(
        select(Article.state, func.count())
        .group_by(Article.state)
    ).all())

    # Gemini calls last 24h
    gemini_24h = s.execute(
        select(func.count()).where(GeminiCall.called_at > last_24h)
    ).scalar()
    gemini_1m = s.execute(
        select(func.count()).where(GeminiCall.called_at > last_min)
    ).scalar()

    # Last 5 runs
    runs = s.execute(
        select(Run).order_by(Run.started_at.desc()).limit(5)
    ).scalars().all()

    # Failing sources
    failing = s.execute(
        select(Source).where(Source.consecutive_failures > 0)
    ).scalars().all()

    return render_template('health.html',
        counts=counts,
        gemini_24h=gemini_24h,
        gemini_1m=gemini_1m,
        rpm_limit=GEMINI_RPM_LIMIT,
        rpd_limit=GEMINI_RPD_LIMIT,
        runs=runs,
        failing=failing,
    )


@bp.route('/health.json')
def health_json():
    """For Uptime Kuma probe."""
    return {'status': 'ok', 'service': 'whipple', 'version': '0.1.0'}
