"""Flask factory."""
from flask import Flask
from whipple.db import init_db
from whipple.routes import health, sources, archives, manual, rss, settings, articles
import config


def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config['SECRET_KEY'] = config.SECRET_KEY
    init_db()
    app.register_blueprint(health.bp)
    app.register_blueprint(sources.bp)
    app.register_blueprint(archives.bp)
    app.register_blueprint(manual.bp)
    app.register_blueprint(rss.bp)
    app.register_blueprint(settings.bp)
    app.register_blueprint(articles.bp)
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=config.PORT, debug=False)
