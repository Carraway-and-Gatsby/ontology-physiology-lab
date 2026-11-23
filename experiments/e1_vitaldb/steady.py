"""Periodic steady state of the six-compartment model for a given parameter set.

The stroboscopic map F sends the six volumes at the start of a beat to the volumes one beat later. Total volume is
conserved, so the periodic state is a fixed point of F on the five-dimensional set of constant total volume. It is
found by a short relaxation followed by a root search, and then checked with the project's periodicity report.
No dataset is involved.
"""
from dataclasses import dataclass, replace

import numpy as np
from scipy.optimize import root

from physiosim.models import COMPARTMENTS, Parameters
from physiosim.simulation import simulate
from physiosim.validation import periodicity_report

SOLVER = dict(rtol=1e-7, atol=1e-8, method="DOP853")


class SteadyStateError(RuntimeError):
    """No periodic state passing the periodicity check was found."""


@dataclass
class Beat:
    """One periodic beat sampled at n+1 points (both endpoints)."""
    time: np.ndarray        # s, starts at 0
    pressures: np.ndarray   # (n+1, 6) mmHg, columns COMPARTMENTS
    volumes: np.ndarray     # (n+1, 6) mL
    flows: np.ndarray       # (n+1, 6) mL/s
    parameters: Parameters
    max_beat_residual_ml: float

    def mean_pressure(self, name: str) -> float:
        p = self.pressures[:, COMPARTMENTS.index(name)]
        return float(np.trapezoid(p, self.time) / (self.time[-1] - self.time[0]))

    @property
    def stroke_volume_ml(self) -> float:
        return float(np.trapezoid(self.flows[:, 0], self.time))

    @property
    def cardiac_output_l_min(self) -> float:
        return self.stroke_volume_ml / (self.time[-1] - self.time[0]) * 60.0 / 1000.0

    def extrema(self, name: str) -> tuple[float, float]:
        v = self.volumes[:, COMPARTMENTS.index(name)]
        return float(v.max()), float(v.min())


def _advance(p: Parameters, x: np.ndarray, beats: int, samples: int = 8) -> np.ndarray:
    r = simulate(parameters=replace(p, initial_volumes=tuple(float(v) for v in x)), cycles=beats,
                 samples_per_cycle=samples, **SOLVER)
    return r.volumes[-1]


def periodic_beat(p: Parameters, samples_per_cycle: int = 200, relax_beats: int = 12, tolerance_ml: float = 1e-4,
                  max_rounds: int = 6) -> Beat:
    """Periodic beat for parameters p (its initial volumes fix the total volume and the starting guess)."""
    total = float(np.sum(p.initial_volumes))
    x = np.asarray(p.initial_volumes, dtype=float)
    floor = 1e-6

    def residual(y5: np.ndarray) -> np.ndarray:
        y = np.append(y5, total - y5.sum())
        if np.any(y <= floor):
            return 1e3 * (1.0 + np.abs(np.minimum(y, floor))[:5])
        return (_advance(p, y, 1) - y)[:5]

    last_error = None
    for _ in range(max_rounds):
        try:
            x = _advance(p, x, relax_beats)
            sol = root(residual, x[:5], method="hybr", options={"xtol": 1e-10, "maxfev": 200})
            cand = np.append(sol.x, total - sol.x.sum())
            if np.all(cand > floor):
                x = cand
            r = simulate(parameters=replace(p, initial_volumes=tuple(float(v) for v in x)), cycles=4,
                         samples_per_cycle=samples_per_cycle, **SOLVER)
            rep = periodicity_report(r.volumes, samples_per_cycle, beats=3, tolerance_ml=tolerance_ml)
            if rep["passed"]:
                fb = r.final_beat
                return Beat(r.time[fb] - r.time[fb][0], r.pressures[fb], r.volumes[fb], r.flows[fb], p,
                            float(rep["max_residual_ml"]))
            x = r.volumes[-1]
            last_error = f"max beat residual {rep['max_residual_ml']:.3e} mL"
        except (RuntimeError, ValueError) as exc:  # integration failure or invalid volumes
            last_error = str(exc)
            x = np.asarray(p.initial_volumes, dtype=float)
            relax_beats *= 2
    raise SteadyStateError(last_error or "no periodic state")
