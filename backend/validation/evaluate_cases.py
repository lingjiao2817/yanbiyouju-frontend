"""
言必有据 · 检测准确性评估脚本
运行方式：
    cd backend
    python -m validation.evaluate_cases

测试集路径：backend/validation/test_cases.json

指标说明：
  命中率（Recall）   = 正样本中被正确标为中/高风险的比例
  误报率（FPR）      = 负样本中被错误标为中/高风险的比例
  声明召回率         = 期望声明类型中被实际检测到的比例
  精确率（Precision）= 预测为正样本中确实是正样本的比例
  F1                = Precision 与 Recall 的调和均值
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


PROJECT_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_BACKEND_DIR))

from app.checker import analyze_text  # noqa: E402


POSITIVE_LEVELS = {"medium", "high"}
CLAIM_TYPES = {"citation", "legal", "statistic", "authority"}


def run_case(case: dict) -> dict:
    """对单条样本运行检测，返回预测结果摘要。"""
    result = analyze_text(case["text"])

    # 整体风险
    predicted_risk = result["overview"]["risk_level"]

    # 汇总所有段落的 claims
    all_claims = []
    for para in result.get("paragraphs", []):
        all_claims.extend(para.get("claims", []))

    predicted_claim_types = Counter(c["type"] for c in all_claims)

    return {
        "predicted_risk":        predicted_risk,
        "predicted_claim_types": predicted_claim_types,
        "claim_count":           len(all_claims),
        "score":                 result["overview"]["score"],
    }


def evaluate(cases: list[dict]) -> None:
    # 全局计数
    positive_total  = 0   # 期望中/高风险的样本数
    negative_total  = 0   # 期望低风险的样本数
    true_positive   = 0   # 正样本中预测正确
    false_positive  = 0   # 负样本中误报
    true_negative   = 0   # 负样本中预测正确

    # 声明类型级别计数
    claim_expected  = Counter()   # 期望的各类型数量
    claim_hit       = Counter()   # 实际检测到的各类型数量（与期望取交集）

    # 各分类统计
    category_stats: dict[str, dict] = defaultdict(lambda: {"total": 0, "correct": 0})

    print("=" * 60)
    print("  言必有据 · 检测准确性评估")
    print("=" * 60)
    print()

    for case in cases:
        pred = run_case(case)
        label         = case.get("label", case["id"])
        expected_risk = case["expected_overall_risk"]
        expected_claims: list[dict] = case.get("expected_claims", [])

        is_positive     = expected_risk in POSITIVE_LEVELS
        pred_positive   = pred["predicted_risk"] in POSITIVE_LEVELS
        is_correct_risk = (is_positive == pred_positive)

        # 风险等级计数
        if is_positive:
            positive_total += 1
            if pred_positive:
                true_positive += 1
        else:
            negative_total += 1
            if pred_positive:
                false_positive += 1
            else:
                true_negative += 1

        # 声明类型计数
        for exp_claim in expected_claims:
            t = exp_claim["type"]
            claim_expected[t] += 1
            if pred["predicted_claim_types"].get(t, 0) > 0:
                claim_hit[t] += 1

        # 分类统计
        case_type = case.get("label", "未分类").split("（")[0]
        category_stats[case_type]["total"] += 1
        if is_correct_risk:
            category_stats[case_type]["correct"] += 1

        # 单条打印
        status = "✓" if is_correct_risk else "✗"
        print(f"[{status}] {case['id']}  {label}")
        print(f"     期望风险: {expected_risk:<8} 预测风险: {pred['predicted_risk']:<8} 得分: {pred['score']}")
        if expected_claims:
            exp_types = ", ".join(c["type"] for c in expected_claims)
            pred_types = ", ".join(f"{t}×{n}" for t, n in pred["predicted_claim_types"].items()) or "无"
            print(f"     期望声明: {exp_types}")
            print(f"     检测声明: {pred_types}")
        print()

    # ── 汇总指标 ──────────────────────────────────────────
    total          = len(cases)
    recall         = true_positive / positive_total if positive_total else 0.0
    fpr            = false_positive / negative_total if negative_total else 0.0
    precision      = true_positive / (true_positive + false_positive) if (true_positive + false_positive) else 0.0
    f1             = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    overall_acc    = (true_positive + true_negative) / total if total else 0.0

    print("=" * 60)
    print("  汇总指标")
    print("=" * 60)
    print(f"  样本总数          {total}")
    print(f"  正样本（中/高风险）{positive_total}  |  负样本（低风险）{negative_total}")
    print()
    print(f"  整体准确率        {overall_acc:.1%}")
    print(f"  精确率 Precision  {precision:.1%}   （预测为正中真正为正的比例）")
    print(f"  召回率 Recall     {recall:.1%}   （正样本中被成功识别的比例）")
    print(f"  F1 Score          {f1:.1%}")
    print(f"  误报率 FPR        {fpr:.1%}   （负样本中被误判为风险的比例）")

    if sum(claim_expected.values()) > 0:
        print()
        print("  声明类型检测率")
        for t in CLAIM_TYPES:
            exp = claim_expected[t]
            hit = claim_hit[t]
            rate = hit / exp if exp else None
            bar = f"{hit}/{exp}" if exp else "—"
            rate_str = f"  {rate:.1%}" if rate is not None else ""
            print(f"    {t:<12} {bar}{rate_str}")

    if category_stats:
        print()
        print("  各分类正确率")
        for cat, stat in sorted(category_stats.items()):
            r = stat["correct"] / stat["total"]
            print(f"    {cat:<20} {stat['correct']}/{stat['total']}  {r:.1%}")

    print()


def main() -> None:
    cases_path = Path(__file__).resolve().with_name("test_cases.json")
    if not cases_path.exists():
        print(f"[错误] 未找到测试集：{cases_path}")
        print("请先创建 backend/validation/test_cases.json")
        sys.exit(1)

    with cases_path.open("r", encoding="utf-8") as f:
        cases = json.load(f)

    evaluate(cases)


if __name__ == "__main__":
    main()
