from flask import Blueprint, jsonify, request

from .checker import analyze_text
from .database import add_comment, delete_check, get_check, list_checks, list_comments, rename_check, save_check
from .document_parser import DocumentParseError, parse_uploaded_document


api = Blueprint("api", __name__)


@api.get("/health")
def health():
    response = jsonify({"status": "ok", "service": "AI 检测小助手"})
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response, 200


@api.get("/checks")
def fetch_checks():
    response = jsonify({"items": list_checks()})
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response, 200


@api.get("/checks/<int:check_id>")
def fetch_check(check_id: int):
    record = get_check(check_id)
    if record is None:
        return jsonify({"message": "记录不存在"}), 404
    response = jsonify(record)
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response, 200


@api.post("/checks")
def create_check():
    if request.files:
        uploaded_file = request.files.get("file")
        try:
            default_title, text = parse_uploaded_document(uploaded_file)
        except DocumentParseError as exc:
            return jsonify({"message": str(exc)}), 400
        except RuntimeError as exc:
            return jsonify({"message": str(exc)}), 500

        raw_title = request.form.get("title") or default_title or "未命名检测"
        title = raw_title.strip()[:80]
    else:
        payload = request.get_json(silent=True) or {}
        title = (payload.get("title") or "未命名检测").strip()[:80]
        text = (payload.get("text") or "").strip()

    if not text:
        return jsonify({"message": "请先输入需要检测的文本"}), 400

    result = analyze_text(text)
    record = save_check(title, text, result)
    response = jsonify(record)
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response, 201


@api.delete("/checks/<int:check_id>")
def remove_check(check_id: int):
    if get_check(check_id) is None:
        return jsonify({"message": "记录不存在"}), 404
    delete_check(check_id)
    return "", 204


@api.patch("/checks/<int:check_id>")
def update_check(check_id: int):
    if get_check(check_id) is None:
        return jsonify({"message": "记录不存在"}), 404
    payload = request.get_json(silent=True) or {}
    title = (payload.get("title") or "").strip()[:80]
    if not title:
        return jsonify({"message": "标题不能为空"}), 400
    rename_check(check_id, title)
    return "", 204


@api.get("/checks/<int:check_id>/comments")
def fetch_comments(check_id: int):
    if get_check(check_id) is None:
        return jsonify({"message": "记录不存在"}), 404
    response = jsonify({"items": list_comments(check_id)})
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response, 200


@api.post("/checks/<int:check_id>/comments")
def create_comment(check_id: int):
    if get_check(check_id) is None:
        return jsonify({"message": "记录不存在"}), 404

    payload = request.get_json(silent=True) or {}
    author = (payload.get("author") or "匿名").strip()[:40]
    role = (payload.get("role") or "用户").strip()[:40]
    content = (payload.get("content") or "").strip()

    if not content:
        return jsonify({"message": "点评内容不能为空"}), 400

    comment = add_comment(check_id, author, role, content[:1000])
    response = jsonify(comment)
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response, 201


