import re
from collections import Counter

from .rules_loader import load_rules


SEVERITY_SCORES = {"low": 1, "medium": 2, "high": 3}
SEVERITY_TEXT = {"low": "低", "medium": "中", "high": "高"}
CATEGORY_LABELS = {
    "citation": "文献引用",
    "law": "法条法规",
    "data": "数据统计",
    "entity": "人名机构",
    "claim": "绝对化结论",
}
SOURCE_HINTS = (
    "教育部",
    "国家统计局",
    "中国知网",
    "知网",
    "人民网",
    "新华社",
    "联合国",
    "世界银行",
    "Crossref",
    "DOI",
    "doi",
    "CNKI",
    "中国教育报",
    "国务院",
    "最高人民法院",
)
ROUTE_LIBRARY = {
    "citation": {
        "title": "文献题录核验",
        "platforms": ["中国知网", "Google Scholar", "Crossref"],
        "instruction": "先搜完整题名，再核对作者、年份、期刊、卷期和 DOI。",
    },
    "law": {
        "title": "法条原文核验",
        "platforms": ["国家法律法规数据库", "中国政府网", "教育部官网"],
        "instruction": "重点核对法规名称、条次、版本时间和发布机关。",
    },
    "data": {
        "title": "统计来源核验",
        "platforms": ["国家统计局", "教育部", "权威调查报告"],
        "instruction": "优先查找原始统计报告，确认样本范围、年份和发布机构。",
    },
    "entity": {
        "title": "人名机构背书核验",
        "platforms": ["高校官网", "研究机构官网", "原始论文或公告"],
        "instruction": "不要只核对名字，要追到原始讲话、论文、新闻稿或官方公告。",
    },
    "claim": {
        "title": "结论措辞复核",
        "platforms": ["原始证据", "课程要求", "指导教师意见"],
        "instruction": "把绝对化说法改成审慎表述，并补上可验证依据。",
    },
}


def analyze_text(text: str) -> dict:
    rules = load_rules()
    paragraphs = split_paragraphs(text)
    paragraph_reports = []
    flags = []

    for index, paragraph in enumerate(paragraphs, start=1):
        issues = deduplicate_flags(scan_paragraph(paragraph, index, rules))
        paragraph_reports.append(
            {
                "index": index,
                "text": paragraph,
                "risk_level": paragraph_risk(issues),
                "notes": [issue["explanation"] for issue in issues],
                "matched_categories": [issue["category"] for issue in issues],
            }
        )
        flags.extend(issues)

    reference_checks = analyze_reference_lines(text, rules)
    for item in reference_checks:
        if item["risk_level"] in {"medium", "high"}:
            flags.append(
                {
                    "category": "citation",
                    "category_label": CATEGORY_LABELS["citation"],
                    "severity": item["risk_level"],
                    "severity_text": SEVERITY_TEXT[item["risk_level"]],
                    "label": "参考文献信息不完整或格式异常",
                    "evidence": item["line"],
                    "explanation": "参考文献缺少关键字段时，AI 很容易把不存在的文献伪装成完整引用。",
                    "suggestion": "优先核对作者、年份、刊名、卷期、页码或 DOI。",
                    "paragraph_index": None,
                }
            )

    flags = sorted(flags, key=lambda item: SEVERITY_SCORES[item["severity"]], reverse=True)
    category_counter = Counter(flag["category"] for flag in flags)
    score = min(100, sum(SEVERITY_SCORES[flag["severity"]] for flag in flags) * 8)
    highest_severity = max((SEVERITY_SCORES[flag["severity"]] for flag in flags), default=0)
    if highest_severity == 3:
        score = max(score, 55)
    elif highest_severity == 2:
        score = max(score, 35)
    risk_level = score_to_level(score)

    return {
        "overview": {
            "score": score,
            "risk_level": risk_level,
            "risk_label": severity_label(risk_level),
            "issue_count": len(flags),
            "categories": dict(category_counter),
            "summary": build_summary(risk_level, flags, category_counter),
            "confidence_note": build_confidence_note(flags, reference_checks),
        },
        "flags": flags,
        "paragraphs": paragraph_reports,
        "reference_checks": reference_checks,
        "verification_routes": build_verification_routes(flags),
        "recommended_actions": build_recommended_actions(flags, reference_checks),
        "rules_summary": build_rules_summary(flags, rules),
    }


