"""Incremental tests of the exploratory cardiovascular model, not clinical validation."""
from dataclasses import replace
import importlib
import importlib.util

import numpy as np
import pytest


def test_elastance_and_pressure_constitutive_laws():
    try:
        spec = importlib.util.find_spec("physiosim.models.cardiovascular")
    except ModuleNotFoundError:
        spec = None
    assert spec is not None, "cardiovascular model must exist"
    model = importlib.import_module("physiosim.models.cardiovascular")
    p = model.Parameters()
    assert p.period == pytest.approx(60.0 / p.heart_rate)
    assert model.elastance(0.0, p) == pytest.approx((p.emin_lv, p.emin_rv))
    peak = p.period * p.systolic_fraction / 2.0
    assert model.elastance(peak, p) == pytest.approx((p.emax_lv, p.emax_rv))
    assert model.elastance(peak + 3 * p.period, p) == pytest.approx(model.elastance(peak, p))
    v = np.array(p.unstressed_volumes) + np.array([100, 150, 700, 100, 80, 90])
    assert model.pressures(0.0, v, p) == pytest.approx([6, 100, 7, 3, 16, 4.5])
    assert model.COMPARTMENTS == ("lv", "sa", "sv", "rv", "pa", "pv")


def test_four_valves_are_diodes_and_two_vascular_beds_are_resistors():
    from physiosim.models import cardiovascular as model
    assert hasattr(model, "flows"), "flow constitutive law must exist"
    p = model.Parameters()
    pressure = np.array([120., 100., 5., 25., 15., 8.])
    expected = np.array([2000., 95., 0., 1000., 70., 0.])
    assert model.flows(pressure, p) == pytest.approx(expected)
    reverse = model.flows(-pressure, p)
    assert reverse[[0, 2, 3, 5]] == pytest.approx([0., 2000., 0., 11200.])
    assert reverse[[1, 4]] == pytest.approx([-95., -70.])
    assert model.FLOW_NAMES == (
        "aortic", "systemic", "tricuspid", "pulmonary_valve", "pulmonary", "mitral"
    )


def test_rhs_is_closed_loop_mass_balance_for_all_six_compartments():
    from physiosim.models import cardiovascular as model
    assert hasattr(model, "rhs"), "mass-balance ODE must exist"
    p = model.Parameters()
    for t in np.linspace(0, 2 * p.period, 13):
        for scale in (0.8, 1.0, 1.2):
            v = np.asarray(p.initial_volumes) * scale
            q = model.flows(model.pressures(t, v, p), p)
            dv = model.rhs(t, v, p)
            assert dv == pytest.approx(np.roll(q, 1) - q)
            assert np.sum(dv) == pytest.approx(0., abs=1e-10)


def test_simulation_returns_conserved_stable_six_compartment_trajectory():
    try:
        spec = importlib.util.find_spec("physiosim.simulation")
    except ModuleNotFoundError:
        spec = None
    assert spec is not None, "simulation API must exist"
    simulation = importlib.import_module("physiosim.simulation")
    from physiosim.models.cardiovascular import Parameters
    p = Parameters()
    result = simulation.simulate(parameters=p, cycles=40, samples_per_cycle=200)
    assert result.parameters == p
    assert result.time.shape == (8001,)
    assert result.time[-1] == pytest.approx(40 * p.period)
    for values in (result.volumes, result.pressures, result.flows):
        assert values.shape == (8001, 6)
        assert np.isfinite(values).all()
    assert np.min(result.volumes) > 0
    assert np.min(result.flows[:, [0, 2, 3, 5]]) >= 0
    assert result.volumes.sum(axis=1) == pytest.approx(sum(p.initial_volumes), abs=1e-7)
    assert np.max(np.abs(result.volumes[-201:] - result.volumes[-401:-200])) < 0.1
    assert result.compartment_names == ("lv", "sa", "sv", "rv", "pa", "pv")
    assert result.flow_names[0] == "aortic"


