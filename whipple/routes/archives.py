"""/archives - past bulletin viewer."""
from flask import Blueprint, render_template, abort
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