def split_paragraphs(text: str) -> list[str]:
    parts = [item.strip() for item in re.split(r"\n+", text) if item.strip()]
    return parts or [text.strip()]


def scan_paragraph(paragraph: str, paragraph_index: int, rules: dict) -> list[dict]:
    issues = []
    issues.extend(detect_citation_risks(paragraph, paragraph_index))
    issues.extend(detect_legal_risks(paragraph, paragraph_index))
    issues.extend(detect_data_risks(paragraph, paragraph_index))
    issues.extend(detect_entity_risks(paragraph, paragraph_index))
    issues.extend(detect_overclaim_risks(paragraph, paragraph_index))
    issues.extend(detect_rule_library_risks(paragraph, paragraph_index, rules))
    return issues


def detect_citation_risks(paragraph: str, paragraph_index: int) -> list[dict]:
    issues = []
    title_match = re.search(r"《[^》]{2,40}》", paragraph)
    has_source_anchor = bool(
        re.search(r"(doi|DOI|CNKI|知网|出版社|Journal|Review|学报|期刊|卷|期|pp\.|页码|\[\d+\])", paragraph)
    )
    attribution_cue = re.search(r"(研究表明|学者.*?(指出|认为)|According to|A study by)", paragraph)

    if title_match and not has_source_anchor:
        issues.append(
            make_flag(
                category="citation",
                severity="high",
                label="疑似文献标题存在，但缺少可追溯出处",
                evidence=clip_text(paragraph),
                explanation="段落提到了明确文献标题，但没有出现刊名、作者、年份、DOI 等关键线索，属于 AI 编造文献的高发形式。",
                suggestion="到知网、Google Scholar 或图书馆数据库核对这条文献是否真实存在。",
                paragraph_index=paragraph_index,
            )
        )

    if attribution_cue and not has_source_anchor:
        issues.append(
            make_flag(
                category="citation",
                severity="medium",
                label="出现“研究表明/学者指出”，但没有给出来源",
                evidence=clip_text(paragraph),
                explanation="这类句式常被 AI 用来制造学术感，但若正文没有来源信息，可信度会明显下降。",
                suggestion="补充作者、年份、论文题目或原始出处后再使用。",
                paragraph_index=paragraph_index,
            )
        )

    return issues


def detect_legal_risks(paragraph: str, paragraph_index: int) -> list[dict]:
    law_title = re.search(r"《[^》]{2,30}(法|条例|办法|规定)》", paragraph)
    article_number = re.search(r"第[一二三四五六七八九十百零〇两0-9]{1,8}条", paragraph)
    strong_legal_claim = re.search(r"(明确规定|写明|要求|禁止|应当|必须|违法|构成)", paragraph)

    if (law_title or article_number) and strong_legal_claim:
        severity = "high" if article_number else "medium"
        return [
            make_flag(
                category="law",
                severity=severity,
                label="疑似法条或法规表述需要核对",
                evidence=clip_text(paragraph),
                explanation="文本使用了具体法条或规范性表述，但没有给出版本、发布机关或官方链接，容易把 AI 杜撰条文当成真实依据。",
                suggestion="到国家法律法规数据库或政府官网核对法规名称、条次和适用版本。",
                paragraph_index=paragraph_index,
            )
        ]

    return []


def detect_data_risks(paragraph: str, paragraph_index: int) -> list[dict]:
    data_cue = re.search(r"(数据显示|据统计|调查显示|报告指出|研究表明|比例已达|超过\d+%|达到\d+%)", paragraph)
    number_cue = re.search(r"(\d+(?:\.\d+)?%|％|\d+(?:\.\d+)?万|\d+(?:\.\d+)?亿|\d+\s*(?:人|篇|份|所|次))", paragraph)
    has_authority = any(hint in paragraph for hint in SOURCE_HINTS)

    if data_cue and number_cue and not has_authority:
        return [
            make_flag(
                category="data",
                severity="high",
                label="出现具体统计数据，但没有可靠来源",
                evidence=clip_text(paragraph),
                explanation="AI 常会生成看起来精确的数据和比例，但没有说明采样机构、报告名称或官方发布者时，风险很高。",
                suggestion="补充统计来源、报告年份和发布机构，或删除无法核实的数据。",
                paragraph_index=paragraph_index,
            )
        ]

    return []


