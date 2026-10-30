"""Reproducible independent verification; run with project .venv/bin/python.

Only project code and installed numerical libraries run. No upstream model code.
The public API fixes s/mL/mmHg. Unit covariance tests its raw equations with
consistently transformed numeric parameters; they do NOT imply API unit support.
"""
from dataclasses import asdict, replace
from pathlib import Path
import hashlib
import json
import platform
import sys
import time

import numpy as np
import pint
import scipy
from scipy.integrate import solve_ivp

from physiosim.models import cardiovascular as model
from physiosim.simulation import SimulationResult, simulate
from physiosim.ontology import cardiovascular_registry, validate_connection, SemanticConnectionError

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
# Independently declared anatomical endpoints and explicit incidence matrix.
EDGES = ((0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 0))
INCIDENCE = np.array([[-1, 0, 0, 0, 0, 1], [1, -1, 0, 0, 0, 0],
                      [0, 1, -1, 0, 0, 0], [0, 0, 1, -1, 0, 0],
                      [0, 0, 0, 1, -1, 0], [0, 0, 0, 0, 1, -1]], dtype=float)
SETTINGS = {'default': dict(rtol=1e-7, atol=1e-8, divisor=100),
            'tight': dict(rtol=1e-9, atol=1e-10, divisor=200),
            'fine': dict(rtol=1e-11, atol=1e-12, divisor=400)}


def resistances(p):
    return np.array([p.resistance_aortic, p.resistance_systemic, p.resistance_tricuspid,
                     p.resistance_pulmonary_valve, p.resistance_pulmonary, p.resistance_mitral])


def independent_pressure_flow(t, v, p):
    phase = t/p.period - np.floor(t/p.period)
    a = np.sin(np.pi*phase/p.systolic_fraction)**2 if phase < p.systolic_fraction else 0.
    stiffness = np.array([p.emin_lv+(p.emax_lv-p.emin_lv)*a,
                          1/p.compliance_sa, 1/p.compliance_sv,
                          p.emin_rv+(p.emax_rv-p.emin_rv)*a,
                          1/p.compliance_pa, 1/p.compliance_pv])
    pressure = stiffness*(v-np.array(p.unstressed_volumes))
    q = np.array([(pressure[src]-pressure[dst])/r
                  for (src, dst), r in zip(EDGES, resistances(p))])
    for j in (0, 2, 3, 5):
        if q[j] < 0:
            q[j] = 0
    return pressure, q


def integrate_samples(t, values):
    dt = np.diff(t)
    if values.ndim == 2:
        dt = dt[:, None]
    return np.sum(dt*(values[:-1]+values[1:])/2, axis=0)


def metrics(t, v, pr, q):
    duration = t[-1]-t[0]
    edv, esv = float(max(v[:, 0])), float(min(v[:, 0]))
    sv = float(integrate_samples(t, q[:, 0]))
    return {'stroke_volume_ml': sv, 'cardiac_output_l_min': sv/duration*.06,
            'lv_edv_ml': edv, 'lv_esv_ml': esv, 'lv_ejection_fraction': (edv-esv)/edv,
            'systemic_mean_pressure_mmhg': float(integrate_samples(t, pr[:, 1])/duration),
            'systemic_systolic_pressure_mmhg': float(max(pr[:, 1])),
            'systemic_diastolic_pressure_mmhg': float(min(pr[:, 1])),
            'pulmonary_venous_mean_pressure_mmhg': float(integrate_samples(t, pr[:, 5])/duration),
            'peak_lv_pressure_mmhg': float(max(pr[:, 0]))}


