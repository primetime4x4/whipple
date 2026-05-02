"""/archives - past bulletin viewer."""
from flask import Blueprint, render_template, abort, Response
from whipple.db import get_session
from whipple.models import Bulletin

bp = Blueprint('archives', __name__)


@bp.route('/archives')
@bp.route('/')
def list_bulletins():
    s = get_session()
    bulletins = s.query(Bulletin).order_by(Bulletin.week_of.desc()).all()
    return render_template('archives.html', bulletins=bulletins)


@bp.route('/archives/<week_of>')
def view_bulletin(week_of):
    s = get_session()
    b = s.query(Bulletin).filter_by(week_of=week_of).first()
    if not b:
        abort(404)
    return render_template('archives_detail.html', bulletin=b)


@bp.route('/archives/<week_of>/raw')
def view_bulletin_raw(week_of):
    """Return the bulletin html_content as a standalone HTML doc.

    Used by archives_detail iframe so the bulletin's email-style CSS is
    isolated from the Whipple app theme. Without this isolation, the
    nested HTML doc inherits the outer theme's H1 color, causing the
    bulletin title to render cream-on-cream and become unreadable.
    """
    s = get_session()
    b = s.query(Bulletin).filter_by(week_of=week_of).first()
    if not b or not b.html_content:
        abort(404)
    return Response(b.html_content, mimetype='text/html')
