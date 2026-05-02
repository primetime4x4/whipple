"""/settings - theme picker (client-side, localStorage)."""
from flask import Blueprint, render_template

bp = Blueprint('settings', __name__)


@bp.route('/settings')
def settings():
    return render_template('settings.html')
