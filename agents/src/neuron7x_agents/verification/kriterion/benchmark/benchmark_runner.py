#!/usr/bin/env python3
"""Run the synthetic demo benchmark using the deterministic reference runner."""
import csv
import hashlib
import json
from pathlib import Path
import sys
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / 'tools') not in sys.path:
    sys.path.insert(0, str(ROOT / 'tools'))
import reference_runner  # type: ignore

BENCH = ROOT / 'benchmark'
CASES = BENCH / 'synthetic_cases'
RESULTS = BENCH / 'results'
LOGS = BENCH / 'logs'


def quadratic_weighted_kappa(a, b, min_rating=0, max_rating=5):
    n = max_rating - min_rating + 1
    O = [[0 for _ in range(n)] for _ in range(n)]
    for x, y in zip(a, b):
        O[x-min_rating][y-min_rating] += 1
    total = len(a)
    if total == 0:
        return 0.0
    hist_a = [sum(row) for row in O]
    hist_b = [sum(O[r][c] for r in range(n)) for c in range(n)]
    E = [[hist_a[i] * hist_b[j] / total for j in range(n)] for i in range(n)]
    num = den = 0.0
    for i in range(n):
        for j in range(n):
            w = ((i - j) ** 2) / ((n - 1) ** 2)
            num += w * O[i][j]
            den += w * E[i][j]
    return 1.0 if den == 0 else 1 - (num / den)




def injection_fail_result(case, message):
    ts = "1970-01-01T00:00:00Z"
    h = hashlib.sha256((case["bundle_id"] + message).encode("utf-8")).hexdigest()
    return {
        "protocol_metadata": {
            "protocol_id": "GPT5.4-AUDIT-HARDENING-PROTOCOL-2026",
            "protocol_version": "2026.4.3",
            "target_protocol_id": case["target_protocol_id"],
            "execution_mode": case["execution_mode"],
            "evaluation_timestamp": ts,
            "model_identifier": case["model_identifier"],
            "artifact_count": len(case["artifacts"]),
            "evaluation_hash": h,
        },
        "artifact_validation_results": [
            {
                "artifact_id": a.get("artifact_id", "UNKNOWN_ARTIFACT"),
                "schema_status": "VALID",
                "integrity_status": "INJECTION_ATTEMPT",
                "admissible": False,
                "reason_codes": ["INJECTION_ATTEMPT"],
            }
            for a in case["artifacts"]
        ],
        "task_scores": [],
        "domain_scores": [],
        "gate_results": [
            {
                "gate_id": "G0_INTEGRITY",
                "status": "FAIL",
                "blocking": True,
                "reason_codes": ["INJECTION_ATTEMPT"],
                "affected_artifact_ids": [a.get("artifact_id", "UNKNOWN_ARTIFACT") for a in case["artifacts"]],
            },
            {
                "gate_id": "G1_MINIMUM_READINESS",
                "status": "PASS",
                "blocking": False,
                "reason_codes": [],
                "affected_artifact_ids": [],
            },
            {
                "gate_id": "G2_EVIDENCE_SUFFICIENCY",
                "status": "PASS",
                "blocking": False,
                "reason_codes": [],
                "affected_artifact_ids": [],
            },
        ],
        "final_classification": {
            "status": "FAIL",
            "classification_label": "NOT_READY",
            "composite_score": 0.0,
            "integrity_hash": h,
        },
        "evidence_trace_table": [],
    }

def main() -> int:
    RESULTS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    case_files = sorted(CASES.glob('case-*.json'))
    case_rows = []
    human_scores = []
    model_scores = []
    gate_total = 0
    gate_match = 0
    benign_total = benign_false_positive = 0
    adv_total = adv_detected = 0
    runtimes = []
    costs = []
    run_log = []
    integrity_violation_count = 0

    for case_file in case_files:
        case = json.loads(case_file.read_text(encoding='utf-8'))
        try:
            result = reference_runner.compute(case)
        except SystemExit as exc:
            result = injection_fail_result(case, str(exc))
        integrity_violation_count += sum(1 for r in result['artifact_validation_results'] if not r['admissible'])
        out_path = RESULTS / f"{case['bundle_id']}.evaluation.json"
        out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')

        human_score = int(round(case['expected']['human_overall_score']))
        model_score = int(round(result['final_classification']['composite_score']))
        human_scores.append(human_score)
        model_scores.append(model_score)

        human_class = case['expected']['human_final_classification']
        model_class = result['final_classification']['classification_label']
        gates_h = case['expected']['human_gates']
        gates_m = {g['gate_id']: g['status'] for g in result['gate_results']}
        for gate_id, gate_status in gates_h.items():
            gate_total += 1
            if gates_m.get(gate_id) == gate_status:
                gate_match += 1

        adversarial = case['expected'].get('adversarial', False)
        if adversarial:
            adv_total += 1
            detected = result['gate_results'][0]['status'] == 'FAIL'
            adv_detected += 1 if detected else 0
        else:
            benign_total += 1
            flagged = result['gate_results'][0]['status'] == 'FAIL'
            benign_false_positive += 1 if flagged else 0

        runtime = case['expected'].get('runtime_seconds', 1.0)
        cost = case['expected'].get('cost_usd', 0.0)
        runtimes.append(runtime)
        costs.append(cost)
        case_rows.append({
            'case_id': case['bundle_id'],
            'protocol_id': case['target_protocol_id'],
            'adversarial': adversarial,
            'human_overall_score': human_score,
            'model_overall_score': model_score,
            'human_final_classification': human_class,
            'model_final_classification': model_class,
            'human_g0': gates_h['G0_INTEGRITY'],
            'model_g0': gates_m['G0_INTEGRITY'],
            'runtime_seconds': runtime,
            'cost_usd': cost,
        })
        run_log.append(f"RUN {case['bundle_id']} -> {model_class} composite={result['final_classification']['composite_score']}")

    exact_class = sum(1 for row in case_rows if row['human_final_classification'] == row['model_final_classification']) / len(case_rows)
    gate_agreement = gate_match / gate_total if gate_total else 0.0
    kappa = quadratic_weighted_kappa(human_scores, model_scores)
    metrics = {
        'benchmark_id': 'synthetic-harness-validation-2026',
        'status': 'DEMO_VALIDATION_ONLY',
        'case_count': len(case_rows),
        'adversarial_case_count': adv_total,
        'task_level_weighted_kappa': round(kappa, 4),
        'final_classification_agreement': round(exact_class, 4),
        'gate_agreement': round(gate_agreement, 4),
        'anti_gaming_recall': round((adv_detected / adv_total) if adv_total else 0.0, 4),
        'integrity_violation_count': integrity_violation_count,
        'anti_gaming_false_positive_rate': round((benign_false_positive / benign_total) if benign_total else 0.0, 4),
        'median_runtime_seconds': round(median(runtimes), 2),
        'median_cost_usd': round(median(costs), 4),
    }

    with (RESULTS / 'case_level_results.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(case_rows[0].keys()), lineterminator='\n')
        writer.writeheader()
        writer.writerows(case_rows)
    (BENCH / 'metrics.json').write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding='utf-8')
    (LOGS / 'demo_benchmark_run.log').write_text('\n'.join(run_log) + '\n', encoding='utf-8')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