def detect_entity_risks(paragraph: str, paragraph_index: int) -> list[dict]:
    named_entity_claim = re.search(
        r"((?:[\u4e00-\u9fa5]{2,4})(?:教授|学者|研究员)|(?:清华大学|北京大学|教育部|哈佛大学|斯坦福大学).{0,8}(指出|认为|发布))",
        paragraph,
    )
    has_source_anchor = bool(re.search(r"(\[\d+\]|doi|DOI|《[^》]+》|发布于|刊于)", paragraph))

    if named_entity_claim and not has_source_anchor:
        return [
            make_flag(
                category="entity",
                severity="medium",
                label="人名或机构背书缺少可追溯引用",
                evidence=clip_text(paragraph),
                explanation="段落借助学者或机构名义增强可信度，但没有给出具体来源，属于典型的“像真的”表述。",
                suggestion="补上原始论文、公开报告或官方公告链接。",
                paragraph_index=paragraph_index,
            )
        ]

    return []


def detect_overclaim_risks(paragraph: str, paragraph_index: int) -> list[dict]:
    overclaim = re.search(r"(100%|完全证明|一致认为|绝对|必然|首次证明|毫无疑问)", paragraph)
    if overclaim:
        return [
            make_flag(
                category="claim",
                severity="low",
                label="存在绝对化结论，建议复核措辞",
                evidence=clip_text(paragraph),
                explanation="过度确定的结论通常需要更强证据支撑，在学术写作里应谨慎使用。",
                suggestion="改成更审慎的表述，并补充证据来源。",
                paragraph_index=paragraph_index,
            )
        ]
    return []


def detect_rule_library_risks(paragraph: str, paragraph_index: int, rules: dict) -> list[dict]:
    issues = []
    fake_authors = find_terms(paragraph, rules.get("fake_authors", []))
    fake_journals = find_terms(paragraph, rules.get("fake_journals", []))
    fake_publishers = find_terms(paragraph, rules.get("fake_publishers", []))
    suspicious_phrases = find_terms(paragraph, rules.get("suspicious_phrases", []))
    suspicious_keywords = find_terms(paragraph, rules.get("suspicious_keywords", []))

    if fake_authors:
        issues.append(
            make_flag(
                category="entity",
                severity="high",
                label="命中规则库中的疑似虚构作者",
                evidence="、".join(fake_authors),
                explanation="这段文本出现了规则库标记的高风险作者名，建议优先核对是否真实存在。",
                suggestion="到知网、学校图书馆或搜索引擎核查作者是否有真实论文记录。",
                paragraph_index=paragraph_index,
            )
        )

    if fake_journals or fake_publishers:
        issues.append(
            make_flag(
                category="citation",
                severity="high",
                label="命中规则库中的疑似虚构期刊或出版社",
                evidence="、".join(fake_journals + fake_publishers),
                explanation="规则库发现了高风险刊名或出版社名，这类引用通常需要立即人工核验。",
                suggestion="优先检索该刊名或出版社是否真实存在，并确认是否与学科方向匹配。",
                paragraph_index=paragraph_index,
            )
        )

    if suspicious_phrases:
        issues.append(
            make_flag(
                category="claim",
                severity="medium",
                label="命中规则库中的高风险表述",
                evidence="、".join(suspicious_phrases),
                explanation="这些句式在 AI 编造文献、数据或绝对化结论时出现频率较高。",
                suggestion="逐句补充出处，或改写为更审慎、可核验的表述。",
                paragraph_index=paragraph_index,
            )
        )

    if suspicious_keywords:
        issues.append(
            make_flag(
                category="citation",
                severity="medium",
                label="命中规则库中的可疑关键词",
                evidence="、".join(suspicious_keywords),
                explanation="规则库标记了这些关键词，说明段落中可能存在伪造来源、伪造 DOI 或模板化引用。",
                suggestion="结合原文上下文逐项核对，不要直接采信。",
                paragraph_index=paragraph_index,
            )
        )

    for pattern in rules.get("suspicious_doi_patterns", []):
        matched = re.findall(pattern, paragraph)
        if matched:
            issues.append(
                make_flag(
                    category="citation",
                    severity="high",
                    label="命中规则库中的可疑 DOI 模式",
                    evidence="、".join(sorted(set(matched))),
                    explanation="这类 DOI 格式被规则库标记为高风险，可能是伪造或模板化生成。",
                    suggestion="到 Crossref 或期刊官网核验 DOI 是否真实可解析。",
                    paragraph_index=paragraph_index,
                )
            )

    return issues


