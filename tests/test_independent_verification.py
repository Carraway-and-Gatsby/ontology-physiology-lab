"""Independent equations/oracles; numerical regression is NOT biology validation."""
from dataclasses import replace
import importlib.util
from pathlib import Path

import numpy as np
import pint
import pytest

from physiosim.models import cardiovascular as model
from physiosim.simulation import simulate
from physiosim.ontology import cardiovascular_registry, validate_connection, SemanticConnectionError


def oracle():
    path = Path(__file__).resolve().parents[1] / 'docs/evidence/c_verify_run.py'
    assert path.exists(), 'independent numerical evidence generator must exist'
    spec = importlib.util.spec_from_file_location('c_verify_run', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_incidence_oracle_matches_seeded_states_and_rejects_conserving_wrong_topology():
    o = oracle()
    p = model.Parameters()
    np.testing.assert_array_equal(o.INCIDENCE.sum(axis=0), np.zeros(6))
    rng = np.random.default_rng(20261030)
    for _ in range(80):
        v = np.array(p.unstressed_volumes) + rng.uniform(1, 400, 6)
        t = rng.uniform(0, 4*p.period)
        pr, q = o.independent_pressure_flow(t, v, p)
        np.testing.assert_allclose(model.pressures(t, v, p), pr, rtol=2e-14, atol=1e-10)
        np.testing.assert_allclose(model.flows(pr, p), q, rtol=2e-14, atol=1e-9)
        actual = model.rhs(t, v, p)
        np.testing.assert_allclose(actual, o.INCIDENCE @ q, rtol=2e-14, atol=1e-9)
        assert abs(actual.sum()) / max(1, np.abs(q).sum()) < 1e-12
    q = np.arange(1., 7.)
    wrong = o.INCIDENCE.copy()
    wrong[:, [1, 4]] = wrong[:, [4, 1]]
    assert np.all(wrong.sum(axis=0) == 0)  # Conservation alone misses this error.
    with pytest.raises(AssertionError):
        np.testing.assert_allclose(wrong @ q, o.INCIDENCE @ q)
    for mutated in (o.INCIDENCE * 2, -o.INCIDENCE, o.INCIDENCE + np.eye(6)):
        with pytest.raises(AssertionError):
            np.testing.assert_allclose(mutated @ q, o.INCIDENCE @ q)


def test_pint_dimensions_and_real_equation_trajectory_covariance():
    o = oracle()
    u = pint.UnitRegistry()
    pressure, volume, time = 1*u.mmHg, 1*u.mL, 1*u.s
    e, c, r = pressure/volume, volume/pressure, pressure*time/volume
    assert (e*volume).to('Pa').dimensionality == pressure.dimensionality
    assert (volume/c).to('mmHg').magnitude == pytest.approx(1)
    assert (pressure/r).to('mL/s').magnitude == pytest.approx(1)
    assert ((pressure/r)*pressure).to('watt').magnitude > 0
    assert (1*u.mL/u.s).to('L/min').magnitude == pytest.approx(.06)
    with pytest.raises(pint.DimensionalityError):
        (pressure*c).to('mmHg')
    result = o.unit_covariance()
    assert result['equation_max_error_ml_s'] < 1e-8
    assert result['trajectory_max_error_ml'] < 2e-5
    assert result['pressure_max_error_mmhg'] < 2e-5
    assert result['unscaled_parameter_negative_control_error_ml_s'] > 1


def test_passive_equal_pressure_is_fixed_equilibrium():
    p = replace(model.Parameters(), emax_lv=.06, emax_rv=.03)
    compliance = np.array([1/p.emin_lv, p.compliance_sa, p.compliance_sv,
                           1/p.emin_rv, p.compliance_pa, p.compliance_pv])
    v = np.array(p.unstressed_volumes) + 6*compliance
    p = replace(p, initial_volumes=tuple(v))
    np.testing.assert_allclose(model.rhs(.123, v, p), 0, atol=2e-12)
    run = simulate(p, cycles=3, samples_per_cycle=40, rtol=1e-10, atol=1e-11)
    np.testing.assert_allclose(run.volumes, np.broadcast_to(v, run.volumes.shape), rtol=0, atol=1e-9)


@pytest.mark.parametrize('gradient', [-100., -1e-9, 0., 1e-9, 100.])
def test_each_valve_gradient_and_all_resistive_dissipation(gradient):
    o = oracle()
    p = model.Parameters()
    for edge, (src, dst) in enumerate(o.EDGES):
        pressure = np.zeros(6)
        pressure[src] = gradient
        q = model.flows(pressure, p)[edge]
        r = o.resistances(p)[edge]
        expected = max(gradient, 0)/r if edge in (0, 2, 3, 5) else gradient/r
        assert q == pytest.approx(expected, abs=1e-14)
        assert q*gradient >= 0
        if edge in (1, 4):
            assert q*gradient == pytest.approx(gradient**2/r)


def test_determinism_baseline_regression_and_reduced_contractility():
    p = model.Parameters()
    kwargs = dict(cycles=60, samples_per_cycle=400, rtol=1e-9, atol=1e-10, max_step=p.period/200)
    b = simulate(p, **kwargs)
    again = simulate(p, **kwargs)
    np.testing.assert_array_equal(b.volumes, again.volumes)
    np.testing.assert_array_equal(b.flows, again.flows)
    reduced = simulate(replace(p, emax_lv=1.25), **kwargs)
    bm, rm = b.metrics(), reduced.metrics()
    # Rounded internal equation-regression anchors, NOT healthy reference ranges.
    # 0.2% is deliberately looser than observed tight/fine discretization error.
    assert bm['cardiac_output_l_min'] == pytest.approx(7.6993, rel=.002)
    assert bm['systemic_mean_pressure_mmhg'] == pytest.approx(133.50, rel=.002)
    assert bm['lv_esv_ml'] == pytest.approx(75.135, rel=.002)
    assert rm['cardiac_output_l_min'] < bm['cardiac_output_l_min']
    assert rm['lv_esv_ml'] > bm['lv_esv_ml']
    assert rm['pulmonary_venous_mean_pressure_mmhg'] > bm['pulmonary_venous_mean_pressure_mmhg']
    for result in (b, reduced):
        assert np.isfinite(result.volumes).all()
        assert result.volumes.min() > 0
        assert np.max(abs(result.volumes.sum(axis=1)-5000))/5000 < 1e-9
        assert result.metrics()['final_beat_max_volume_difference_ml'] < .1


def test_saved_evidence_refinement_gates_and_independent_metrics():
    import json
    path = Path(__file__).resolve().parents[1] / 'docs/evidence/c_verify_results.json'
    assert path.exists(), 'run c_verify_run.py to produce observed numerical evidence'
    report = json.loads(path.read_text())
    assert len(report['runs']) == 6
    for scenario in ('baseline', 'reduced'):
        comparison = report['comparisons'][scenario]['tight_vs_fine']
        assert comparison['max_metric_relative_error'] < .005
        assert comparison['final_volume_scaled_max_error'] < .01
        assert comparison['final_pressure_scaled_max_error'] < .01
        assert report['repeatability'][scenario]['exact_volume_equality']
    for run in report['runs'].values():
        assert run['global_volume_relative_drift'] < 1e-9
        assert run['independent_metric_max_abs_difference'] < 1e-9
        assert run['solver_success']
        assert run['minimum_stage_volume_ml'] > 0


def test_isolated_passive_reservoir_exact_solution_under_step_refinement():
    evidence = oracle().passive_reservoir_refinement()
    errors = [row['max_volume_error_ml'] for row in evidence]
    assert errors[2] < errors[1] < errors[0]
    assert errors[-1] < 1e-5
    assert all(row['other_compartments_max_change_ml'] < 1e-9 for row in evidence)


def test_semantic_reference_temporal_anatomic_and_unit_negative_controls():
    r = cardiovascular_registry()
    p = r['P_pv']
    assert p.anatomy.local and 'atr' not in p.anatomy.label.lower()
    for altered in (replace(p, anatomy=r['P_lv'].anatomy),
                    replace(p, reference='absolute'), replace(p, temporal_context='mean'),
                    replace(p, unit='mL')):
        with pytest.raises(SemanticConnectionError):
            validate_connection(p, altered)
    for name, endpoints in zip(('aortic', 'systemic', 'tricuspid', 'pulmonary_valve', 'pulmonary', 'mitral'),
                               (('lv', 'sa'), ('sa', 'sv'), ('sv', 'rv'), ('rv', 'pa'), ('pa', 'pv'), ('pv', 'lv'))):
        assert r['Q_'+name].orientation == endpoints
