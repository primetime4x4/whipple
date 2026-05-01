"""/sources - source list management."""
from flask import Blueprint, render_template, request, redirect, url_for
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


@bp.route('/sources/bulk', methods=['POST'])
def bulk_action():
    action = request.form.get('action', '')
    s = get_session()
    n = 0
    if action == 'enable_all':
        n = s.query(Source).update({'active': 1, 'consecutive_failures': 0}, synchronize_session=False)
    elif action == 'disable_all':
        n = s.query(Source).update({'active': 0}, synchronize_session=False)
    elif action == 'enable_modern':
        n = s.query(Source).filter(Source.origin == 'modern').update(
            {'active': 1, 'consecutive_failures': 0}, synchronize_session=False)
    elif action == 'enable_whipple_rss':
        defunct = ('energybulletin.org', 'daily.energybulletin.org')
        n = s.query(Source).filter(
            Source.origin == 'whipple-archive',
            Source.source_type == 'rss',
            ~Source.name.in_(defunct),
        ).update({'active': 1, 'consecutive_failures': 0}, synchronize_session=False)
    elif action == 'disable_whipple':
        n = s.query(Source).filter(Source.origin == 'whipple-archive').update(
            {'active': 0}, synchronize_session=False)
    elif action == 'disable_noise':
        noise = ('bsky.app', 'facebook.com', 'x.com', 'linkedin.com')
        n = s.query(Source).filter(Source.name.in_(noise)).update(
            {'active': 0}, synchronize_session=False)
    elif action == 'disable_defunct':
        defunct = ('energybulletin.org', 'daily.energybulletin.org')
        n = s.query(Source).filter(Source.name.in_(defunct)).update(
            {'active': 0}, synchronize_session=False)
    s.commit()
    return redirect(url_for('sources.list_sources'))