def unit_covariance():
    u = pint.UnitRegistry()
    volume_scale = (1*u.mL).to('L').magnitude
    pressure_scale = (1*u.mmHg).to('Pa').magnitude
    p = model.Parameters()
    changes = {}
    for name, value in asdict(p).items():
        if name.startswith(('emin_', 'emax_')):
            changes[name] = value*pressure_scale/volume_scale
        elif name.startswith('compliance_'):
            changes[name] = value*volume_scale/pressure_scale
        elif name.startswith('resistance_'):
            changes[name] = value*pressure_scale/volume_scale
        elif name in ('initial_volumes', 'unstressed_volumes'):
            changes[name] = tuple(np.array(value)*volume_scale)
    scaled = replace(p, **changes)
    v = np.array(p.initial_volumes)
    eq = np.max(abs(model.rhs(.123, v, p)-model.rhs(.123, v*volume_scale, scaled)/volume_scale))
    kwargs = dict(cycles=3, samples_per_cycle=200, rtol=1e-11, max_step=p.period/400)
    a = simulate(p, atol=1e-12, **kwargs)
    b = simulate(scaled, atol=1e-12*volume_scale, **kwargs)
    # Omit resistance conversion only. Scaling both E and R incorrectly by the
    # same factor can cancel in dV/dt, so a volume-only negative control is weak.
    bad = replace(scaled, **{name: value for name, value in asdict(p).items()
                             if name.startswith('resistance_')})
    return {'volume_units': 'mL -> L', 'pressure_units': 'mmHg -> Pa', 'time_units': 's unchanged',
            'volume_scale': volume_scale, 'pressure_scale': pressure_scale,
            'equation_max_error_ml_s': float(eq),
            'trajectory_max_error_ml': float(np.max(abs(a.volumes-b.volumes/volume_scale))),
            'pressure_max_error_mmhg': float(np.max(abs(a.pressures-b.pressures/pressure_scale))),
            'unscaled_parameter_negative_control_error_ml_s': float(np.max(abs(model.rhs(.123, v, p)-model.rhs(.123, v*volume_scale, bad)/volume_scale)))}


def passive_reservoir_refinement():
    # Keep the other four pressures exactly at the two-reservoir equilibrium.
    # SA approaches it from above, SV from below: both incident valves stay shut.
    p = replace(model.Parameters(), emax_lv=.06, emax_rv=.03)
    c1, c2, r = p.compliance_sa, p.compliance_sv, p.resistance_systemic
    equilibrium = (2*c1+1*c2)/(c1+c2)
    capacities = np.array([1/p.emin_lv, c1, c2, 1/p.emin_rv, p.compliance_pa, p.compliance_pv])
    pressure = np.full(6, equilibrium)
    pressure[1], pressure[2] = 2., 1.
    initial = np.array(p.unstressed_volumes)+capacities*pressure
    p = replace(p, initial_volumes=tuple(initial))
    evidence = []
    for step in (.2, .1, .05):
        run = simulate(p, cycles=10, samples_per_cycle=40, method='RK23',
                       rtol=1e-2, atol=1e-3, max_step=step)
        difference = np.exp(-run.time*(1/c1+1/c2)/r)
        exact_sa = p.unstressed_volumes[1]+c1*(equilibrium+c2/(c1+c2)*difference)
        exact_sv = p.unstressed_volumes[2]+c2*(equilibrium-c1/(c1+c2)*difference)
        error = max(np.max(abs(run.volumes[:, 1]-exact_sa)), np.max(abs(run.volumes[:, 2]-exact_sv)))
        evidence.append({'method': 'RK23', 'max_step_s': step,
                         'max_volume_error_ml': float(error),
                         'other_compartments_max_change_ml': float(np.max(abs(run.volumes[:, [0, 3, 4, 5]]-initial[[0, 3, 4, 5]])))})
    return evidence


