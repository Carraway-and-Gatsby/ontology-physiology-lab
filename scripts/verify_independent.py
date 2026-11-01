"""Re-execute the independently authored review, preserving historical evidence."""
import importlib.util
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / 'docs/evidence/c_verify_run.py'
spec = importlib.util.spec_from_file_location('independent_review', path)
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)
review.OUT = root / 'results/independent'
review.OUT.mkdir(parents=True, exist_ok=True)
review.main()
report = json.loads((review.OUT / 'c_verify_results.json').read_text())
assert len(report['runs']) == 6
for scenario in ('baseline', 'reduced'):
    assert report['comparisons'][scenario]['tight_vs_fine']['max_metric_relative_error'] < .005
    assert all(report['repeatability'][scenario].values())
    # Preserve the existing independent-refinement bounds for the additional
    # cross-integrator comparison; exact equality still gates repeatability.
    comparison = report['public_api_vs_native_fine'][scenario]
    assert comparison['max_metric_relative_error'] < .005
    assert comparison['final_volume_scaled_max_error'] < .01
    assert comparison['final_pressure_scaled_max_error'] < .01
for case in ('missing_both_references', 'missing_both_anatomy_iris'):
    assert report['semantic_probes']['decisions'][case]['decision'] == 'rejected'
print('PASS: independent numerical comparisons reproduced; paired missing semantic fields rejected.')
