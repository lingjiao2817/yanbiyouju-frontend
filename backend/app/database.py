import json
import sqlite3
from pathlib import Path

from flask import current_app, g

from .checker import analyze_text


SCHEMA = """
CREATE TABLE IF NOT EXISTS checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    input_text TEXT NOT NULL,
    overall_risk TEXT NOT NULL,
    summary TEXT NOT NULL,
    result_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    check_id INTEGER NOT NULL,
    author TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (check_id) REFERENCES checks(id) ON DELETE CASCADE
);
"""


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        db_path = Path(current_app.config["DATABASE_PATH"])
        db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(db_path)
        connection.row_factory = sqlite3.Row
        g.db = connection
    return g.db


def close_db(_error=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    db = get_db()
    db.executescript(SCHEMA)
    db.commit()
    seed_demo_record()
    seed_demo_comment()


def seed_demo_record() -> None:
    db = get_db()
    exists = db.execute("SELECT COUNT(1) FROM checks").fetchone()[0]
    if exists:
        return

    sample_text = (
        "据《人工智能赋能高校思政教育研究》(李明，2024)指出，大学生使用生成式AI辅助完成课程作业的比例已达67%。\n"
        "《教育数字化促进条例》第12条明确规定，所有高校必须在课程论文中披露AI使用痕迹。\n"
        "王磊教授认为，AI写作已经100%改变了中国大学生的学术规范。\n\n"
        "[1] 李明. 人工智能赋能高校思政教育研究[J]. 2024.\n"
        "[2] 王磊. AI与课程论文诚信. XX大学学报, 待查."
    )
    sample_result = analyze_text(sample_text)
    record = save_check("演示样本文本", sample_text, sample_result)
    add_comment(record["id"], "张老师", "指导教师", "第二段法条风险最高，建议先去国家法律法规数据库核对。")


def seed_demo_comment() -> None:
    db = get_db()
    comment_count = db.execute("SELECT COUNT(1) FROM comments").fetchone()[0]
    if comment_count:
        return

    first_check = db.execute("SELECT id FROM checks ORDER BY id ASC LIMIT 1").fetchone()
    if first_check is None:
        return

    add_comment(first_check["id"], "张老师", "指导教师", "优先核对法条和统计数据，再决定正文是否保留这些表述。")


def save_check(title: str, input_text: str, result: dict) -> dict:
    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO checks (title, input_text, overall_risk, summary, result_json)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            title,
            input_text,
            result["overview"]["risk_level"],
            result["overview"]["summary"],
            json.dumps(result, ensure_ascii=False),
        ),
    )
    db.commit()
    return get_check(cursor.lastrowid)


def list_checks(limit: int = 12) -> list[dict]:
    db = get_db()
    rows = db.execute(
        """
        SELECT id, title, overall_risk, summary, created_at
        FROM checks
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


def get_check(check_id: int) -> dict | None:
    db = get_db()
    row = db.execute("SELECT * FROM checks WHERE id = ?", (check_id,)).fetchone()
    if row is None:
        return None

    payload = dict(row)
    raw_result = json.loads(payload.pop("result_json"))
    payload["result"] = upgrade_result_payload(payload["id"], payload["input_text"], raw_result)
    payload["comments"] = list_comments(check_id)
    return payload


def list_comments(check_id: int) -> list[dict]:
    db = get_db()
    rows = db.execute(
        """
        SELECT id, check_id, author, role, content, created_at
        FROM comments
        WHERE check_id = ?
        ORDER BY id DESC
        """,
        (check_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def add_comment(check_id: int, author: str, role: str, content: str) -> dict:
    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO comments (check_id, author, role, content)
        VALUES (?, ?, ?, ?)
        """,
        (check_id, author, role, content),
    )
    db.commit()
    row = db.execute(
        """
        SELECT id, check_id, author, role, content, created_at
        FROM comments
        WHERE id = ?
        """,
        (cursor.lastrowid,),
    ).fetchone()
    return dict(row)


def upgrade_result_payload(check_id: int, input_text: str, result: dict) -> dict:
    overview = result.get("overview", {})
    missing_new_fields = (
        "verification_routes" not in result
        or "recommended_actions" not in result
        or "confidence_note" not in overview
    )

    if not missing_new_fields:
        return result

    refreshed = analyze_text(input_text)
    db = get_db()
    db.execute(
        """
        UPDATE checks
        SET overall_risk = ?, summary = ?, result_json = ?
        WHERE id = ?
        """,
        (
            refreshed["overview"]["risk_level"],
            refreshed["overview"]["summary"],
            json.dumps(refreshed, ensure_ascii=False),
            check_id,
        ),
    )
    db.commit()
    return refreshed
