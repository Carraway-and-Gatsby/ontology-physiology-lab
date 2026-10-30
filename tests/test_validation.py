import importlib.util
import numpy as np
import pytest


def test_conservation_audit_rejects_real_volume_leak():
    assert importlib.util.find_spec('physiosim.validation') is not None, 'Missing numerical audit'
    from physiosim.validation import audit_closed_loop
    t = np.array([0., 1., 2.])
    volumes = np.array([[100., 200.], [101., 199.], [102., 198.]])
    flows = np.array([[0., 5.], [4., 3.], [0., 1.]])
    report = audit_closed_loop(t, volumes, flows, valve_columns=[0])
    assert report['volume_drift_ml'] == 0.0
    volumes[-1, 0] += 0.01
    with pytest.raises(ValueError, match='conservation'):
        audit_closed_loop(t, volumes, flows, valve_columns=[0])


@pytest.mark.parametrize('fault', ['reverse_valve', 'nonfinite', 'negative_volume', 'time_order', 'shape', 'bad_tolerance'])
def test_audit_rejects_invalid_trajectories(fault):
    from physiosim.validation import audit_closed_loop
    t = np.array([0., 1., 2.])
    v = np.full((3, 2), 100.)
    q = np.zeros((3, 2))
    tolerance = 1e-6
    if fault == 'reverse_valve': q[1, 0] = -1.
    if fault == 'nonfinite': v[1, 0] = np.nan
    if fault == 'negative_volume': v[:, 0] = -1.
    if fault == 'time_order': t[1] = 3.
    if fault == 'shape': q = q[:2]
    if fault == 'bad_tolerance': tolerance = float('nan')
    with pytest.raises(ValueError):
        audit_closed_loop(t, v, q, valve_columns=[0], volume_tolerance_ml=tolerance)
