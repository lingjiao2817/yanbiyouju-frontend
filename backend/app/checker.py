"""
AI 内容事实核查引擎。
核心评分逻辑（造假风险分 0~100）：
  = 公式化程度（统计特征 ± 困惑度）+ 可疑声明加权
  - 每处高风险声明（引用/法条）+20 分，中风险声明（数据/专家观点）+8 分，最多叠加 50 分
  - 若 ENABLE_PERPLEXITY=1：困惑度占公式化部分的 40%，统计特征占 60%
"""
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from statistics import mean, pstdev
from time import perf_counter

import numpy as np

from .crossref_service import recommend_papers
from .llm_service import generate_suggestions
from .perplexity_service import calc_perplexity, is_enabled as perplexity_enabled

_RE_SPLIT_PARAGRAPH = re.compile(r"\n{2,}|\r\n{2,}|\n")
_RE_COLLAPSE_SPACE  = re.compile(r"\s+")
_RE_SPLIT_SENTENCE  = re.compile(r"[。！？!?]+")
_RE_PUNCTUATIONS    = re.compile(r"[，。！？、；：,.!?;:]")





RISK_LABELS = {"low": "低风险", "medium": "中风险", "high": "高风险"}

CONNECTIVES = [
    "首先", "其次", "此外", "因此", "总之", "然而", "同时",
    "值得注意的是", "综上所述", "由此可见",
]
CLICHES = [
    "在当今社会", "随着技术的发展", "随着时代的发展",
    "具有重要意义", "发挥着重要作用", "不可忽视",
    "不难看出", "总的来说", "综上所述", "由此可见",
]
TEMPLATE_PATTERNS = [
    "本文将从", "可以看出", "值得注意的是",
    "从某种意义上说", "这说明", "由此可知",
]
PUNCTUATIONS = r"[，。！？、；：,.!?;:]"

# ── 造假声明识别模式 ─────────────────────────────────────────────────

CLAIM_TYPE_TIPS = {
    "citation":  "引用文献需在知网/万方/Semantic Scholar等数据库中核实是否真实存在",
    "legal":     "法条引用需在国家法律法规数据库（pkulaw.com / 法律法规全文检索系统）核实原文",
    "statistic": "精确数据需追溯原始统计来源，AI生成的数字常被虚构或夸大",
    "authority": "专家观点需核实该人物真实存在及原始表述出处",
}

_CITATION_RE = re.compile(
    r'《[^》]{2,50}》\s*[（(][^）)]{2,25}[，,]\s*\d{4}\s*[）)]'
)
_LEGAL_RE = re.compile(
    r'第\s*\d+\s*条(?:[第\s]*[款项\d])*'
    r'|《[^》]{2,40}(?:法|条例|规定|办法|准则|意见|通知|规范)》'
)
_STAT_RE = re.compile(
    r'(?:达到?|高达|超过|约为?|仅有|占比|比例为?|增长|降低|下降|提升)\s*\d+(?:\.\d+)?\s*%'
    r'|\b\d+(?:\.\d+)?\s*(?:%|％)'
    r'|\d+(?:\.\d+)?\s*(?:亿|万)\s*(?:人|元|件|篇|项)'
)
_AUTHORITY_RE = re.compile(
    r'[\u4e00-\u9fff]{2,4}\s*(?:教授|学者|研究员|院士|博士|专家)'
    r'\s*(?:认为|指出|表示|研究发现|强调|提出|发现)'
)

_CLAIM_PATTERNS: list[tuple] = [
    (_CITATION_RE,  "citation",  "high"),
    (_LEGAL_RE,     "legal",     "high"),
    (_STAT_RE,      "statistic", "medium"),
    (_AUTHORITY_RE, "authority", "medium"),
]