def analyze_reference_lines(text: str, rules: dict) -> list[dict]:
    lines = [line.strip() for line in text.splitlines() if re.match(r"^\s*\[\d+\]", line)]
    results = []

    for line in lines:
        notes = []
        max_score = 0

        if not re.search(r"(19|20)\d{2}", line):
            notes.append("缺少年份信息")
            max_score = max(max_score, SEVERITY_SCORES["high"])

        if not re.search(r"(出版社|Journal|Review|学报|期刊|大学|Press|Conference|会议)", line):
            notes.append("缺少刊名、出版社或会议来源")
            max_score = max(max_score, SEVERITY_SCORES["medium"])

        if not re.search(r"(doi|DOI|pp\.|页|页码|\d+\(\d+\)|第\d+卷|第\d+期)", line):
            notes.append("缺少卷期、页码或 DOI 等细节")
            max_score = max(max_score, SEVERITY_SCORES["medium"])

        if re.search(r"(XX|某某|待补|待查|\?{2,})", line):
            notes.append("包含明显占位或未核实内容")
            max_score = max(max_score, SEVERITY_SCORES["high"])

        fake_journals = find_terms(line, rules.get("fake_journals", []))
        fake_publishers = find_terms(line, rules.get("fake_publishers", []))
        fake_authors = find_terms(line, rules.get("fake_authors", []))
        if fake_journals:
            notes.append(f"命中疑似虚构期刊: {'、'.join(fake_journals)}")
            max_score = max(max_score, SEVERITY_SCORES["high"])
        if fake_publishers:
            notes.append(f"命中疑似虚构出版社: {'、'.join(fake_publishers)}")
            max_score = max(max_score, SEVERITY_SCORES["high"])
        if fake_authors:
            notes.append(f"命中疑似虚构作者: {'、'.join(fake_authors)}")
            max_score = max(max_score, SEVERITY_SCORES["high"])

        for pattern in rules.get("suspicious_doi_patterns", []):
            if re.search(pattern, line):
                notes.append("命中疑似伪造 DOI 规则")
                max_score = max(max_score, SEVERITY_SCORES["high"])

        risk_level = score_to_level(max_score * 20) if max_score else "low"
        results.append({"line": line, "risk_level": risk_level, "notes": notes})

    return results


def build_verification_routes(flags: list[dict]) -> list[dict]:
    category_counter = Counter(flag["category"] for flag in flags)
    routes = []

    for category, count in category_counter.most_common():
        route_meta = ROUTE_LIBRARY[category]
        routes.append(
            {
                "category": category,
                "category_label": CATEGORY_LABELS[category],
                "title": route_meta["title"],
                "count": count,
                "platforms": route_meta["platforms"],
                "instruction": route_meta["instruction"],
            }
        )

    if not routes:
        routes.append(
            {
                "category": "general",
                "category_label": "常规复核",
                "title": "关键事实人工复核",
                "count": 0,
                "platforms": ["课程教材", "图书馆数据库", "权威官网"],
                "instruction": "虽然系统没有识别出高风险项，但课程作业中的关键事实仍建议人工核对。",
            }
        )

    return routes


