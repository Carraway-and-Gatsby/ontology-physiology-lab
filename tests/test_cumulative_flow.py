"""Tests for opt-in solver-integrated cumulative edge flows."""

import numpy as np
import pytest

from physiosim.models.cardiovascular import Parameters
from physiosim.simulation import SimulationResult, simulate


def test_cumulative_flows_default_is_disabled_and_unchanged():
    implicit = simulate(cycles=2, samples_per_cycle=40)
    explicit = simulate(cycles=2, samples_per_cycle=40, cumulative_flows=False)

    assert implicit.cumulative_flows is None
    assert explicit.cumulative_flows is None
    np.testing.assert_array_equal(implicit.time, explicit.time)
    np.testing.assert_array_equal(implicit.volumes, explicit.volumes)
    np.testing.assert_array_equal(implicit.pressures, explicit.pressures)
    np.testing.assert_array_equal(implicit.flows, explicit.flows)
    assert implicit.metrics() == explicit.metrics()


@pytest.mark.parametrize("value", [0, 1, None, "true", np.bool_(True)])
def test_cumulative_flows_requires_a_real_bool(value):
    with pytest.raises(ValueError, match="cumulative_flows must be a bool"):
        simulate(cycles=1, samples_per_cycle=4, cumulative_flows=value)


def test_augmented_volume_trajectory_agrees_with_six_state_run():
    p = Parameters()
    settings = dict(
        parameters=p, cycles=4, samples_per_cycle=200,
        rtol=1e-9, atol=1e-10, max_step=p.period / 200,
    )
    plain = simulate(**settings)
    augmented = simulate(**settings, cumulative_flows=True)

    # Including six growing C states in adaptive (RMS-norm) error control changes
    # accepted steps. Measured (4 cycles): |augmented - plain| = 2.29e-5 mL,
    # |plain - fine reference| = 6.2e-6 mL, |augmented - fine| = 2.34e-5 mL.
    # The bound is ~4x the measured difference so a defect cannot hide in it.
    np.testing.assert_allclose(augmented.volumes, plain.volumes, rtol=0.0, atol=1e-4)


def test_local_balance_uses_independent_literal_incidence_oracle():
    p = Parameters()
    result = simulate(
        p, cycles=20, samples_per_cycle=200, rtol=1e-9, atol=1e-10,
        max_step=p.period / 200, cumulative_flows=True,
    )
    # Rows: lv, sa, sv, rv, pa, pv. Columns: aortic, systemic,
    # tricuspid, pulmonary_valve, pulmonary, mitral. +1 in, -1 out.
    incidence = np.array([
        [-1,  0,  0,  0,  0, +1],
        [+1, -1,  0,  0,  0,  0],
        [ 0, +1, -1,  0,  0,  0],
        [ 0,  0, +1, -1,  0,  0],
        [ 0,  0,  0, +1, -1,  0],
        [ 0,  0,  0,  0, +1, -1],
    ], dtype=float)
    volume_change = result.volumes - result.volumes[0]
    oracle_residual = volume_change - result.cumulative_flows @ incidence.T

    assert np.max(np.abs(oracle_residual)) <= 1e-6
    assert result.local_balance_residual_ml() <= 1e-6

    wrong = incidence.copy()
    wrong[:, [0, 1]] = wrong[:, [1, 0]]
    wrong_residual = volume_change - result.cumulative_flows @ wrong.T
    assert np.max(np.abs(wrong_residual)) > 1.0


def test_cumulative_methods_require_augmented_result():
    result = simulate(cycles=1, samples_per_cycle=4)
    with pytest.raises(ValueError, match="cumulative flows are unavailable"):
        result.local_balance_residual_ml()
    with pytest.raises(ValueError, match="cumulative flows are unavailable"):
        result.cumulative_metrics()

    # The new last field keeps all historical positional construction valid.
    positional = SimulationResult(
        result.time, result.volumes, result.pressures, result.flows,
        result.parameters, result.samples_per_cycle,
    )
    assert positional.cumulative_flows is None


def test_valve_cumulative_flows_are_monotone():
    p = Parameters()
    # Fine error control suppresses dense-interpolant undershoot on intervals
    # where an ideal-diode flow is exactly zero.
    result = simulate(
        p, cycles=4, samples_per_cycle=200, rtol=1e-11, atol=1e-12,
        max_step=p.period / 400, cumulative_flows=True,
    )
    assert np.min(np.diff(result.cumulative_flows[:, [0, 2, 3, 5]], axis=0)) >= -1e-9


def test_cumulative_stroke_volume_converges_under_tolerance_refinement():
    p = Parameters()
    common = dict(parameters=p, cycles=40, samples_per_cycle=400, cumulative_flows=True)
    tight = simulate(
        **common, rtol=1e-9, atol=1e-10, max_step=p.period / 200,
    )
    fine = simulate(
        **common, rtol=1e-11, atol=1e-12, max_step=p.period / 400,
    )
    # Measured difference 1.29e-6 mL. The bound (~8x measured) is below the
    # 1600-samples/beat trapezoid error (~1.0e-3 mL), so post-hoc quadrature
    # could not satisfy it.
    assert tight.cumulative_metrics()["stroke_volume_cumulative_ml"] == pytest.approx(
        fine.cumulative_metrics()["stroke_volume_cumulative_ml"], rel=0, abs=1e-5,
    )


def test_cumulative_stroke_volume_improves_on_sampled_quadrature():
    p = Parameters()
    settings = dict(
        parameters=p, cycles=40, rtol=1e-9, atol=1e-10,
        max_step=p.period / 200,
    )
    cumulative = simulate(**settings, samples_per_cycle=400, cumulative_flows=True)
    sampled_400 = simulate(**settings, samples_per_cycle=400)
    sampled_1600 = simulate(**settings, samples_per_cycle=1600)
    sv_cumulative = cumulative.cumulative_metrics()["stroke_volume_cumulative_ml"]
    sv_400 = sampled_400.metrics()["stroke_volume_ml"]
    sv_1600 = sampled_1600.metrics()["stroke_volume_ml"]

    assert sv_cumulative == pytest.approx(sv_400, rel=0.002)
    assert abs(sv_cumulative - sv_1600) < abs(sv_cumulative - sv_400)


def test_final_beat_edge_throughputs_follow_periodicity_residual():
    p = Parameters()
    result = simulate(
        p, cycles=40, samples_per_cycle=400, rtol=1e-9, atol=1e-10,
        max_step=p.period / 200, cumulative_flows=True,
    )
    metrics = result.cumulative_metrics()
    throughput = np.array([
        metrics[f"final_beat_net_throughput_{name}_ml"]
        for name in result.flow_names
    ])
    beat_volume_change = result.volumes[-1] - result.volumes[-401]

    # Adjacent throughput differences equal the corresponding compartment's
    # beat volume change. Around the ring, the range is bounded by the sum of
    # those periodicity residuals (plus roundoff). This follows from the same
    # linear invariant as the balance test: a consistency check, not
    # independent evidence of cumulative-flow accuracy.
    tolerance = float(np.sum(np.abs(beat_volume_change)) + 1e-8)
    assert np.ptp(throughput) <= tolerance
