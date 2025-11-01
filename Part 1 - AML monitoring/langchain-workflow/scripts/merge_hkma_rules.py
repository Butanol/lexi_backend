"""Merge HKMA rule JSON files in logs/ into a single deduplicated file.

Behavior:
- Reads all files matching curr_HKMA_rules*.json in the logs directory,
  sorted by filename.
- Keeps the `regulation_summary` from the first file.
- Merges `actionable_rules` arrays, deduplicating by rule content (ignoring
  `rule_id`). If a `rule_id` conflicts with an already-used id, the script
  assigns a new id in the form `HKMA-R-###`.
- Writes output to `logs/merged_HKMA_rules.json` and prints a short summary.
"""
from pathlib import Path
import json
import re


def _find_key(d: dict, candidates):
    for c in candidates:
        if c in d:
            return c
    # case-insensitive fallback
    lower_map = {k.lower(): k for k in d.keys()}
    for c in candidates:
        if c.lower() in lower_map:
            return lower_map[c.lower()]
    return None


def normalize_rule_for_key(rule: dict) -> str:
    # remove any key that looks like a rule id (common variants) before
    # canonicalizing. We remove keys that contain both 'rule' and 'id' in
    # their lowercase form, or exact matches.
    r = {}
    for k, v in rule.items():
        kl = k.lower()
        if ("rule" in kl and "id" in kl) or kl in ("ruleid", "rule_id", "id"):
            continue
        r[k] = v
    return json.dumps(r, sort_keys=True, ensure_ascii=False).strip().lower()


def main():
    base = Path(__file__).resolve().parents[1]
    logs = base / "logs"
    files = sorted(logs.glob("curr_HKMA_rules*.json"))
    if not files:
        print("No HKMA rule files found in", logs)
        return

    merged = {}
    merged_rules = []
    seen_keys = set()
    used_ids = set()
    new_id_counter = 1

    first = True
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"Skipping {f.name}: failed to read JSON: {e}")
            continue

        if first:
            summary_key = _find_key(data, ["regulation_summary", "regulationsummary", "regulationSummary"])
            merged["regulation_summary"] = data.get(summary_key, "") if summary_key else ""
            first = False

        rules_key = _find_key(data, ["actionable_rules", "actionablerules", "actionableRules"])
        for rule in (data.get(rules_key, []) if rules_key else []):
            key = normalize_rule_for_key(rule)
            if key in seen_keys:
                continue
            seen_keys.add(key)

            id_key = _find_key(rule, ["rule_id", "ruleid", "ruleId", "id"]) if isinstance(rule, dict) else None
            rid = rule.get(id_key) if id_key else (rule.get("rule_id") if isinstance(rule, dict) else "") or ""
            # normalize existing id (remove illegal chars)
            rid_norm = re.sub(r"[^A-Za-z0-9\-]", "", str(rid))
            if rid_norm and rid_norm not in used_ids:
                rule["rule_id"] = rid_norm
                used_ids.add(rid_norm)
            else:
                # assign a new sequential HKMA-R-### id
                while True:
                    candidate = f"HKMA-R-{new_id_counter:03d}"
                    new_id_counter += 1
                    if candidate not in used_ids:
                        break
                rule["rule_id"] = candidate
                used_ids.add(candidate)

            merged_rules.append(rule)

    merged["actionable_rules"] = merged_rules

    out = logs / "merged_HKMA_rules.json"
    out.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Merged {len(files)} files -> {out}")
    print(f"Total actionable_rules: {len(merged_rules)}")


if __name__ == "__main__":
    main()
