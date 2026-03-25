from pathlib import Path

from flask import Flask
from flask_cors import CORS

from .database import close_db, init_db
from .routes import api


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["DATABASE_PATH"] = Path(app.root_path).parent / "data" / "yanbiyouju.db"
    app.json.ensure_ascii = False

    CORS(app, resources={r"/api/*": {"origins": "*"}})

    app.register_blueprint(api, url_prefix="/api")
    app.teardown_appcontext(close_db)

    with app.app_context():
        init_db()

    return app
