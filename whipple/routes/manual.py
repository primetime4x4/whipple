"""/manual - phrase-gated triggers for ticks, finalize, resend."""
import subprocess
import sys
from flask import Blueprint, render_template, request, abort, redirect, url_for
from whipple.db import get_session
from whipple.models import Bulletin, Article
from whipple.pipeline.scrape import current_sunday_ct
from config import MANUAL_TRIGGER_PHRASE

bp = Blueprint('manual', __name__)


def _check_phrase():
    if request.form.get('phrase') != MANUAL_TRIGGER_PHRASE:
        abort(403)


@bp.route('/manual')
def manual():
    return render_template('manual.html')


@bp.route('/manual/tick', methods=['POST'])
def trigger_tick():
    _check_phrase()
    subprocess.Popen([sys.executable, '-m', 'whipple.tick'])
    return redirect(url_for('health.health'))


@bp.route('/manual/finalize', methods=['POST'])
def trigger_finalize():
    _check_phrase()
    subprocess.Popen([sys.executable, '-m', 'whipple.finalize'])
    return redirect(url_for('health.health'))


@bp.route('/manual/skip-week', methods=['POST'])
def skip_week():
    _check_phrase()
    s = get_session()
    week = current_sunday_ct()
    s.query(Article).filter(
        Article.week_of == week,
        Article.state.in_(['SCRAPED', 'CLASSIFIED', 'SELECTED', 'SUMMARIZED'])
    ).update({'state': 'SKIPPED'}, synchronize_session=False)
    s.commit()
    return redirect(url_for('manual.manual'))


@bp.route('/manual/resend', methods=['POST'])
def resend_last():
    _check_phrase()
    from whipple.services.gmail import send_bulletin
    from datetime import datetime
    s = get_session()
    b = s.query(Bulletin).filter_by(status='SENT').order_by(Bulletin.sent_at.desc()).first()
    if b and b.html_content:
        fmt = "%B %-d, %Y"
        subject = f"Energy Bulletin Weekly - {datetime.fromisoformat(b.week_of).strftime(fmt)}"
        send_bulletin(subject=subject, html=b.html_content)
    return redirect(url_for('manual.manual'))
