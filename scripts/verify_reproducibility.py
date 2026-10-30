"""Run the installed wheel twice and verify numerical artifacts exactly.

Usage: .clean-venv/bin/python scripts/verify_reproducibility.py
Run from the repository root after installing the wheel into a fresh environment.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
outputs = [root / 'results/phase1', root / 'results/replay']
logs = []
for output in outputs:
    command = [sys.executable, '-I', '-m', 'physiosim', '--config', str(root / 'experiments/phase1.json'), '--output', str(output)]
    run = subprocess.run(command, cwd=root, capture_output=True, text=True)
    logs.append({'command': command, 'exit_code': run.returncode, 'stdout': run.stdout, 'stderr': run.stderr})
    print(run.stdout, end='')
    if run.returncode:
        raise SystemExit(f'Experiment failed with code {run.returncode}: {run.stderr}')
comparisons = {}
for path in sorted(outputs[0].glob('*.csv')):
    left, right = path.read_bytes(), (outputs[1] / path.name).read_bytes()
    comparisons[path.name] = {'identical_bytes': left == right, 'sha256': hashlib.sha256(left).hexdigest()}
    if left != right:
        raise AssertionError(f'Nonidentical numerical trajectory: {path.name}')
summary_equal = json.loads((outputs[0] / 'summary.json').read_text()) == json.loads((outputs[1] / 'summary.json').read_text())
assert summary_equal
import physiosim
assert 'site-packages' in str(Path(physiosim.__file__).resolve()), 'Expected installed wheel, not editable source'
report = {'python': sys.version, 'imported_package': physiosim.__file__, 'runs': logs,
          'csv_comparisons': comparisons, 'summary_equal': summary_equal,
          'scope': 'Same-host, same-dependency installed-wheel deterministic replay; not cross-platform bitwise reproducibility'}
path = root / 'results/reproducibility.json'
path.write_text(json.dumps(report, indent=2) + '\n')
print(f'PASS: {len(comparisons)} numerical CSVs identical; summary identical. Evidence: {path}')
