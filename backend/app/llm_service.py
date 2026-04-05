"""
改写建议生成模块。
默认使用本地模板（无需 API Key）。
通过环境变量调用外部大模型：
  AI_SUGGESTION_PROVIDER=deepseek  需要 DEEPSEEK_API_KEY
"""
import logging
import os
os.environ["DEEPSEEK_API_KEY"] = "sk-152e6ba510fb45559040114b85b5647f"
os.environ["AI_SUGGESTION_PROVIDER"] = "deepseek"
import requests as http_requests

logger = logging.getLogger(__name__)

DEFAULT_DIRECTION_MAP = {
    "high": "本段含有高风险声明（引用/法条）或大量公式化表达，建议先逐一核实声明真实性，再重写句式结构，补入经过核实的具体事实。",
    "medium": "本段存在需核实的数据或专家引述，建议追溯原始来源确认后保留，同时减少模板化连接词，增加真实细节。",
    "low": "整体表达较自然，可只对个别引述做轻量核实，确认来源可信后再使用。",
}


def generate_suggestions(paragraph: str, risk_level: str, feature_summary: dict, reasons: list[str]) -> dict:
    provider = os.getenv("AI_SUGGESTION_PROVIDER", "local-template")


    if provider == "deepseek":
        try:
            return _call_deepseek(paragraph, risk_level, feature_summary, reasons)
        except Exception as exc:
            logger.warning("DeepSeek 调用失败，回退本地模板：%s", exc)
            result = _build_local_result(risk_level, feature_summary, reasons)
            result["notes"] = [f"DeepSeek 调用失败（{exc}），已使用本地模板兜底。"]
            return result

    return _build_local_result(risk_level, feature_summary, reasons)



# 外部 LLM 调用


def _build_prompt(paragraph: str, risk_level: str, feature_summary: dict, reasons: list[str]) -> str:
    level_label = {"high": "高", "medium": "中", "low": "低"}.get(risk_level, "中")
    # 区分声明警告和公式化原因
    claim_reasons = [r for r in reasons if r.startswith("⚠")]
    reasons_text = "\n".join(f"- {r}" for r in reasons) if reasons else "- 整体表达偏规整，建议补入更具体的语境和个人化表达"
    claim_block = (
        "\n【需优先核实的声明】\n" + "\n".join(f"- {r}" for r in claim_reasons)
        if claim_reasons else ""
    )
    return f"""你是学术写作核查助手。以下段落被标记为"{level_label}风险"——可能包含AI编造的内容或公式化表达。
{claim_block}
【段落原文】
{paragraph}

【检测原因】
{reasons_text}

【检测特征数据】
- 句长方差：{feature_summary.get("length_variance", "N/A")}（越小句式越均匀，越像AI）
- 连接词密度：{feature_summary.get("connective_density", "N/A")}（越高越像模板化输出）
- 词汇多样性（TTR）：{feature_summary.get("ttr", "N/A")}（越低重复越多）
- 套话数量：{feature_summary.get("cliche_count", "N/A")}（套话越多原创感越弱）

请给出：
1. **修改方向**（2-3句：先说需核实哪些声明，再说如何改写表达）
2. **具体建议**（3-5条，每条以动词开头，可操作，优先针对可疑声明）
3. **改写示例**（直接给出改写后的段落或句子，不要重复原文，只展示修改后的版本）

要求：优先处理引用/数据/法条的真实性问题，再处理表达方式。改写示例中不要出现"原文"字样。"""


