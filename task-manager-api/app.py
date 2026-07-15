"""Composition root (F-007).

Importing this module no longer touches the database. Schema creation is an
explicit call (`init_db`) or the `flask init-db` CLI command, not an import-time
side effect.
"""
import logging

from flask import Flask
from flask_cors import CORS

from config import cors_origins, load_config
from database import db
from errors import register_error_handlers


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(load_config(config))

    logging.basicConfig(
        level=logging.DEBUG if app.config['DEBUG'] else logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    )

    origins = cors_origins(app.config)
    if origins:
        CORS(app, origins=origins)

    db.init_app(app)

    register_blueprints(app)
    register_error_handlers(app)
    register_cli(app)

    @app.route('/health')
    def health():
        from timeutil import isoformat, utcnow

        return {'status': 'ok', 'timestamp': isoformat(utcnow())}

    @app.route('/')
    def index():
        return {'message': 'Task Manager API', 'version': '2.0'}

    return app


def register_blueprints(app):
    from routes.category_routes import category_bp
    from routes.report_routes import report_bp
    from routes.task_routes import task_bp
    from routes.user_routes import user_bp

    app.register_blueprint(task_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(category_bp)
    app.register_blueprint(report_bp)


def register_cli(app):
    @app.cli.command('init-db')
    def init_db_command():
        """Create the database schema."""
        init_db(app)
        print('Schema criado.')


def init_db(app):
    # Importing the models registers them on the metadata before create_all.
    import models.category  # noqa: F401
    import models.task  # noqa: F401
    import models.user  # noqa: F401

    with app.app_context():
        db.create_all()


app = create_app()


if __name__ == '__main__':
    init_db(app)
    app.run(
        debug=app.config['DEBUG'],
        host=app.config['HOST'],
        port=app.config['PORT'],
    )
