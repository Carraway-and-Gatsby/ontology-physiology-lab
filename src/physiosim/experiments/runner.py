"""Reproducible, audited Phase 1 experiments. All scenarios are experimental."""
from dataclasses import asdict, replace
import hashlib
from html import escape
from importlib.metadata import version
import json
from pathlib import Path
import platform
import sys

import numpy as np

from physiosim.models import Parameters, COMPARTMENTS, FLOW_NAMES
from physiosim.simulation import simulate
from physiosim.interventions import ParameterChange
from physiosim.ontology import cardiovascular_registry, export_graph, UnitConversion
from physiosim.ontology.bindings import connect_value
from physiosim.validation import audit_closed_loop
from physiosim.visualization import plot_comparison
from physiosim.experiments.semantic_benchmark import run_benchmark

DEFAULT_CONFIG = dict(cycles=60, samples_per_cycle=400, rtol=1e-9, atol=1e-10,
                      max_step_fraction=.005, periodicity_tolerance_ml=.1)


def _json_write(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def run_experiment(output, config=None):
    settings = DEFAULT_CONFIG | ({} if config is None else config)
    unknown = set(settings) - set(DEFAULT_CONFIG)
    if unknown:
        raise ValueError(f'Unknown configuration keys: {sorted(unknown)}')
    for key in ('max_step_fraction', 'periodicity_tolerance_ml'):
        if not np.isfinite(settings[key]) or settings[key] <= 0:
            raise ValueError(f'{key} must be finite and positive')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    base = Parameters()
    impairment = ParameterChange('Reduced LV contractility', 'emax_lv', .5,
                                 'Maximum LV systolic elastance',
                                 'Exploratory isolated contractility impairment; not a clinical heart-failure diagnosis')
    impaired, impaired_record = impairment.apply(base, time_s=0)
    restore = ParameterChange('Partial contractility restoration', 'emax_lv', 1.5,
                              'Maximum LV systolic elastance',
                              'Illustrative increase relative to impaired parameter; independent run, not a timed drug treatment')
    restored, restored_record = restore.apply(impaired, time_s=0)
    scenarios = [('baseline', base, []), ('reduced_contractility', impaired, [impaired_record]),
                 ('partial_contractility_restoration', restored, [impaired_record, restored_record])]
    results, summaries = {}, {}
    registry = cardiovascular_registry()
    target_co = replace(registry['CO'], name='report_CO', unit='L/min')
    for name, p, events in scenarios:
        result = simulate(p, cycles=settings['cycles'], samples_per_cycle=settings['samples_per_cycle'],
                          rtol=settings['rtol'], atol=settings['atol'],
                          max_step=p.period * settings['max_step_fraction'], method='DOP853')
        audit = audit_closed_loop(result.time, result.volumes, result.flows, valve_columns=[0, 2, 3, 5])
        metrics = result.metrics()
        residual = metrics['final_beat_max_volume_difference_ml']
        periodic = bool(np.isfinite(residual) and residual <= settings['periodicity_tolerance_ml'])
        # JSON null means unavailable, never a fabricated convergence result.
        metrics = {k: v if np.isfinite(v) else None for k, v in metrics.items()}
        connected_co = connect_value(result, 'CO', target_co, conversion=UnitConversion('mL/s', 'L/min'))
        summaries[name] = dict(parameters=asdict(p), changes=events, metrics=metrics, audit=audit,
                               connected_CO_l_min=connected_co,
                               status='periodic_within_declared_gate' if periodic else 'transient_not_periodic')
        columns = ['time_s'] + ['V_' + k + '_ml' for k in COMPARTMENTS] + ['P_' + k + '_mmhg' for k in COMPARTMENTS] + ['Q_' + k + '_ml_s' for k in FLOW_NAMES]
        data = np.column_stack((result.time, result.volumes, result.pressures, result.flows))
        np.savetxt(output / (name + '.csv'), data, delimiter=',', header=','.join(columns), comments='', fmt='%.17g')
        results[name] = result
    summary = {'experimental': True, 'clinical_validity': 'not established',
               'baseline_interpretation': 'Exploratory elevated-pressure reference; not a normal healthy adult',
               'scenario_design': 'Independent runs from identical initial volumes; changes applied at simulation time zero',
               'config': settings, 'solver': 'DOP853',
               'all_periodic': all(s['status'] == 'periodic_within_declared_gate' for s in summaries.values()),
               'periodicity_definition': 'maximum absolute six-volume difference between last two sampled beat waveforms',
               'scenarios': summaries, 'annotated_variable_count': len(registry)}
    _json_write(output / 'summary.json', summary)
    _json_write(output / 'semantic_benchmark.json', run_benchmark(results['baseline']))
    _json_write(output / 'variables.json', {k: asdict(v) for k, v in registry.items()})
    (output / 'annotations.trig').write_text(export_graph(registry))
    plot_comparison(results, output)
    rows = ''.join('<tr><td>' + escape(name) + '</td><td>' + f"{s['metrics']['cardiac_output_l_min']:.4f}" + '</td><td>' + f"{s['metrics']['stroke_volume_ml']:.3f}" + '</td><td>' + escape(s['status']) + '</td></tr>' for name, s in summaries.items())
    annotations = ''.join('<tr>' + ''.join('<td>' + escape(str(x)) + '</td>' for x in (v.name, v.anatomy.label, v.property.label, v.unit, v.equation)) + '</tr>' for v in registry.values())
    html = '''<!doctype html><html lang="en"><meta charset="utf-8"><title>Experimental cardiovascular simulation</title>
<style>body{font:16px system-ui;max-width:1200px;margin:30px auto;padding:20px}img{width:100%}td,th{border:1px solid #ccc;padding:6px}table{border-collapse:collapse}pre{white-space:pre-wrap}.warning{background:#fff0ce;padding:16px}</style>
<h1>EXPERIMENTAL cardiovascular simulation</h1><p class="warning">Research and education only. No clinical validity established. All numerical defaults are exploratory. Baseline has elevated pressure and is not a healthy reference. Independent parameter scenarios are not a timed treatment-response simulation.</p>
<table><tr><th>Scenario</th><th>CO (L/min)</th><th>Forward SV (mL)</th><th>Periodicity</th></tr>''' + rows + '''</table>
<img src="comparison.png" alt="Computed final-cycle pressure, flow, volume and pressure-volume plots">
<img src="transients.png" alt="Computed initialization transients and beatwise cardiac output">
<h2>Model assumptions and limits</h2><p>Six compartments; synchronous prescribed elastance; linear vascular compliance; four ideal diode valves; fixed external pressure zero. No atria, baroreflex, renal regulation, septal interaction, respiration or drug pharmacokinetics. Pulmonary venous pressure is a reservoir variable, not measured left-atrial pressure. Metadata checks cannot detect falsely labeled numerical data.</p>
<h2>Actual parameters, solver settings and mechanism changes</h2><pre>''' + escape(json.dumps(summary, indent=2)) + '''</pre>
<h2>Selected biological annotations and equations</h2><p>External concept labels are source-verified; aggregate compartments and several quantities are explicitly local extensions. Project relations are not imported ontology entailments.</p><table><tr><th>Variable</th><th>Anatomy</th><th>Property</th><th>Unit</th><th>Equation</th></tr>''' + annotations + '</table></html>'
    (output / 'index.html').write_text(html)
    source_root = Path(__file__).resolve().parents[1]
    code_hashes = {str(p.relative_to(source_root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(source_root.rglob('*.py'))}
    output_names = ['summary.json', 'semantic_benchmark.json', 'variables.json', 'annotations.trig',
                    'comparison.png', 'transients.png', 'index.html'] + [name + '.csv' for name in results]
    manifest = {'python': sys.version, 'platform': platform.platform(),
                'dependencies': {name: version(name) for name in ('numpy', 'scipy', 'matplotlib', 'rdflib', 'pint')},
                'source_sha256': code_hashes,
                'config_sha256': hashlib.sha256(json.dumps(settings, sort_keys=True).encode()).hexdigest(),
                'output_sha256': {name: hashlib.sha256((output / name).read_bytes()).hexdigest() for name in output_names}}
    _json_write(output / 'manifest.json', manifest)
    return summary