#核心函数一
def analyze_text(text: str) -> dict:
    started_at = perf_counter()
    paragraphs = normalize_paragraphs(text)
    if not paragraphs:
        paragraphs = [text.strip()]

    # ── 阶段一：并行处理每个段落的独立计算 ──────────────────────────
    # 包括：特征提取、声明扫描、困惑度、文献推荐（均无段落间依赖）
    def _process_paragraph(args: tuple) -> dict:
        index, paragraph = args
        features  = extract_features(paragraph)
        ppl       = calc_perplexity(paragraph)
        claims    = extract_claims(paragraph)
        score     = compute_ai_score(features, ppl, claims)
        paper_result = recommend_papers(paragraph, top_k=3)
        return {
            "index":          index,
            "text":           paragraph,
            "score":          round(score, 1),
            "perplexity":     round(ppl, 2) if ppl is not None else None,
            "claims":         claims,
            "paper_result":   paper_result,
            "feature_summary": build_feature_summary(features),
            "features":       normalize_features(features),
        }

    max_workers = min(len(paragraphs), 4)
    raw_results: dict[int, dict] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_process_paragraph, (i, p)): i
            for i, p in enumerate(paragraphs, start=1)
        }
        for future in as_completed(futures):
            result = future.result()
            raw_results[result["index"]] = result

    # 按原始顺序排列，汇总分数后计算相对风险等级
    ordered = [raw_results[i] for i in sorted(raw_results)]
    scores = [r["score"] for r in ordered]
    risk_levels = determine_risk_levels(scores)

    # ── 阶段二：依赖 risk_level 的串行后处理 ─────────────────────────
    # generate_suggestions 需要知道风险等级，必须在阶段一完成后执行
    paragraph_reports: list[dict] = []
    paper_recommendations: list[dict] = []

    for item, risk_level in zip(ordered, risk_levels):
        reasons = explain_detection(item["feature_summary"], item.get("perplexity"), item["claims"])
        item["risk_level"]  = risk_level
        item["risk_label"]  = RISK_LABELS[risk_level]
        item["reasons"]     = reasons
        item["reason_text"] = "；".join(reasons) if reasons else "整体表达较自然。"
        item["suggestion"]  = generate_suggestions(
            item["text"], risk_level, item["feature_summary"], reasons
        )
        paper_recommendations.append({"paragraph_index": item["index"], **item.pop("paper_result")})
        paragraph_reports.append(item)

    overview = build_overview(paragraph_reports)
    elapsed_ms = round((perf_counter() - started_at) * 1000, 2)

    return {
        "overview": overview,
        "paragraphs": paragraph_reports,
        "paper_recommendations": paper_recommendations,
        "meta": {
            "paragraph_count": len(paragraph_reports),
            "perplexity_enabled": perplexity_enabled(),
            "suggestion_provider": (
                paragraph_reports[0]["suggestion"]["provider"]
                if paragraph_reports
                else "local-template"
            ),
            "paper_provider": next(
                (item["provider"] for item in paper_recommendations if item.get("provider")),
                "semantic-scholar",
            ),
            "processing_ms": elapsed_ms,
        },
    }



# 文本分段


def normalize_paragraphs(text: str) -> list[str]:
    if not text.strip():
        return []
    raw_parts = _RE_SPLIT_PARAGRAPH.split(text)
    cleaned = [_RE_COLLAPSE_SPACE.sub(" ", part).strip() for part in raw_parts]
    long_enough = [part for part in cleaned if len(part) >= 20]
    return long_enough or [part for part in cleaned if part]



# 声明提取（可疑引用/法条/数据/权威观点）


def extract_claims(text: str) -> list[dict]:
    """
    扫描段落中的"可疑声明"，返回命中列表。
    每项：{ text, type, risk, tip, start, end }
    """
    found: list[dict] = []
    seen_spans: list[tuple[int, int]] = []

    for pattern, claim_type, risk in _CLAIM_PATTERNS:
        for m in pattern.finditer(text):
            span = (m.start(), m.end())
            # 跳过与已命中区间重叠的匹配
            if any(s < span[1] and span[0] < e for s, e in seen_spans):
                continue
            seen_spans.append(span)
            found.append({
                "text":  m.group(),
                "type":  claim_type,
                "risk":  risk,
                "tip":   CLAIM_TYPE_TIPS[claim_type],
                "start": m.start(),
                "end":   m.end(),
            })

    return found


# 特征提取

#核心函数二
def extract_features(text: str) -> dict:         
    sentences = split_sentences(text)
    lengths = [len(s) for s in sentences] or [len(text)]
    chars = [c for c in text if not c.isspace()]
    puncts = _RE_PUNCTUATIONS.findall(text)
    template_hits = sum(text.count(p) for p in TEMPLATE_PATTERNS)
    connective_count = sum(text.count(w) for w in CONNECTIVES)
    cliche_count = sum(text.count(c) for c in CLICHES)

    return {
        "sentence_count": len(sentences),
        "avg_sentence_length": round(sum(lengths) / max(len(lengths), 1), 2),
        "length_variance": float(np.var(lengths)) if lengths else 0.0,
        "connective_density": connective_count / max(len(sentences), 1),
        "ttr": len(set(chars)) / max(len(chars), 1),
        "cliche_count": cliche_count,
        "punct_diversity": len(set(puncts)) / max(len(puncts), 1),
        "template_hits": template_hits,
        "repetition_ratio": repetition_ratio(chars),
    }


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _RE_SPLIT_SENTENCE.split(text) if s.strip()]