def build_recommended_actions(flags: list[dict], reference_checks: list[dict]) -> list[str]:
    actions = []
    categories = {flag["category"] for flag in flags}

    if "citation" in categories:
        actions.append("先核对所有带书名号的题名和参考文献行，确认真实存在。")
    if "data" in categories:
        actions.append("把所有百分比、人数和调查结论追溯到原始统计报告。")
    if "law" in categories:
        actions.append("逐条核对法规名称、条次和版本，避免使用不存在的法条。")
    if "entity" in categories:
        actions.append("对于学者、学校或机构结论，必须找到原始论文、公告或新闻稿。")
    if any(item["risk_level"] == "high" for item in reference_checks):
        actions.append("优先修复高风险参考文献条目，再继续完善正文引用。")
    if not actions:
        actions.append("未发现显著高风险项，但交稿前仍建议抽查核心事实和引用。")

    return actions


def build_confidence_note(flags: list[dict], reference_checks: list[dict]) -> str:
    if not flags:
        return "本次结果属于初筛提醒，不等于事实真实性认证。"

    high_risk_count = sum(1 for flag in flags if flag["severity"] == "high")
    high_ref_count = sum(1 for item in reference_checks if item["risk_level"] == "high")
    return (
        f"系统识别到 {high_risk_count} 处高风险表述、{high_ref_count} 条高风险参考文献。"
        "这些内容应优先进行人工检索和原文核验。"
    )


def build_rules_summary(flags: list[dict], rules: dict) -> dict:
    meta = rules.get("__meta", {})
    matched_rule_flags = [
        flag for flag in flags if flag["label"].startswith("命中规则库")
    ]
    return {
        "version": meta.get("version", "unknown"),
        "source_file": meta.get("source_file", "unknown"),
        "loaded_from_sample": meta.get("loaded_from_sample", False),
        "rule_counts": meta.get("rule_counts", {}),
        "matched_rule_flags": len(matched_rule_flags),
    }


def make_flag(
    category: str,
    severity: str,
    label: str,
    evidence: str,
    explanation: str,
    suggestion: str,
    paragraph_index: int | None,
) -> dict:
    return {
        "category": category,
        "category_label": CATEGORY_LABELS[category],
        "severity": severity,
        "severity_text": SEVERITY_TEXT[severity],
        "label": label,
        "evidence": evidence,
        "explanation": explanation,
        "suggestion": suggestion,
        "paragraph_index": paragraph_index,
    }


def deduplicate_flags(flags: list[dict]) -> list[dict]:
    seen = set()
    deduped = []
    for flag in flags:
        key = (flag["category"], flag["label"], flag["evidence"])
        if key not in seen:
            seen.add(key)
            deduped.append(flag)
    return deduped


def find_terms(text: str, terms: list[str]) -> list[str]:
    matches = []
    for term in terms:
        if term and term in text:
            matches.append(term)
    return matches


def clip_text(text: str, limit: int = 120) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 1]}..."


def paragraph_risk(issues: list[dict]) -> str:
    if not issues:
        return "low"
    max_score = max(SEVERITY_SCORES[issue["severity"]] for issue in issues)
    if max_score == 3:
        return "high"
    if max_score == 2:
        return "medium"
    return "low"


def score_to_level(score: int) -> str:
    if score >= 65:
        return "high"
    if score >= 35:
        return "medium"
    return "low"


def severity_label(level: str) -> str:
    return {"low": "低风险", "medium": "中风险", "high": "高风险"}[level]


def build_summary(risk_level: str, flags: list[dict], category_counter: Counter) -> str:
    if not flags:
        return "当前文本未识别出明显高风险表述，但仍建议对关键事实进行人工复核。"

    top_categories = []
    for category, count in category_counter.most_common(3):
        top_categories.append(f"{CATEGORY_LABELS.get(category, category)} {count} 处")

    category_text = "、".join(top_categories)
    level_text = severity_label(risk_level)
    return f"本次共识别 {len(flags)} 处需要复核的内容，主要集中在 {category_text}，整体判断为 {level_text}。"
