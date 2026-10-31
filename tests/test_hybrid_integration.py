"""Portability and hybrid-event regressions; original acceptance bounds unchanged."""
from dataclasses import replace
import math

import numpy as np
import pytest

from physiosim.models import cardiovascular as model
from physiosim.simulation import simulate


def _dot_with_reduction(original, reduction):
    def dot(a, b, out=None):
        a, b = np.asarray(a), np.asarray(b)
        if (a.dtype != np.float64 or b.dtype != np.float64 or a.ndim not in (1, 2)
                or b.ndim not in (1, 2) or a.shape[-1] != b.shape[0]):
            return original(a, b, out=out)

        def contract(left, right):
            products = [float(x)*float(y) for x, y in zip(left, right)]
            if reduction == 'fsum':
                return math.fsum(products)
            result = 0.0
            for product in products:
                result += product
            return result

        if a.ndim == b.ndim == 1:
            value = np.float64(contract(a, b))
        elif b.ndim == 1:
            value = np.array([contract(row, b) for row in a])
        elif a.ndim == 1:
            value = np.array([contract(a, col) for col in b.T])
        else:
            value = np.array([[contract(row, col) for col in b.T] for row in a])
        if out is not None:
            out[...] = value
            return out
        return value
    return dot


@pytest.mark.parametrize('reduction', ['native', 'fsum', 'serial'])
def test_volume_agreement_survives_equivalent_dot_reductions(
    reduction, monkeypatch, record_testsuite_property,
):
    if reduction != 'native':
        monkeypatch.setattr(np, 'dot', _dot_with_reduction(np.dot, reduction))
    p = model.Parameters()
    settings = dict(parameters=p, cycles=4, samples_per_cycle=200,
                    rtol=1e-9, atol=1e-10, max_step=p.period/200)
    plain = simulate(**settings)
    augmented = simulate(**settings, cumulative_flows=True)
    error = float(np.max(np.abs(augmented.volumes-plain.volumes)))
    record_testsuite_property('volume_error_ml.'+reduction, error)
    np.testing.assert_allclose(augmented.volumes, plain.volumes, rtol=0, atol=1e-4)
    assert augmented.local_balance_residual_ml() <= 1e-6


@pytest.mark.parametrize('activation', ['native', 'cos2'])
def test_stroke_refinement_survives_equivalent_activation(
    activation, monkeypatch, record_testsuite_property,
):
    def equivalent(time, p):
        phase = (time % p.period) / p.period
        activation = 1-math.cos(math.pi*phase/p.systolic_fraction)**2 if phase < p.systolic_fraction else 0.0
        return (p.emin_lv+(p.emax_lv-p.emin_lv)*activation,
                p.emin_rv+(p.emax_rv-p.emin_rv)*activation)
    if activation == 'cos2':
        monkeypatch.setattr(model, 'elastance', equivalent)
    p = model.Parameters()
    common = dict(parameters=p, cycles=40, samples_per_cycle=400, cumulative_flows=True)
    tight = simulate(**common, rtol=1e-9, atol=1e-10, max_step=p.period/200)
    fine = simulate(**common, rtol=1e-11, atol=1e-12, max_step=p.period/400)
    first = tight.cumulative_metrics()['stroke_volume_cumulative_ml']
    second = fine.cumulative_metrics()['stroke_volume_cumulative_ml']
    record_testsuite_property(activation+'_stroke_error_ml', abs(first-second))
    record_testsuite_property(activation+'_tight_stroke_ml', first)
    record_testsuite_property(activation+'_fine_stroke_ml', second)
    assert first == pytest.approx(second, rel=0, abs=1e-5)


def test_zero_flow_equilibrium_does_not_chatter():
    p = model.Parameters()
    p = replace(p, initial_volumes=p.unstressed_volumes)
    result = simulate(p, cycles=2, samples_per_cycle=40, cumulative_flows=True)
    np.testing.assert_array_equal(result.volumes, np.broadcast_to(p.initial_volumes, result.volumes.shape))
    np.testing.assert_array_equal(result.flows, 0)
    np.testing.assert_array_equal(result.cumulative_flows, 0)


def test_simultaneous_valve_transitions_preserve_symmetric_circuits():
    p = model.Parameters(
        emin_lv=0.05, emin_rv=0.05, emax_lv=1.0, emax_rv=1.0,
        compliance_sa=5.0, compliance_pa=5.0, compliance_sv=20.0, compliance_pv=20.0,
        resistance_systemic=0.1, resistance_pulmonary=0.1,
        initial_volumes=(140., 180., 490., 140., 180., 490.),
        unstressed_volumes=(10., 100., 400., 10., 100., 400.),
    )
    result = simulate(p, cycles=2, samples_per_cycle=100, rtol=1e-9, atol=1e-10,
                      cumulative_flows=True)
    np.testing.assert_allclose(result.volumes[:, :3], result.volumes[:, 3:], rtol=0, atol=1e-7)
    np.testing.assert_allclose(result.cumulative_flows[:, :3], result.cumulative_flows[:, 3:], rtol=0, atol=1e-6)


def test_output_sampling_does_not_change_the_trajectory():
    settings = dict(cycles=2, rtol=1e-9, atol=1e-10, cumulative_flows=True)
    coarse = simulate(**settings, samples_per_cycle=40)
    dense = simulate(**settings, samples_per_cycle=80)
    np.testing.assert_array_equal(coarse.time, dense.time[::2])
    np.testing.assert_array_equal(coarse.volumes, dense.volumes[::2])
    np.testing.assert_array_equal(coarse.cumulative_flows, dense.cumulative_flows[::2])