def repetition_ratio(chars: list[str]) -> float:
    if not chars:
        return 0.0
    counter = Counter(chars)
    repeated = sum(count for count in counter.values() if count > 1)
    return repeated / len(chars)



# 综合评分

#核心函数三
def compute_ai_score(
    features: dict,
    perplexity: float | None = None,
    claims: list[dict] | None = None,
) -> float:
    """
    造假风险综合评分，返回 0~100（越高越可疑）。

    公式化得分（base）：
      有困惑度：0.4 × ppl_score + 0.6 × stat_score
      无困惑度：stat_score

    声明加权（叠加，最多 +50）：
      每处 high 级声明（引用/法条）+20
      每处 medium 级声明（数据/专家）+8
    """
    stat_score = _stat_score(features)

    if perplexity is not None:
        ppl_score = 100.0 * (1 - min(perplexity, 200) / 200)
        base = 0.4 * ppl_score + 0.6 * stat_score
    else:
        base = stat_score

    claim_bonus = 0.0
    for claim in (claims or []):
        claim_bonus += 20.0 if claim["risk"] == "high" else 8.0
    claim_bonus = min(claim_bonus, 50.0)

    return max(0.0, min(100.0, base + claim_bonus))


#核心函数四
def _stat_score(features: dict) -> float:       
    """纯统计特征评分（总和 100 分）。"""
    score = 0.0
    score += 22 * (1 - min(features["length_variance"], 400) / 400)
    score += 18 * min(features["connective_density"] / 0.45, 1)
    score += 16 * (1 - min(max(features["ttr"], 0), 1))
    score += 14 * min(features["cliche_count"] / 3, 1)
    score += 12 * (1 - min(features["punct_diversity"], 1))
    score += 10 * min(features["template_hits"] / 3, 1)
    score += 8 * min(features["repetition_ratio"] / 0.85, 1)
    return score



# 风险等级划分

#核心函数五
def determine_risk_levels(scores: list[float]) -> list[str]:
    if not scores:
        return []
    if len(scores) == 1:
        return [score_to_level(scores[0])]

    score_mean = mean(scores)
    score_std = pstdev(scores) if len(scores) > 1 else 0
    levels = []
    for score in scores:
        if score_std == 0:
            levels.append(score_to_level(score))
        elif score > score_mean + 0.5 * score_std:
            levels.append("high")
        elif score > score_mean - 0.5 * score_std:
            levels.append("medium")
        else:
            levels.append("low")
    return levels


def score_to_level(score: float) -> str:
    if score >= 65:
        return "high"
    if score >= 40:
        return "medium"
    return "low"



# 原因解释


def explain_detection(
    feature_summary: dict,
    perplexity: float | None = None,
    claims: list[dict] | None = None,
) -> list[str]:
    reasons: list[str] = []

    # 可疑声明警告（最优先）
    type_labels = {"citation": "文献引用", "legal": "法条引用", "statistic": "精确数据", "authority": "专家观点"}
    for claim in (claims or []):
        label = type_labels.get(claim["type"], claim["type"])
        prefix = "⚠ 高风险" if claim["risk"] == "high" else "⚠ 需核实"
        snippet = claim["text"][:30] + ("…" if len(claim["text"]) > 30 else "")
        reasons.append(f'{prefix}：{label}「{snippet}」——{claim["tip"]}')

    # 公式化文本特征
    if perplexity is not None and perplexity < 80:
        reasons.append(f'困惑度偏低({perplexity:.1f})，文本对语言模型"过于好预测"，典型 AI 生成特征')
    if feature_summary["length_variance"] < 80:
        reasons.append("句子长度过于均匀，整体节奏比较像模板化生成")
    if feature_summary["connective_density"] > 0.3:
        reasons.append("连接词使用偏多，段落推进方式较机械")
    if feature_summary["cliche_count"] > 0:
        reasons.append("出现常见套话，原创表达感偏弱")
    if feature_summary["ttr"] < 0.62:
        reasons.append("字词重复度偏高，词汇变化不足")
    if feature_summary["punct_diversity"] < 0.35:
        reasons.append("标点变化较少，语气层次不够自然")
    if feature_summary["template_hits"] > 0:
        reasons.append('命中总结式模板短语，容易带来"AI味"')

    return reasons or ["整体表达偏规整，建议适当加入更具体的语境和个人化表达"]