def run_case(name, p, setting, cycles=60, samples=400):
    config = SETTINGS[setting]
    stages = {'minimum': float('inf'), 'finite': True}
    def monitored_rhs(t, v):
        stages['minimum'] = min(stages['minimum'], float(np.min(v)))
        stages['finite'] = stages['finite'] and bool(np.isfinite(v).all())
        return model.rhs(t, v, p)
    start = time.perf_counter()
    solution = solve_ivp(monitored_rhs, (0, cycles*p.period), p.initial_volumes,
                         method='DOP853', rtol=config['rtol'], atol=config['atol'],
                         max_step=p.period/config['divisor'], dense_output=True)
    if not solution.success:
        raise RuntimeError(solution.message)
    t = np.linspace(0, cycles*p.period, cycles*samples+1)
    v = solution.sol(t).T
    pr = np.array([model.pressures(ti, vi, p) for ti, vi in zip(t, v)])
    q = np.array([model.flows(pi, p) for pi in pr])
    result = SimulationResult(t, v, pr, q, p, samples)
    sl = slice(-samples-1, None)
    m = metrics(t[sl], v[sl], pr[sl], q[sl])
    original = result.metrics()
    native_pr_q = [independent_pressure_flow(ti, vi, p) for ti, vi in zip(solution.t, solution.y.T)]
    native_pr = np.array([x[0] for x in native_pr_q])
    native_q = np.array([x[1] for x in native_pr_q])
    native_balance = solution.y[:, -1]-solution.y[:, 0]-INCIDENCE @ integrate_samples(solution.t, native_q)
    residuals = []
    for beat in range(2, cycles+1):
        current = v[(beat-1)*samples:beat*samples+1]
        previous = v[(beat-2)*samples:(beat-1)*samples+1]
        residuals.append(float(np.max(abs(current-previous))))
    first_strict = next((j+4 for j in range(len(residuals)-2)
                         if max(residuals[j:j+3]) <= 1e-4), None)
    integrated = integrate_samples(t[sl], q[sl])
    final_balance = v[-1]-v[-samples-1]-INCIDENCE @ integrated
    # Output-grid refinement uses the SAME continuous numerical solution.
    sample_study = {}
    for density in (400, 800, 1600):
        ts = np.linspace((cycles-1)*p.period, cycles*p.period, density+1)
        vs = solution.sol(ts).T
        pqs = [independent_pressure_flow(ti, vi, p) for ti, vi in zip(ts, vs)]
        prs, qs = np.array([x[0] for x in pqs]), np.array([x[1] for x in pqs])
        sample_study[str(density)] = metrics(ts, vs, prs, qs)
    file = OUT / f'c_verify_{name}_{setting}.npz'
    np.savez_compressed(file, time=t, volumes=v, pressures=pr, flows=q,
                        native_time=solution.t, native_volumes=solution.y.T,
                        native_pressures=native_pr, native_flows=native_q,
                        beat_residuals=np.array(residuals))
    # Read the saved arrays, not the live SimulationResult, for independent metrics.
    with np.load(file) as saved:
        saved_metrics = metrics(saved['time'][sl], saved['volumes'][sl], saved['pressures'][sl], saved['flows'][sl])
    config_record = dict(parameters=asdict(p), cycles=cycles, samples_per_cycle=samples,
                         method='DOP853', rtol=config['rtol'], atol=config['atol'], max_step=p.period/config['divisor'])
    record = {'configuration': config_record,
              'configuration_sha256': hashlib.sha256(json.dumps(config_record, sort_keys=True).encode()).hexdigest(),
              'artifact': str(file.relative_to(ROOT)), 'metrics': m,
              'solver_success': bool(solution.success), 'nfev': solution.nfev,
              'native_accepted_steps': len(solution.t)-1,
              'min_native_step_s': float(min(np.diff(solution.t))),
              'max_native_step_s': float(max(np.diff(solution.t))),
              'runtime_seconds': time.perf_counter()-start,
              'minimum_stage_volume_ml': stages['minimum'], 'all_stages_finite': stages['finite'],
              'global_volume_relative_drift': float(np.max(abs(v.sum(axis=1)-sum(p.initial_volumes)))/sum(p.initial_volumes)),
              'native_global_volume_drift_ml': float(np.max(abs(solution.y.sum(axis=0)-sum(p.initial_volumes)))),
              'native_integrated_balance_max_error_ml': float(np.max(abs(native_balance))),
              'final_beat_integrated_balance_max_error_ml': float(np.max(abs(final_balance))),
              'final_beat_integrated_edge_flows_ml': integrated.tolist(),
              'final_beat_inlet_outlet_overlap_samples': int(np.sum((q[sl, 0]>0) & (q[sl, 5]>0))),
              'flow_sv_minus_volume_excursion_ml': m['stroke_volume_ml']-(m['lv_edv_ml']-m['lv_esv_ml']),
              'final_three_beat_residuals_ml': residuals[-3:],
              'milestone_periodicity_pass': residuals[-1] < .1,
              'strict_final_three_periodicity_pass': max(residuals[-3:]) <= 1e-4,
              'first_three_successive_strict_pass_ending_beat': first_strict,
              'independent_metric_max_abs_difference': max(abs(saved_metrics[k]-original[k]) for k in saved_metrics if k in original),
              'sampling_refinement': sample_study}
    return result, record


