from flask import Blueprint, jsonify, request

from .checker import analyze_text
from .database import add_comment, get_check, list_checks, list_comments, save_check
from .rules_loader import load_rules


api = Blueprint("api", __name__)


@api.get("/health")
def health() -> tuple[dict, int]:
    return {"status": "ok", "service": "言必有据"}, 200


@api.get("/rules/meta")
def fetch_rules_meta() -> tuple[dict, int]:
    rules = load_rules()
    return {"rules_summary": rules["__meta"]}, 200


@api.get("/checks")
def fetch_checks() -> tuple[dict, int]:
    return {"items": list_checks()}, 200


@api.get("/checks/<int:check_id>")
def fetch_check(check_id: int):
    record = get_check(check_id)
    if record is None:
        return jsonify({"message": "记录不存在"}), 404
    return jsonify(record), 200


@api.post("/checks")
def create_check():
    payload = request.get_json(silent=True) or {}
    title = (payload.get("title") or "未命名查证").strip()[:80]
    text = (payload.get("text") or "").strip()

    if not text:
        return jsonify({"message": "请先输入需要核查的文本"}), 400

    result = analyze_text(text)
    record = save_check(title, text, result)
    return jsonify(record), 201


@api.get("/checks/<int:check_id>/comments")
def fetch_comments(check_id: int):
    if get_check(check_id) is None:
        return jsonify({"message": "记录不存在"}), 404
    return jsonify({"items": list_comments(check_id)}), 200


@api.post("/checks/<int:check_id>/comments")
def create_comment(check_id: int):
    if get_check(check_id) is None:
        return jsonify({"message": "记录不存在"}), 404

    payload = request.get_json(silent=True) or {}
    author = (payload.get("author") or "匿名评阅人").strip()[:40]
    role = (payload.get("role") or "教师点评").strip()[:40]
    content = (payload.get("content") or "").strip()

    if not content:
        return jsonify({"message": "点评内容不能为空"}), 400

    comment = add_comment(check_id, author, role, content[:1000])
    return jsonify(comment), 201