def test_metrics_integrate_only_last_full_beat_with_explicit_units():
    from physiosim.models.cardiovascular import Parameters
    from physiosim.simulation import SimulationResult
    assert hasattr(SimulationResult, "metrics"), "summary metrics must exist"
    p = Parameters(heart_rate=60.)
    time = np.linspace(0, 2, 9)
    volumes = np.tile([100., 850., 3200., 140., 180., 530.], (9, 1))
    volumes[-5:, 0] = [100., 80., 60., 80., 100.]
    volumes[-5:, 5] += [0., 20., 40., 20., 0.]
    pressure = np.tile([5., 90., 5., 5., 15., 8.], (9, 1))
    flow = np.full((9, 6), 80.)
    flow[:4] = 999.
    result = SimulationResult(time, volumes, pressure, flow, p, 4)
    metrics = result.metrics()
    assert result.final_beat == slice(-5, None)
    assert metrics["heart_rate_bpm"] == 60.
    assert metrics["stroke_volume_ml"] == pytest.approx(80.)
    assert metrics["cardiac_output_l_min"] == pytest.approx(4.8)
    assert metrics["cardiac_output_m3_s"] == pytest.approx(80e-6)
    assert metrics["lv_edv_ml"] == 100.
    assert metrics["lv_esv_ml"] == 60.
    assert metrics["lv_ejection_fraction"] == pytest.approx(0.4)
    assert metrics["systemic_mean_pressure_mmhg"] == pytest.approx(90.)
    assert metrics["systemic_systolic_pressure_mmhg"] == 90.
    assert metrics["systemic_diastolic_pressure_mmhg"] == 90.
    assert metrics["pulmonary_mean_pressure_mmhg"] == 15.
    assert metrics["pulmonary_venous_mean_pressure_mmhg"] == 8.
    assert metrics["volume_drift_ml"] == 0.
    assert metrics["final_beat_max_volume_difference_ml"] == 40.


@pytest.mark.parametrize("changes", [
    {"heart_rate": 0.}, {"heart_rate": float("nan")},
    {"emax_lv": 0.01}, {"emax_rv": 0.001},
    {"compliance_sv": -1.}, {"resistance_mitral": 0.},
    {"systolic_fraction": 1.}, {"systolic_fraction": 0.},
    {"initial_volumes": (100.,)},
    {"initial_volumes": (0., 1., 1., 1., 1., 1.)},
    {"unstressed_volumes": (-1., 1., 1., 1., 1., 1.)},
])
def test_invalid_parameters_are_rejected(changes):
    from physiosim.models.cardiovascular import Parameters
    with pytest.raises(ValueError):
        replace(Parameters(), **changes)


@pytest.mark.parametrize("options", [
    {"cycles": True}, {"samples_per_cycle": 3}, {"rtol": 0.},
    {"atol": 0.}, {"max_step": float("inf")},
])
def test_invalid_solver_controls_are_rejected(options):
    from physiosim.simulation import simulate
    with pytest.raises(ValueError):
        simulate(**({"cycles": 1, "samples_per_cycle": 8} | options))


def test_reduced_lv_contractility_is_a_dataclass_replacement_with_model_response():
    from physiosim.models.cardiovascular import Parameters
    from physiosim.simulation import simulate
    p = Parameters()
    baseline = simulate(p, cycles=40, samples_per_cycle=400)
    reduced = simulate(replace(p, emax_lv=0.5 * p.emax_lv), cycles=40, samples_per_cycle=400)
    b, r = baseline.metrics(), reduced.metrics()
    assert p.emax_lv == 2.5
    assert 2. < b["cardiac_output_l_min"] < 9.
    assert 50. < b["systemic_mean_pressure_mmhg"] < 150.
    assert r["cardiac_output_l_min"] < b["cardiac_output_l_min"]
    assert r["lv_esv_ml"] > b["lv_esv_ml"]
    assert r["pulmonary_venous_mean_pressure_mmhg"] > b["pulmonary_venous_mean_pressure_mmhg"]
    assert r["final_beat_max_volume_difference_ml"] < 0.1
    assert r["volume_drift_ml"] < 1e-7


def test_tight_tolerances_and_independent_solver_agree():
    from physiosim.simulation import simulate
    reference = simulate(cycles=4, samples_per_cycle=200, rtol=1e-9, atol=1e-10, max_step=0.004)
    alternate = simulate(cycles=4, samples_per_cycle=200, rtol=1e-8, atol=1e-9, max_step=0.004, method="Radau")
    assert alternate.volumes == pytest.approx(reference.volumes, abs=0.002)
    assert alternate.metrics()["stroke_volume_ml"] == pytest.approx(reference.metrics()["stroke_volume_ml"], rel=1e-4)


def test_single_beat_reports_unavailable_convergence_as_nan():
    from physiosim.simulation import simulate
    result = simulate(cycles=1, samples_per_cycle=20)
    assert np.isnan(result.metrics()["final_beat_max_volume_difference_ml"])


def test_models_package_exports_the_public_parameter_type_and_names():
    import physiosim.models as models
    from physiosim.models.cardiovascular import Parameters, COMPARTMENTS, FLOW_NAMES
    assert getattr(models, "Parameters", None) is Parameters
    assert models.COMPARTMENTS == COMPARTMENTS
    assert models.FLOW_NAMES == FLOW_NAMES

