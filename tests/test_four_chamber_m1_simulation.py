"""Synthetic mathematics and regressions; no physiological target assertions."""
from dataclasses import replace
import numpy as np
import pytest
from scipy.linalg import expm
from physiosim.models import four_chamber_m1 as m
from physiosim.simulation import four_chamber_m1 as s
from test_four_chamber_m1_model import fixture


def run(p=None, cycles=2, samples=80, **controls):
    return s.simulate_m1(p or fixture(), cycles, samples, s.SolverSettings(**controls))


def test_eight_states_named_outputs_metrics_conservation():
    r = run()
    assert r.volumes.shape == r.pressures.shape == r.flows.shape == r.cumulative_flows.shape == (161,8)
    assert r.compartment_names == m.COMPARTMENTS and r.edge_names == m.EDGE_NAMES
    assert r.time[-1] == 2*r.parameters.period
    for i,c in enumerate(m.COMPARTMENTS):
        np.testing.assert_array_equal(r.volume(c), r.volumes[:,i])
        np.testing.assert_array_equal(r.pressure(c), r.pressures[:,i])
    for i,e in enumerate(m.EDGE_NAMES): np.testing.assert_array_equal(r.flow(e), r.flows[:,i])
    for t,v,pr,q in zip(r.time,r.volumes,r.pressures,r.flows):
        np.testing.assert_array_equal(pr,m.pressures(t,v,r.parameters))
        np.testing.assert_array_equal(q,m.edge_flows(pr,r.parameters))
    assert np.min(r.volumes)>0 and np.all(r.flows[:,m.VALVE_INDICES]>=0)
    assert r.conservation()['total_volume_drift_ml'] <= 1e-7
    assert r.conservation()['local_balance_residual_ml'] <= 1e-6
    assert set(r.periodicity()['per_compartment_ml']) == set(m.COMPARTMENTS)
    metrics = r.metrics()
    for c in ['la','ra']:
        for name in ['pressure_min_mmhg','pressure_max_mmhg','pressure_mean_mmhg',
                     'volume_min_ml','volume_max_ml','volume_mean_ml']:
            assert np.isfinite(metrics[c+'_'+name])
    for c,e in [('lv','aortic'),('rv','pulmonary_valve')]:
        sv = r.cumulative_flows[-1,m.EDGE_NAMES.index(e)]-r.cumulative_flows[-81,m.EDGE_NAMES.index(e)]
        assert metrics[c+'_stroke_volume_ml'] == sv
        assert metrics[c+'_cardiac_output_l_min'] == sv/r.parameters.period*60/1000
        assert metrics[c+'_edv_sample_ml'] >= metrics[c+'_esv_sample_ml']
    assert run(cycles=1).periodicity()['per_compartment_ml'] is None
    with pytest.raises(KeyError): r.volume('not_a_compartment')


def test_passive_closed_valve_analytic():
    p = replace(fixture(), heart_rate=120., emax_lv=.06, emax_rv=.03,
        resistance_systemic=10., resistance_venous_return=10.,
        resistance_pulmonary=10., resistance_pulmonary_venous=10.)
    coefficients = np.array([.06,1/1.5,.01,.1,.03,.2,.05,.15])
    pressure = np.array([5.,20.,10.,1.,5.,20.,10.,1.])
    p = replace(p, initial_volumes=tuple(np.array(p.unstressed_volumes)+pressure/coefficients))
    r = run(p,cycles=1, samples=60,rtol=1e-10,atol=1e-10)
    difference = np.zeros((8,8)); difference[np.arange(8),m.SOURCE]=1; difference[np.arange(8),m.TARGET]-=1
    conductance = 1/m.resistances(p); conductance[m.VALVE_INDICES]=0
    matrix = m.INCIDENCE @ np.diag(conductance) @ difference @ np.diag(coefficients)
    expected = np.array([np.array(p.unstressed_volumes)+expm(matrix*t)@(np.array(p.initial_volumes)-p.unstressed_volumes) for t in r.time])
    assert np.max(np.abs(r.volumes-expected))<=1e-6
    assert np.all(r.pressures[:,m.SOURCE[m.VALVE_INDICES]] < r.pressures[:,m.TARGET[m.VALVE_INDICES]])
    np.testing.assert_array_equal(r.cumulative_flows[:,m.VALVE_INDICES],0)


def test_zero_flow_and_simultaneous_symmetry():
    p=fixture(); r=run(replace(p,initial_volumes=p.unstressed_volumes))
    np.testing.assert_array_equal(r.volumes,np.broadcast_to(p.unstressed_volumes,r.volumes.shape))
    np.testing.assert_array_equal(r.flows,0); np.testing.assert_array_equal(r.cumulative_flows,0)
    p=replace(p,emin_lv=.05,emin_rv=.05,emax_lv=1.,emax_rv=1.,
        elastance_la=.1,elastance_ra=.1,compliance_sa=5.,compliance_pa=5.,
        compliance_sv=20.,compliance_pv=20.,resistance_systemic=.1,resistance_pulmonary=.1,
        initial_volumes=(140.,180.,490.,60.,140.,180.,490.,60.),
        unstressed_volumes=(10.,100.,400.,20.,10.,100.,400.,20.))
    r=run(p)
    np.testing.assert_allclose(r.volumes[:,:4],r.volumes[:,4:],rtol=0,atol=1e-7)
    np.testing.assert_allclose(r.cumulative_flows[:,:4],r.cumulative_flows[:,4:],rtol=0,atol=1e-6)


