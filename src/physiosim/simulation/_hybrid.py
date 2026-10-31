"""Integrate the ideal-diode model on smooth valve/activation regimes.

A fixed valve regime is continued smoothly while locating its first transition.
Only the portion up to that event is retained. Thus a dense interpolant never
has to approximate both sides of the ``max(flow, 0)`` corner.
"""
import numpy as np
from scipy.integrate import solve_ivp

from physiosim.models.cardiovascular import VALVE_INDICES, flows, pressures


_VALVES = np.asarray(VALVE_INDICES)
_DOWNSTREAM = (_VALVES + 1) % 6


def _right_hand_modes(time, volume, parameters, modes, boundary):
    """Disambiguate roundoff-scale ties, including simultaneous transitions.

    A short forward Euler probe selects the side of a zero-pressure event; it
    never advances the actual state. At a tie the physical RHS is independent
    of whether a zero-flow valve is labelled open or closed.
    """
    pressure = pressures(time, volume, parameters)
    gaps = pressure[_VALVES] - pressure[_DOWNSTREAM]
    eps = np.finfo(float).eps
    resolution = np.full(4, 64 * eps * max(1.0, float(np.max(np.abs(pressure)))))
    delta = min(np.sqrt(eps) * parameters.period, (boundary-time)/2)
    future = gaps
    if delta > 0 and time + delta > time:
        q = flows(pressure, parameters)
        probe_volume = volume + delta * (np.roll(q, 1) - q)
        probe_pressure = pressures(time+delta, probe_volume, parameters)
        future = probe_pressure[_VALVES] - probe_pressure[_DOWNSTREAM]
        # A root's time is accurate only to a few ulps. On a steep pressure
        # crossing its residual can exceed pressure-arithmetic roundoff.
        slope = np.abs(future-gaps) / delta
        resolution += 8 * eps * (1+abs(time)) * slope
    tied = np.abs(gaps) <= resolution
    modes = np.where(tied, modes, gaps > 0).copy()
    decided = tied & (np.abs(future) > resolution)
    modes[decided] = future[decided] > 0
    return modes


def integrate(parameters, times, cycles, cumulative_flows, method, rtol, atol, max_step):
    """Return volumes and optional cumulative flows at the requested times.

    Tolerances and max_step are forwarded unchanged. For cumulative flows they
    control increments within the current smooth regime, rather than a growing
    run-long integral. Reported totals are sums of those increments; neither
    volumes nor conservation residuals are projected or renormalized.
    """
    p = parameters
    resistance = np.asarray([
        p.resistance_aortic, p.resistance_systemic, p.resistance_tricuspid,
        p.resistance_pulmonary_valve, p.resistance_pulmonary, p.resistance_mitral,
    ])
    volume = np.asarray(p.initial_volumes, dtype=float).copy()
    offset = np.zeros(6)
    output = np.empty((len(times), 12 if cumulative_flows else 6))
    initial_pressure = pressures(float(times[0]), volume, p)
    modes = initial_pressure[_VALVES] > initial_pressure[_DOWNSTREAM]
    current = float(times[0])
    next_sample = 0
    zero_length_events = 0
    # The activation is smooth within systole and diastole, but not across
    # their boundaries at the order assumed by high-order RK interpolants.
    boundaries = [value for beat in range(cycles) for value in (
        (beat + p.systolic_fraction) * p.period, (beat + 1) * p.period)]
    boundaries[-1] = float(times[-1])

    for boundary in boundaries:
        boundary = min(float(boundary), float(times[-1]))
        while current < boundary:
            modes = _right_hand_modes(current, volume, p, modes, boundary)
            regime = modes.copy()

            def derivative(time, state):
                pressure = pressures(time, state[:6], p)
                q = (pressure - np.roll(pressure, -1)) / resistance
                q[_VALVES[~regime]] = 0.0
                dv = np.roll(q, 1) - q
                return np.concatenate((dv, q)) if cumulative_flows else dv

            events = []
            for edge, opened in zip(_VALVES, regime):
                def event(time, state, edge=int(edge), opened=bool(opened)):
                    pressure = pressures(time, state[:6], p)
                    gap = float(pressure[edge] - pressure[(edge+1) % 6])
                    # An identically zero gap is not a transition. This signed
                    # sentinel changes no nonzero gap and prevents zero-flow
                    # equilibria from repeatedly terminating at the same time.
                    if gap == 0.0:
                        return np.finfo(float).eps if opened else -np.finfo(float).eps
                    return gap
                event.terminal = True
                event.direction = -1 if opened else 1
                events.append(event)

            initial = np.concatenate((volume, np.zeros(6))) if cumulative_flows else volume
            solution = solve_ivp(
                derivative, (current, boundary), initial, method=method,
                rtol=rtol, atol=atol, max_step=max_step,
                dense_output=True, events=events,
            )
            if not solution.success:
                raise RuntimeError(f"Cardiovascular integration failed: {solution.message}")
            end = float(solution.t[-1])
            end_state = solution.y[:, -1]
            end_sample = int(np.searchsorted(times, end, side='right'))
            if end_sample > next_sample:
                values = solution.sol(times[next_sample:end_sample]).T
                output[next_sample:end_sample, :6] = values[:, :6]
                if cumulative_flows:
                    output[next_sample:end_sample, 6:] = values[:, 6:] + offset
                next_sample = end_sample
            volume = end_state[:6].copy()
            if cumulative_flows:
                offset = offset + end_state[6:]
            if solution.status == 1:
                for index, found in enumerate(solution.t_events):
                    if len(found):
                        modes[index] = not modes[index]
            if end <= current:
                zero_length_events += 1
                if solution.status != 1 or zero_length_events > 8:
                    raise RuntimeError('Cardiovascular valve events failed to advance time')
            else:
                zero_length_events = 0
            current = end
    if next_sample != len(times):
        raise RuntimeError('Cardiovascular integration did not cover all requested samples')
    return output[:, :6], output[:, 6:] if cumulative_flows else None