def compare(a, b):
    n = a.samples_per_cycle
    errors = {}
    for key, av in metrics(a.time[-n-1:], a.volumes[-n-1:], a.pressures[-n-1:], a.flows[-n-1:]).items():
        bv = metrics(b.time[-n-1:], b.volumes[-n-1:], b.pressures[-n-1:], b.flows[-n-1:])[key]
        floor = .01 if 'fraction' in key else (.1 if 'output' in key else 1.)
        errors[key] = {'absolute': abs(av-bv), 'relative_with_floor': abs(av-bv)/max(abs(bv), floor)}
    diff = abs(a.volumes-b.volumes)
    index = np.unravel_index(np.argmax(diff), diff.shape)
    # Per-compartment max absolute fine waveform magnitude, floored at 1 unit.
    volume_scale = np.maximum(np.max(abs(b.volumes[-n-1:]), axis=0), 1.)
    pressure_scale = np.maximum(np.max(abs(b.pressures[-n-1:]), axis=0), 1.)
    return {'metric_errors': errors, 'max_metric_relative_error': max(x['relative_with_floor'] for x in errors.values()),
            'full_volume_max_error_ml': float(diff.max()),
            'full_volume_error_location': {'time_s': float(a.time[index[0]]), 'compartment': model.COMPARTMENTS[index[1]]},
            'final_volume_max_error_ml': float(np.max(diff[-n-1:])),
            'final_pressure_max_error_mmhg': float(np.max(abs(a.pressures[-n-1:]-b.pressures[-n-1:]))),
            'final_volume_scaled_max_error': float(np.max(diff[-n-1:]/volume_scale)),
            'final_pressure_scaled_max_error': float(np.max(abs(a.pressures[-n-1:]-b.pressures[-n-1:])/pressure_scale))}


def semantic_probes():
    r = cardiovascular_registry()
    p = r['P_lv']
    cases = {'wrong_anatomy': (p, r['P_rv']),
             'wrong_reference': (p, replace(p, reference='absolute')),
             'wrong_temporal': (p, replace(p, temporal_context='mean')),
             'wrong_unit': (p, replace(p, unit='mL')),
             'missing_both_references': (replace(p, reference=''), replace(p, reference='')),
             'missing_both_anatomy_iris': (replace(p, anatomy=replace(p.anatomy, uri='')), replace(p, anatomy=replace(p.anatomy, uri=''))),
             'changed_equation_only': (p, replace(p, equation='P = V*C')),
             'changed_source_context_only': (p, replace(p, source_context='unrelated incompatible model'))}
    decisions = {}
    for name, (a, b) in cases.items():
        try:
            validate_connection(a, b)
            decisions[name] = {'decision': 'accepted'}
        except SemanticConnectionError as exc:
            decisions[name] = {'decision': 'rejected', 'reason': str(exc)}
    return {'decisions': decisions, 'sv_annotation': asdict(r['SV']),
            'note': 'Connection equivalence checker is not a registry completeness or equation-equivalence validator.'}


def main():
    p = model.Parameters()
    report = {'scope': 'independent implementation verification, NOT external biological validation',
              'versions': {'python': sys.version, 'numpy': np.__version__, 'scipy': scipy.__version__,
                           'pint': pint.__version__, 'platform': platform.platform()},
              'seed': 20261030, 'state_order': list(model.COMPARTMENTS),
              'flow_order': list(model.FLOW_NAMES), 'runs': {}, 'comparisons': {}, 'repeatability': {},
              'unit_covariance': unit_covariance(), 'semantic_probes': semantic_probes(),
              'passive_reservoir_refinement': passive_reservoir_refinement()}
    for scenario, parameters in (('baseline', p), ('reduced', replace(p, emax_lv=1.25))):
        runs = {}
        for setting in SETTINGS:
            run, record = run_case(scenario, parameters, setting)
            runs[setting] = run
            report['runs'][scenario+'_'+setting] = record
            print(scenario, setting, json.dumps({'CO': record['metrics']['cardiac_output_l_min'],
                                                 'last_three': record['final_three_beat_residuals_ml']}), flush=True)
        report['comparisons'][scenario] = {'default_vs_tight': compare(runs['default'], runs['tight']),
                                            'tight_vs_fine': compare(runs['tight'], runs['fine'])}
        # Exercise actual public API independently of native-step generator route.
        replay = simulate(parameters, cycles=60, samples_per_cycle=400, rtol=1e-9, atol=1e-10, max_step=p.period/200)
        report['repeatability'][scenario] = {'exact_volume_equality': bool(np.array_equal(replay.volumes, runs['tight'].volumes)),
                                             'exact_pressure_equality': bool(np.array_equal(replay.pressures, runs['tight'].pressures)),
                                             'exact_flow_equality': bool(np.array_equal(replay.flows, runs['tight'].flows))}
    report['source_sha256'] = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                               for path in [ROOT/'src/physiosim/models/cardiovascular.py',
                                            ROOT/'src/physiosim/simulation/__init__.py',
                                            ROOT/'src/physiosim/ontology/__init__.py', Path(__file__),
                                            ROOT/'tests/test_independent_verification.py']}
    (OUT/'c_verify_results.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print('Saved', OUT/'c_verify_results.json', flush=True)


if __name__ == '__main__':
    main()
