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

    for case_file in case_files:
        case = json.loads(case_file.read_text(encoding='utf-8'))
        result = reference_runner.compute(case)
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
        'anti_gaming_false_positive_rate': round((benign_false_positive / benign_total) if benign_total else 0.0, 4),
        'median_runtime_seconds': round(median(runtimes), 2),
        'median_cost_usd': round(median(costs), 4),
    }

    with (RESULTS / 'case_level_results.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(case_rows[0].keys()))
        writer.writeheader()
        writer.writerows(case_rows)
    (BENCH / 'metrics.json').write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding='utf-8')
    (LOGS / 'demo_benchmark_run.log').write_text('\n'.join(run_log) + '\n', encoding='utf-8')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
