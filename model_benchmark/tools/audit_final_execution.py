"""Independent preflight and postflight for the final evaluation (no inference)."""
import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import torch
from sklearn import metrics as sk

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import final_evaluate_11class_large as ev
from benchmark_common import load_locked_inputs, validate_campaign_lock, sha256_file

def dump(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def check_metrics(y, p, reported, classes):
    pred = p.argmax(1)
    labels = list(range(len(classes)))
    expected = {
        'accuracy': sk.accuracy_score(y, pred),
        'balanced_accuracy': sk.balanced_accuracy_score(y, pred),
        'macro_precision': sk.precision_score(y, pred, labels=labels, average='macro', zero_division=0),
        'macro_recall': sk.recall_score(y, pred, labels=labels, average='macro', zero_division=0),
        'macro_f1': sk.f1_score(y, pred, labels=labels, average='macro', zero_division=0),
        'negative_log_likelihood': sk.log_loss(y, p, labels=labels),
    }
    for key, value in expected.items():
        assert np.isclose(reported[key], value, atol=2e-6), (key, reported[key], value)
    assert np.array_equal(reported['confusion_matrix'], sk.confusion_matrix(y, pred, labels=labels))
    return expected

def preflight():
    inputs = load_locked_inputs(ev.CONTRACT)
    lock = validate_campaign_lock(inputs, ev.CAMPAIGN_LOCK)
    data = ev.validate_data_locks(lock)
    checkpoints, valrows = ev.validate_runs(inputs, sha256_file(ev.CAMPAIGN_LOCK))
    assert sha256_file(ev.SELECTION_MANIFEST) == data['dataset_lock']['selection_manifest_sha256']
    rows = ev.read_csv(inputs.manifest_path)
    filelock = {r['relative_path']: r for r in data['dataset_lock']['files']}
    assert len(rows) == len(filelock) == 21216
    actual = {p.relative_to(inputs.dataset_root).as_posix() for p in inputs.dataset_root.rglob('*') if p.is_file()}
    assert actual == set(filelock) == {r['relative_path'] for r in rows}
    for i, row in enumerate(rows, 1):
        p = inputs.dataset_root / row['relative_path']
        assert p.resolve().is_relative_to(inputs.dataset_root.resolve())
        digest = sha256_file(p)
        assert digest == row['sha256'] == filelock[row['relative_path']]['sha256'], str(p)
        assert p.stat().st_size == filelock[row['relative_path']]['bytes']
        if i % 3000 == 0:
            print(f'FULL DATASET SHA: {i}/21216', flush=True)
    for (model, seed), path in checkpoints.items():
        cp = torch.load(path, map_location='cpu', weights_only=False)
        assert cp['model_id'] == model and cp['training_seed'] == seed
        assert cp['class_names'] == list(inputs.canonical_classes)
        assert cp['contract_sha256'] == inputs.contract_sha256
        assert cp['split_manifest_sha256'] == inputs.manifest_sha256
        run = ev.read_json(path.parent / 'run_manifest.json')
        assert cp['global_epoch'] == run['best_global_epoch']
        assert abs(cp['validation_metrics']['macro_f1'] - run['best_validation_macro_f1']) < 1e-12
    rng = np.random.default_rng(431)
    y = np.tile(np.arange(11), 10)
    p = rng.dirichlet(np.ones(11), len(y))
    check_metrics(y, p, ev.detailed_metrics(y, p, inputs.canonical_classes, 55), inputs.canonical_classes)
    from scipy.stats import binomtest
    for b, c in [(0,0),(0,4),(13,21),(300,400)]:
        expected = binomtest(b, b+c, .5).pvalue if b+c else 1.
        assert np.isclose(ev.exact_mcnemar_p(b,c), expected, atol=1e-12)
    leak = ev.leakage_audit()
    result = {'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'status':'passed',
        'all_dataset_files_verified':21216, 'checkpoint_metadata_verified':len(checkpoints),
        'metric_crosscheck':'sklearn and scipy on synthetic data', 'leakage_audit':leak,
        'validation_ranking':ev.validation_ranking(inputs, valrows),
        'evaluation_code_sha256':{name:sha256_file(ROOT/'src'/name) for name in ['final_evaluate_11class_large.py','compare_final_11class_large_v2.py']},
        'limitations':['pHash grouping is not verified field/plant/session grouping.',
        'Three-seed SD is distinct from test-image sampling uncertainty.',
        'Image bootstrap and randomization assume independent/exchangeable sampling units; clustering may invalidate this assumption.',
        'Primary result is per-seed metrics and their arithmetic mean; probability ensemble is supplemental.',
        'High accuracy alone is neither proof of leakage nor proof of real-world validity.']}
    dump(ROOT/'runs'/'final_preflight_11class_large.json', result)
    print(json.dumps({k:v for k,v in result.items() if k not in ['evaluation_code_sha256']}, ensure_ascii=True), flush=True)

def postflight():
    out = ev.OUTPUT_ROOT
    summary = ev.read_json(out/'final_summary.json')
    assert summary['status'] == 'complete'
    classes = tuple(summary['provenance']['canonical_classes'])
    checked = []
    for setname, setsummary in summary['results'].items():
        expected_rows = ev.read_csv(ev.EXTERNAL_MANIFEST) if setname == 'external_source_test' else [r for r in ev.read_csv(ev.load_locked_inputs(ev.CONTRACT).manifest_path) if r['split']=='test']
        expected = {r.get('locked_relative_path',r.get('relative_path')): r['label'] for r in expected_rows}
        for path in sorted((out/setname).rglob('predictions.csv')):
            rows = ev.read_csv(path)
            assert len(rows) == len(expected) == len({r['relative_path'] for r in rows})
            for row in rows:
                assert expected[row['relative_path']] == row['true_label'] == classes[int(row['true_index'])]
            y = np.array([int(r['true_index']) for r in rows])
            p = np.array([[float(r['probability_'+c]) for c in classes] for r in rows])
            assert np.isfinite(p).all() and (p>=0).all() and np.allclose(p.sum(1), 1, atol=1e-6)
            assert np.array_equal(p.argmax(1), [int(r['predicted_index']) for r in rows])
            m = ev.read_json(path.parent/'metrics.json')
            independent = check_metrics(y,p,m,classes)
            checked.append({'path':str(path.relative_to(out)), 'count':len(y), 'sha256':sha256_file(path), 'independent_metrics':independent})
        for model, agg in setsummary['aggregate_across_training_seeds'].items():
            for metric, values in agg.items():
                vals = [ev.read_json(out/setname/model/f'seed_{s}'/'metrics.json')[metric] for s in (42,123,2026)]
                assert np.isclose(np.mean(vals),values['mean']) and np.isclose(np.std(vals,ddof=1),values['sample_std'])
    assert len(checked)==38
    dump(out/'independent_verification.json', {'status':'passed','prediction_tables_checked':len(checked),'checks':checked})
    lines = ['# Final evaluation — 11 classes', '', 'Primary summary: arithmetic mean and sample SD over three fixed training seeds. Metrics below are percentages; SD is in percentage points.', '', '| Model | Validation F1 | Internal test F1 | External test F1 | External accuracy |','|---|---:|---:|---:|---:|']
    ranking = ev.read_json(out/'evaluation_lock.json')['validation_ranking']
    for r in ranking:
        model=r['model_id']; a=summary['results']['internal_grouped_test']['aggregate_across_training_seeds'][model]; b=summary['results']['external_source_test']['aggregate_across_training_seeds'][model]
        fmt=lambda v:f"{100*v['mean']:.3f} ± {100*v['sample_std']:.3f}"
        lines.append(f"| {model} | {100*r['validation_macro_f1_mean']:.3f} | {fmt(a['macro_f1'])} | {fmt(b['macro_f1'])} | {fmt(b['accuracy'])} |")
    lines += ['', 'Validation-selected architecture: '+summary['selected_model'], '', 'Internal test: 3,185 images. External test: 1,100 images, 100/class. All 38 prediction tables independently cross-checked against scikit-learn; row labels, probabilities, confusion matrices and aggregates verified.', '', 'Limitations: pHash groups are not verified plant/field/session IDs. Confidence intervals assume independent images within each class and may be too narrow for correlated photos. External sources and labels have not all been independently expert-verified. Test scores cannot be used to revise model selection. Ensemble metrics are supplemental, not single-model results. Bootstrap intervals are marginal; only Holm-adjusted p-values control the specified family of tests.']
    (out/'RESULTS_REVIEW.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines), flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('stage',choices=['pre','post']); args=parser.parse_args()
    preflight() if args.stage=='pre' else postflight()
