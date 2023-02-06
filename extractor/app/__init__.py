from flask import Flask
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from extractor import app_config
from extractor.app.auth import _build_auth_code_flow

db = SQLAlchemy()

# This section is needed for url_for("foo", _external=True) to automatically
# generate http scheme when this sample is running on localhost,
# and to generate https scheme when it is deployed behind reversed proxy.
# See also https://flask.palletsprojects.com/en/1.0.x/deploying/wsgi-standalone/#proxy-setups
from werkzeug.middleware.proxy_fix import ProxyFix


def create_app():
    app = Flask(__name__, instance_relative_config=True, template_folder='templates', static_folder='static')
    app.config.from_object(app_config)
    db.init_app(app)

    session = Session()
    session.init_app(app)

    with app.app_context():
        db.create_all()

    from .routes import bp
    app.register_blueprint(bp)

    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    app.jinja_env.globals.update(_build_auth_code_flow=_build_auth_code_flow)  # Used in template

    return app
