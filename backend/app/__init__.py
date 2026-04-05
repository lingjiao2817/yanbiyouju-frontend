from pathlib import Path

from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import RequestEntityTooLarge

from .database import close_db, init_db
from .document_parser import MAX_UPLOAD_SIZE
from .routes import api


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["DATABASE_PATH"] = Path(app.root_path).parent / "data" / "yanbiyouju.db"
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE
    app.json.ensure_ascii = False
    app.config['JSON_AS_ASCII'] = False

    CORS(app, resources={r"/api/*": {"origins": "*"}})

    app.register_blueprint(api, url_prefix="/api")
    app.teardown_appcontext(close_db)

    with app.app_context():
        init_db()  #读取SQL脚本

    @app.errorhandler(RequestEntityTooLarge)
    def handle_file_too_large(_error):
        response = jsonify({"message": "上传文件不能超过 16MB。"})
        response.headers["Content-Type"] = "application/json; charset=utf-8"
        return response, 413

    return app