@pytest.mark.parametrize('ventricle,edge', [('lv',0),('rv',4)])
@pytest.mark.parametrize('peak_fraction',[.8,.95,.99])
def test_large_step_pulse(ventricle,edge,peak_fraction):
    p=fixture(); peak=p.emax_lv*130 if ventricle=='lv' else p.emax_rv*200
    ap=peak_fraction*peak
    p=replace(p,resistance_systemic=1000.,resistance_pulmonary=1000.,
        emax_lv=p.emax_lv if ventricle=='lv' else p.emin_lv,
        emax_rv=p.emax_rv if ventricle=='rv' else p.emin_rv,
        initial_volumes=(140.,700+1.5*ap,3000.,60.,210.,100+5*ap,500.,60.))
    ref=run(p,cycles=1,samples=400,max_step=p.period/400)
    large=run(p,cycles=1,samples=400,max_step=p.period)
    assert ref.cumulative_flows[-1,edge]>.1
    np.testing.assert_allclose(large.volumes,ref.volumes,rtol=0,atol=1e-4)
    np.testing.assert_allclose(large.cumulative_flows,ref.cumulative_flows,rtol=0,atol=1e-5)


def test_refinement_methods_sampling_replay():
    p=fixture()
    r=run(p,cycles=3,rtol=1e-9,atol=1e-10,max_step=p.period/200)
    fine=run(p,cycles=3,rtol=1e-11,atol=1e-12,max_step=p.period/400)
    for field in ['volumes','cumulative_flows']:
        np.testing.assert_allclose(getattr(r,field),getattr(fine,field),rtol=0,atol=1e-5)
    dop=run(p,rtol=1e-10,atol=1e-10)
    rad=run(p,rtol=1e-10,atol=1e-10,method='Radau')
    dense=run(p,samples=160,rtol=1e-10,atol=1e-10)
    replay=run(p,rtol=1e-10,atol=1e-10)
    for field in ['time','volumes','cumulative_flows']:
        np.testing.assert_array_equal(getattr(dop,field),getattr(dense,field)[::2])
        np.testing.assert_array_equal(getattr(dop,field),getattr(replay,field))
    for field in ['volumes','cumulative_flows']:
        np.testing.assert_allclose(getattr(dop,field),getattr(rad,field),rtol=0,atol=1e-4)


def test_validation_and_volume_failure(monkeypatch):
    for kwargs in [dict(method='bogus'),dict(rtol=True),dict(atol=-1),dict(max_step=float('inf'))]:
        with pytest.raises(ValueError): s.SolverSettings(**kwargs)
    for args in [dict(cycles=True),dict(cycles=0),dict(samples_per_cycle=3)]:
        with pytest.raises(ValueError): s.simulate_m1(fixture(),**args)
    with pytest.raises(TypeError): s.simulate_m1(None)
    p=fixture(); v=list(p.initial_volumes); v[1]=v[2]=1.
    v0=list(p.unstressed_volumes); v0[1]=10000.
    with pytest.raises(RuntimeError,match='volume'):
        run(replace(p,initial_volumes=v,unstressed_volumes=v0),cycles=1)
    def failed(*a,**kw):
        from types import SimpleNamespace
        return SimpleNamespace(success=False,message='synthetic solver failure')
    monkeypatch.setattr(s,'solve_ivp',failed)
    with pytest.raises(RuntimeError,match='synthetic solver failure'): run()


def test_internal_pressure_path_skips_public_validation_and_matches_scalar(monkeypatch):
    from unittest.mock import Mock
    from physiosim.models.four_chamber_m1 import pressures, edge_flows
    from physiosim.simulation import four_chamber_m1 as simulation

    public = Mock(wraps=pressures)
    monkeypatch.setattr(simulation, 'pressures', public, raising=False)
    from physiosim.experiments.four_chamber_m1_demo import synthetic_fixture
    p = synthetic_fixture()
    result = simulation.simulate_m1(p, cycles=2, samples_per_cycle=50,
        settings=simulation.SolverSettings(max_step=p.period/200))
    assert public.call_count == 0
    expected = np.array([pressures(t, v, p) for t, v in zip(result.time, result.volumes)])
    assert np.array_equal(result.pressures, expected)
    assert np.array_equal(result.flows, np.array([edge_flows(pr, p) for pr in expected]))
    for time, volumes in [(float('nan'), p.initial_volumes), (0., [1.]),
                          (True, p.initial_volumes), (0., [float('inf')]*8)]:
        with pytest.raises(ValueError):
            pressures(time, volumes, p)
