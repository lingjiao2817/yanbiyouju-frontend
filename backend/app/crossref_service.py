import os
from typing import Any

import jieba.analyse
import requests


SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"


def recommend_papers(paragraph: str, top_k: int = 3) -> dict:
    keywords = extract_keywords(paragraph)
    if not keywords:
        return {
            "enabled": False,
            "provider": "semantic-scholar",
            "status": "skipped",
            "query": "",
            "items": [],
            "summary": "当前段落关键词不足，未生成文献推荐。",
        }

    query = " ".join(keywords)
    if os.getenv("DISABLE_PAPER_SEARCH", "0") == "1":
        return {
            "enabled": False,
            "provider": "semantic-scholar",
            "status": "disabled",
            "query": query,
            "items": [],
            "summary": "已关闭在线文献推荐，当前返回空结果。",
        }

    try:
        response = requests.get(
            SEMANTIC_SCHOLAR_URL,
            params={
                "query": query,
                "limit": top_k,
                "fields": "title,authors,year,citationCount,url,externalIds",
            },
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        return {
            "enabled": False,
            "provider": "semantic-scholar",
            "status": "error",
            "query": query,
            "items": [],
            "summary": f"文献推荐请求失败：{exc}",
        }

    items = [format_paper(item) for item in payload.get("data", [])]
    return {
        "enabled": True,
        "provider": "semantic-scholar",
        "status": "ok",
        "query": query,
        "items": items,
        "summary": "已根据段落关键词生成真实文献推荐。" if items else "未检索到足够相关的文献结果。",
    }


def extract_keywords(paragraph: str) -> list[str]:
    return [item.strip() for item in jieba.analyse.extract_tags(paragraph, topK=5) if item.strip()]


def format_paper(item: dict[str, Any]) -> dict:
    authors = item.get("authors", [])[:3]
    external_ids = item.get("externalIds", {}) or {}
    return {
        "title": item.get("title") or "未命名文献",
        "authors": ", ".join(author.get("name", "") for author in authors if author.get("name")),
        "year": item.get("year"),
        "citations": item.get("citationCount", 0),
        "doi": external_ids.get("DOI", ""),
        "url": item.get("url") or "",
    }
