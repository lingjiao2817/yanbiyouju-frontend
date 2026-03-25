import json
from pathlib import Path


DEFAULT_RULES = {
    "version": "sample-v1",
    "fake_authors": [],
    "fake_journals": [],
    "fake_publishers": [],
    "suspicious_doi_patterns": [],
    "suspicious_phrases": [],
    "suspicious_keywords": [],
}


def load_rules() -> dict:
    rules_dir = Path(__file__).resolve().parents[1] / "rules"
    primary_path = rules_dir / "rules.json"
    sample_path = rules_dir / "rules.sample.json"

    rule_path = primary_path if primary_path.exists() else sample_path
    loaded_from_sample = rule_path == sample_path

    if not rule_path.exists():
        return normalize_rules(DEFAULT_RULES, "built-in-default", True)

    with rule_path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    return normalize_rules(payload, rule_path.name, loaded_from_sample)


def normalize_rules(payload: dict, source_file: str, loaded_from_sample: bool) -> dict:
    rules = dict(DEFAULT_RULES)
    rules.update({key: value for key, value in payload.items() if key in rules or key == "version"})

    normalized = {"version": str(rules.get("version") or "sample-v1")}
    for field in (
        "fake_authors",
        "fake_journals",
        "fake_publishers",
        "suspicious_doi_patterns",
        "suspicious_phrases",
        "suspicious_keywords",
    ):
        values = rules.get(field) or []
        normalized[field] = [str(item).strip() for item in values if str(item).strip()]

    normalized["__meta"] = {
        "source_file": source_file,
        "loaded_from_sample": loaded_from_sample,
        "version": normalized["version"],
        "rule_counts": {
            "fake_authors": len(normalized["fake_authors"]),
            "fake_journals": len(normalized["fake_journals"]),
            "fake_publishers": len(normalized["fake_publishers"]),
            "suspicious_doi_patterns": len(normalized["suspicious_doi_patterns"]),
            "suspicious_phrases": len(normalized["suspicious_phrases"]),
            "suspicious_keywords": len(normalized["suspicious_keywords"]),
        },
    }
    return normalized