# 整体概览


def build_overview(paragraphs: list[dict]) -> dict:
    scores = [item["score"] for item in paragraphs]
    risk_counter = Counter(item["risk_level"] for item in paragraphs)
    average_score = round(sum(scores) / max(len(scores), 1), 1) if scores else 0.0
    high_count = risk_counter.get("high", 0)
    medium_count = risk_counter.get("medium", 0)
    risk_level = overall_level(average_score, high_count)

    # 汇总声明数量
    all_claims = [c for item in paragraphs for c in item.get("claims", [])]
    high_claims = [c for c in all_claims if c["risk"] == "high"]
    med_claims  = [c for c in all_claims if c["risk"] == "medium"]

    top_reasons: Counter = Counter()
    for item in paragraphs:
        for reason in item["reasons"]:
            top_reasons[reason] += 1

    highlights = [reason for reason, _ in top_reasons.most_common(3)]

    claim_note = ""
    if high_claims or med_claims:
        claim_note = (
            f"检测到 {len(high_claims)} 处高风险声明（引用/法条）、"
            f"{len(med_claims)} 处需核实声明（数据/专家观点），请逐一核实后使用。"
        )

    summary = (
        f"共分析 {len(paragraphs)} 段文本，其中高风险 {high_count} 段，中风险 {medium_count} 段。"
        + (f" {claim_note}" if claim_note else "")
        + f" 主要问题：{'；'.join(highlights) if highlights else '整体表达较自然'}。"
    )

    return {
        "score": average_score,
        "risk_level": risk_level,
        "risk_label": RISK_LABELS[risk_level],
        "summary": summary,
        "confidence_note": "本结果基于统计特征与事实核查规则，供提交前自查使用，不等同于学校或平台的官方检测结论。",
        "claim_stats": {
            "total": len(all_claims),
            "high": len(high_claims),
            "medium": len(med_claims),
        },
        "risk_distribution": {
            "low": risk_counter.get("low", 0),
            "medium": risk_counter.get("medium", 0),
            "high": risk_counter.get("high", 0),
        },
    }


def overall_level(average_score: float, high_count: int) -> str:
    if high_count >= 2 or average_score >= 65:
        return "high"
    if high_count >= 1 or average_score >= 40:
        return "medium"
    return "low"



# 特征格式化（供前端展示）


def build_feature_summary(features: dict) -> dict:
    return {
        "length_variance": round(features["length_variance"], 2),
        "connective_density": round(features["connective_density"], 3),
        "ttr": round(features["ttr"], 3),
        "cliche_count": int(features["cliche_count"]),
        "punct_diversity": round(features["punct_diversity"], 3),
        "template_hits": int(features["template_hits"]),
        "avg_sentence_length": round(features["avg_sentence_length"], 2),
        "sentence_count": int(features["sentence_count"]),
        "repetition_ratio": round(features["repetition_ratio"], 3),
    }


def normalize_features(features: dict) -> list[dict]:
    return [
        {
            "key": "avg_sentence_length",
            "label": "平均句长",
            "value": round(features["avg_sentence_length"], 2),
            "hint": "句子长度过于接近时，容易显得像模板输出。",
        },
        {
            "key": "length_variance",
            "label": "句长方差",
            "value": round(features["length_variance"], 2),
            "hint": "方差越小，句式通常越规整，AI味越重。",
        },
        {
            "key": "connective_density",
            "label": "连接词密度",
            "value": round(features["connective_density"], 3),
            "hint": "连接词过多可能让段落显得机械。",
        },
        {
            "key": "ttr",
            "label": "词汇多样性",
            "value": round(features["ttr"], 3),
            "hint": "多样性越低，重复表达越明显，越像AI。",
        },
        {
            "key": "cliche_count",
            "label": "套话数量",
            "value": int(features["cliche_count"]),
            "hint": "套话越多，原创感越弱。",
        },
        {
            "key": "punct_diversity",
            "label": "标点多样性",
            "value": round(features["punct_diversity"], 3),
            "hint": "标点变化影响语气层次，AI文本通常较单调。",
        },
        {
            "key": "template_hits",
            "label": "模板短语命中",
            "value": int(features["template_hits"]),
            "hint": "命中越多，越容易被认为像 AI 概括文本。",
        },
    ]
