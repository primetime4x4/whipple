"""/sources - source list management."""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from whipple.db import get_session
from whipple.models import Source

bp = Blueprint('sources', __name__)


@bp.route('/sources')
def list_sources():
    s = get_session()
    sources = s.query(Source).order_by(Source.active.desc(), Source.name).all()
    return render_template('sources.html', sources=sources)


@bp.route('/sources/<int:source_id>/toggle', methods=['POST'])
def toggle(source_id):
    s = get_session()
    src = s.query(Source).get(source_id)
    if src:
        src.active = 0 if src.active else 1
        if src.active:
            src.consecutive_failures = 0  # reset on re-enable
        s.commit()
    return redirect(url_for('sources.list_sources'))


@bp.route('/sources/new', methods=['GET', 'POST'])
def new_source():
    if request.method == 'POST':
        s = get_session()
        s.add(Source(
            name=request.form['name'].strip(),
            url=request.form['url'].strip(),
            source_type=request.form.get('source_type', 'rss'),
            section_hint=request.form.get('section_hint') or None,
            weight=float(request.form.get('weight', 1.0)),
            origin='manual', active=0,
        ))
        s.commit()
        return redirect(url_for('sources.list_sources'))
    return render_template('sources.html', new_form=True)
