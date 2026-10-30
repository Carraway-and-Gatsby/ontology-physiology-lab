"""Runtime numerical audits; passing is not external biological validation."""
import numpy as np


def audit_closed_loop(time, volumes, flows, *, valve_columns, volume_tolerance_ml=1e-6):
    time, volumes, flows = map(np.asarray, (time, volumes, flows))
    if not np.isfinite(volume_tolerance_ml) or volume_tolerance_ml <= 0:
        raise ValueError('volume tolerance must be finite and positive')
    if time.ndim != 1 or len(time) < 2 or volumes.ndim != 2 or flows.ndim != 2:
        raise ValueError('expected time vector and sample-by-variable arrays')
    if len(time) != len(volumes) or len(time) != len(flows):
        raise ValueError('time and observation shapes differ')
    if not all(np.isfinite(a).all() for a in (time, volumes, flows)):
        raise ValueError('nonfinite trajectory')
    if np.any(np.diff(time) <= 0):
        raise ValueError('time must be strictly increasing')
    if np.any(volumes <= 0):
        raise ValueError('nonpositive compartment volume')
    if np.any(flows[:, valve_columns] < 0):
        raise ValueError('reverse valve flow')
    drift = float(np.max(np.abs(volumes.sum(axis=1) - volumes[0].sum())))
    if drift > volume_tolerance_ml:
        raise ValueError(f'blood volume conservation violated: {drift} mL')
    return {'volume_drift_ml': drift, 'volume_tolerance_ml': volume_tolerance_ml}


def periodicity_report(volumes, samples_per_cycle, *, beats=3, tolerance_ml=1e-4):
    """Compare the last `beats` beats with their predecessors, in mL.

    volumes: (n_samples, n_states) in mL, uniformly sampled with exactly
    samples_per_cycle intervals per beat; beat boundaries sit at multiples of
    samples_per_cycle and the last sample ends the last beat. For each beat j,
    residual_j is max |V_j - V_(j-1)| over phases and states, with both beat
    endpoints included. Passing is a numerical settling check only: it is not
    biological validation and does not prove a unique limit cycle.
    """
    volumes = np.asarray(volumes, dtype=float)
    if isinstance(samples_per_cycle, bool) or not isinstance(samples_per_cycle, (int, np.integer)) or samples_per_cycle < 4:
        raise ValueError('samples_per_cycle must be an integer >= 4')
    if isinstance(beats, bool) or not isinstance(beats, (int, np.integer)) or beats < 1:
        raise ValueError('beats must be an integer >= 1')
    if isinstance(tolerance_ml, bool) or not isinstance(tolerance_ml, (int, float, np.integer, np.floating)):
        raise ValueError('tolerance must be finite and positive')
    if not np.isfinite(tolerance_ml) or tolerance_ml <= 0:
        raise ValueError('tolerance must be finite and positive')
    if volumes.ndim != 2 or not np.isfinite(volumes).all():
        raise ValueError('volumes must be a finite 2-D array')
    n = int(samples_per_cycle)
    if (len(volumes) - 1) % n:
        raise ValueError('n_samples - 1 must be divisible by samples_per_cycle')
    cycles = (len(volumes) - 1) // n
    beats = int(beats)
    base = {'beats': beats, 'tolerance_ml': float(tolerance_ml)}
    if cycles < beats + 1:
        return {**base, 'residuals_ml': [], 'max_residual_ml': float('nan'),
                'monotone_nonincreasing': False, 'passed': False, 'available': False}
    residuals = []
    for j in range(cycles - beats, cycles):
        current = volumes[j * n:(j + 1) * n + 1]
        previous = volumes[(j - 1) * n:j * n + 1]
        residuals.append(float(np.max(np.abs(current - previous))))
    max_residual = max(residuals)
    monotone = all(later <= earlier for earlier, later in zip(residuals, residuals[1:]))
    return {**base, 'residuals_ml': residuals, 'max_residual_ml': max_residual,
            'monotone_nonincreasing': monotone, 'passed': max_residual <= tolerance_ml, 'available': True}