def _parse_llm_response(
    content: str,
    provider: str,
    risk_level: str,
    feature_summary: dict,
    reasons: list[str],
) -> dict:
    """解析 LLM 返回内容，提取方向 / 建议 / 示例三段。"""
    lines = [line.strip() for line in content.splitlines() if line.strip()]

    direction_parts: list[str] = []
    actions: list[str] = []
    example_parts: list[str] = []
    current_section: str | None = None

    for line in lines:
        low = line.lower()
        if "修改方向" in low or (line.startswith("1") and "方向" in line):
            current_section = "direction"
            continue
        if "具体建议" in low or (line.startswith("2") and "建议" in line):
            current_section = "actions"
            continue
        if "改写示例" in low or (line.startswith("3") and "示例" in line):
            current_section = "example"
            continue

        cleaned = line.lstrip("0123456789.-•*· ").strip()
        if not cleaned:
            continue
        if current_section == "direction":
            direction_parts.append(cleaned)
        elif current_section == "actions":
            actions.append(cleaned)
        elif current_section == "example":
            example_parts.append(cleaned)

    direction = " ".join(direction_parts) or DEFAULT_DIRECTION_MAP.get(risk_level, "")
    if not actions:
        # 解析失败，回退本地模板的 actions
        actions = _build_local_result(risk_level, feature_summary, reasons)["actions"]

    return {
        "enabled": True,
        "provider": provider,
        "direction": direction,
        "actions": actions[:5],
        "example_rewrite": "\n".join(example_parts),
        "reason_summary": "；".join(reasons) if reasons else "整体表达偏规整，可增加自然写作痕迹。",
        "raw_response": content,
    }



def _call_deepseek(paragraph: str, risk_level: str, feature_summary: dict, reasons: list[str]) -> dict:
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY 未设置")

    prompt = _build_prompt(paragraph, risk_level, feature_summary, reasons)
    response = http_requests.post(
        "https://api.deepseek.com/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
        },
        timeout=30,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    return _parse_llm_response(content, "deepseek", risk_level, feature_summary, reasons)



# 本地模板（默认兜底）


def _build_local_result(risk_level: str, feature_summary: dict, reasons: list[str]) -> dict:
    direction = DEFAULT_DIRECTION_MAP.get(risk_level, DEFAULT_DIRECTION_MAP["medium"])
    actions: list[str] = []

    if feature_summary.get("connective_density", 0) > 0.3:
        actions.append('减少\u201c首先、其次、因此、总之\u201d等串联词，改成更自然的过渡。')
    if feature_summary.get("cliche_count", 0) > 0:
        actions.append("替换套话表达，把抽象判断改成更具体的事实、场景或个人观察。")
    if feature_summary.get("length_variance", 0) < 80:
        actions.append("拉开句长差异，混合短句、解释句和补充句，增加节奏变化。")
    if feature_summary.get("ttr", 1) < 0.62:
        actions.append("减少重复字词，换用更贴近语境的近义表达。")
    if feature_summary.get("punct_diversity", 1) < 0.35:
        actions.append("适当调整标点和停顿方式，避免整段语气过于平直。")

    if not actions:
        actions = [
            "补入更具体的情境、对象或经历，减少泛泛而谈。",
            "把结论句拆开重写，避免一口气给出过于完整的标准答案。",
            "保留原意的同时加入更自然的主观判断或限制条件。",
        ]

    return {
        "enabled": True,
        "provider": "local-template",
        "direction": direction,
        "actions": actions[:5],
        "example_rewrite": _make_example(risk_level),
        "reason_summary": "；".join(reasons) if reasons else "整体表达偏规整，可增加自然写作痕迹。",
    }


def _make_example(paragraph: str, risk_level: str) -> str:
    if risk_level == "high":
        return (
            "近期研究显示，生成式AI在大学生课程写作中的使用已相当普遍"
            "（注：需根据实际调查数据补充具体比例）。"
            "有学者指出，AI工具正在重塑学术实践的规范，这引发了关于学术诚信与学习效能的深入讨论。"
        )
    if risk_level == "medium":
        return (
            "相关领域的研究表明，该问题正受到学界的广泛关注"
            "（具体数据可参考教育部或权威机构的近期报告）。"
            "在实践层面，各方正在探索兼顾效率与规范的应对路径。"
        )
    return (
        "这一现象值得持续关注。结合实际情况来看，"
        "不同场景下的效果可能存在差异，建议在具体使用时结合实际背景加以判断。"
    )