import math

import numpy as np
import pytest

N_STATES = 6


def base_waveform(n, seed=0):
    return np.random.default_rng(seed).uniform(50., 150., size=(n, N_STATES))


def periodic_volumes(cycles, n):
    i = np.arange(cycles * n + 1)
    return base_waveform(n)[i % n]


def decaying_volumes(cycles, n, a, r):
    # Offset a * r**(sample/n) makes beat j differ from beat j-1 by a*r**(j-1)*(1-r) at phase 0.
    i = np.arange(cycles * n + 1)
    return base_waveform(n)[i % n] + (a * r ** (i / n))[:, None]


def test_exactly_periodic_signal_has_zero_residuals():
    from physiosim.validation import periodicity_report
    report = periodicity_report(periodic_volumes(6, 20), 20)
    assert report['available'] is True
    assert report['passed'] is True
    assert report['monotone_nonincreasing'] is True
    assert len(report['residuals_ml']) == 3
    assert all(abs(x) <= 1e-12 for x in report['residuals_ml'])
    assert report['max_residual_ml'] <= 1e-12


@pytest.mark.parametrize('r', [0.5, 0.8, 2.0])
def test_geometric_transient_matches_analytical_residuals(r):
    from physiosim.validation import periodicity_report
    a, cycles, n = 0.5, 6, 20
    report = periodicity_report(decaying_volumes(cycles, n, a, r), n)
    # Difference at phase p is a*r**(j-1+p/n)*(r-1); the maximum is at the start phase if r<1, the end phase if r>1.
    expected = [a * max(r ** (j - 1), r ** j) * abs(1 - r) for j in (3, 4, 5)]
    assert report['residuals_ml'] == pytest.approx(expected, abs=1e-12)
    assert report['max_residual_ml'] == pytest.approx(max(expected), abs=1e-12)
    assert report['monotone_nonincreasing'] is (r < 1)


def test_pass_fail_decision_follows_tolerance_between_residuals():
    from physiosim.validation import periodicity_report
    volumes = decaying_volumes(6, 20, 0.5, 0.5)
    first = periodicity_report(volumes, 20)['residuals_ml'][0]
    second = periodicity_report(volumes, 20)['residuals_ml'][1]
    between = 0.5 * (first + second)
    assert periodicity_report(volumes, 20, tolerance_ml=between)['passed'] is False
    assert periodicity_report(volumes, 20, tolerance_ml=first * 1.01)['passed'] is True


@pytest.mark.parametrize('cycles', [0, 3])
def test_insufficient_beats_is_unavailable_and_never_passes(cycles):
    from physiosim.validation import periodicity_report
    report = periodicity_report(periodic_volumes(cycles, 20), 20, beats=3)
    assert report['available'] is False
    assert report['passed'] is False
    assert report['residuals_ml'] == []
    assert math.isnan(report['max_residual_ml'])


def test_exactly_enough_beats_is_available():
    from physiosim.validation import periodicity_report
    report = periodicity_report(periodic_volumes(4, 20), 20, beats=3)
    assert report['available'] is True
    assert report['passed'] is True


@pytest.mark.parametrize('kwargs', [
    {'samples_per_cycle': 3},
    {'samples_per_cycle': 2.5},
    {'samples_per_cycle': True},
    {'samples_per_cycle': 20, 'beats': 0},
    {'samples_per_cycle': 20, 'beats': 1.0},
    {'samples_per_cycle': 20, 'beats': True},
    {'samples_per_cycle': 20, 'tolerance_ml': 0.0},
    {'samples_per_cycle': 20, 'tolerance_ml': -1e-4},
    {'samples_per_cycle': 20, 'tolerance_ml': float('nan')},
    {'samples_per_cycle': 20, 'tolerance_ml': float('inf')},
    {'samples_per_cycle': 20, 'volumes': np.zeros(21)},
    {'samples_per_cycle': 20, 'volumes': np.zeros((21, 2, 2))},
    {'samples_per_cycle': 20, 'volumes': np.full((81, 6), np.nan)},
    {'samples_per_cycle': 20, 'volumes': np.zeros((70, 6))},
    {'samples_per_cycle': 20, 'volumes': np.zeros((0, 6))},
])
def test_invalid_inputs_raise(kwargs):
    from physiosim.validation import periodicity_report
    arguments = {'volumes': periodic_volumes(4, 20), 'samples_per_cycle': 20}
    arguments.update(kwargs)
    volumes = arguments.pop('volumes')
    samples_per_cycle = arguments.pop('samples_per_cycle')
    with pytest.raises(ValueError):
        periodicity_report(volumes, samples_per_cycle, **arguments)


def test_real_model_last_residual_matches_metrics():
    from physiosim.simulation import simulate
    from physiosim.validation import periodicity_report
    result = simulate(cycles=6, samples_per_cycle=50)
    report = periodicity_report(result.volumes, 50)
    assert report['available'] is True
    assert report['residuals_ml'][-1] == result.metrics()['final_beat_max_volume_difference_ml']
