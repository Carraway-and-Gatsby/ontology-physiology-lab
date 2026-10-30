import importlib.util


def test_fault_injection_benchmark_counts_failures_honestly():
    assert importlib.util.find_spec('physiosim.experiments') is not None, 'Missing reproducible experiments'
    from physiosim.experiments.semantic_benchmark import run_benchmark
    report = run_benchmark()
    rows = report['fixtures']
    assert len(rows) == report['fixture_count']
    assert len(rows) >= 10
    by_id = {r['id']: r for r in rows}
    assert by_id['wrong_anatomy']['manual'] is True
    assert by_id['wrong_anatomy']['units_only'] is True
    assert by_id['wrong_anatomy']['semantic'] is False
    assert by_id['explicit_conversion']['semantic'] is True
    # Deliberately dishonest metadata is beyond a metadata-only validator.
    assert by_id['misannotated_payload']['truth'] is False
    assert by_id['misannotated_payload']['semantic'] is True
    assert report['counts']['semantic']['false_accept'] == 1
    assert report['human_integration_effort'] == 'not measured'


def test_cli_executes_real_scenarios_exports_and_flags_transients(tmp_path):
    import importlib.util
    import json
    import subprocess
    import sys
    import csv
    import hashlib
    from pathlib import Path
    assert importlib.util.find_spec('physiosim.cli') is not None, 'Missing executable CLI'
    config = {
        'cycles': 2, 'samples_per_cycle': 40, 'rtol': 1e-9, 'atol': 1e-10,
        'max_step_fraction': 0.005, 'periodicity_tolerance_ml': 0.1,
    }
    config_path = tmp_path / 'config.json'
    config_path.write_text(json.dumps(config))
    output = tmp_path / 'results'
    completed = subprocess.run([sys.executable, '-m', 'physiosim', '--config', str(config_path),
                                '--output', str(output)], capture_output=True, text=True)
    assert completed.returncode == 2, completed.stdout + completed.stderr
    report = json.loads((output / 'summary.json').read_text())
    assert report['experimental'] is True
    assert report['all_periodic'] is False
    assert set(report['scenarios']) == {'baseline', 'reduced_contractility', 'partial_contractility_restoration'}
    for name, scenario in report['scenarios'].items():
        assert scenario['metrics']['volume_drift_ml'] < 1e-6
        assert scenario['status'] == 'transient_not_periodic'
        with (output / (name + '.csv')).open() as stream:
            rows = list(csv.DictReader(stream))
        assert len(rows) == config['cycles'] * config['samples_per_cycle'] + 1
        assert 'P_sa_mmhg' in rows[0]
        import pytest
        # mL/s -> L/min round trip permits floating-point rounding only.
        assert scenario['connected_CO_l_min'] == pytest.approx(scenario['metrics']['cardiac_output_l_min'], rel=1e-14)
    b = report['scenarios']['baseline']
    d = report['scenarios']['reduced_contractility']
    assert b['parameters']['emax_lv'] != d['parameters']['emax_lv']
    assert b['metrics']['cardiac_output_l_min'] != d['metrics']['cardiac_output_l_min']
    assert (output / 'comparison.png').read_bytes()[:8] == b'\x89PNG\r\n\x1a\n'
    assert (output / 'transients.png').read_bytes()[:8] == b'\x89PNG\r\n\x1a\n'
    assert 'EXPERIMENTAL' in (output / 'index.html').read_text()
    assert (output / 'annotations.trig').stat().st_size > 0
    benchmark = json.loads((output / 'semantic_benchmark.json').read_text())
    assert benchmark['payload_evidence']['mislabeled_pressure_max_error_mmhg'] > 0
    assert benchmark['payload_evidence']['validator_accepted'] is True
    manifest = json.loads((output / 'manifest.json').read_text())
    for name, digest in manifest['output_sha256'].items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == digest
