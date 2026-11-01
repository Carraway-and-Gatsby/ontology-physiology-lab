"""Integration and sampled outputs for the exploratory cardiovascular model."""
from dataclasses import dataclass

import numpy as np
from scipy.integrate import trapezoid

from physiosim.models.cardiovascular import (
    COMPARTMENTS, FLOW_NAMES, Parameters, flows, pressures,
)
from ._hybrid import integrate


@dataclass
class SimulationResult:
    """Sampled arrays: time (s), volumes (mL), pressures (mmHg), flows (mL/s).

    Rows are samples; columns follow compartment_names or flow_names.
    All simulated beats are retained, including the initial transient.
    """
    time: np.ndarray
    volumes: np.ndarray
    pressures: np.ndarray
    flows: np.ndarray
    parameters: Parameters
    samples_per_cycle: int
    compartment_names: tuple[str, ...] = COMPARTMENTS
    flow_names: tuple[str, ...] = FLOW_NAMES
    cumulative_flows: np.ndarray | None = None

    @property
    def final_beat(self) -> slice:
        """Slice selecting the last full beat, both endpoints included."""
        return slice(-self.samples_per_cycle - 1, None)

    def metrics(self) -> dict[str, float]:
        """Sample-based summaries; no claim that the last beat is converged.

        SV integrates forward aortic flow, whereas EF uses LV volume extrema.
        Pressure means use time integration. The beat difference compares all
        six volume waveforms to the penultimate beat at identical phases.
        """
        beat = self.final_beat
        t, v, pressure = self.time[beat], self.volumes[beat], self.pressures[beat]
        duration = t[-1] - t[0]
        sv = float(trapezoid(self.flows[beat, 0], t))
        edv, esv = float(v[:, 0].max()), float(v[:, 0].min())
        n = self.samples_per_cycle
        beat_difference = (
            float(np.max(np.abs(v - self.volumes[-2*n-1:-n])))
            if len(self.time) >= 2*n + 1 else float("nan")
        )
        return {
            "heart_rate_bpm": self.parameters.heart_rate,
            "stroke_volume_ml": sv,
            "cardiac_output_l_min": sv / duration * 60.0 / 1000.0,
            "cardiac_output_m3_s": sv / duration * 1e-6,
            "lv_edv_ml": edv,
            "lv_esv_ml": esv,
            "lv_ejection_fraction": (edv - esv) / edv,
            "systemic_systolic_pressure_mmhg": float(pressure[:, 1].max()),
            "systemic_diastolic_pressure_mmhg": float(pressure[:, 1].min()),
            "systemic_mean_pressure_mmhg": float(trapezoid(pressure[:, 1], t) / duration),
            "pulmonary_mean_pressure_mmhg": float(trapezoid(pressure[:, 4], t) / duration),
            "pulmonary_venous_mean_pressure_mmhg": float(trapezoid(pressure[:, 5], t) / duration),
            "volume_drift_ml": float(np.max(np.abs(self.volumes.sum(axis=1) - self.volumes[0].sum()))),
            "final_beat_max_volume_difference_ml": beat_difference,
        }

    def local_balance_residual_ml(self) -> float:
        """Maximum cumulative local balance residual (mL).

        Edge ``i`` is compartment ``i``'s outflow and edge ``i-1`` (modulo
        six) is its inflow. This residual is a linear invariant of the
        augmented ODE, so a near-zero value verifies incidence/sign wiring and
        roundoff only. It does not verify cumulative-flow quadrature accuracy;
        that requires tolerance refinement.
        """
        if self.cumulative_flows is None:
            raise ValueError("cumulative flows are unavailable")
        cumulative_inflow = np.roll(self.cumulative_flows, 1, axis=1)
        cumulative_outflow = self.cumulative_flows
        residual = (
            self.volumes - self.volumes[0]
            - (cumulative_inflow - cumulative_outflow)
        )
        return float(np.max(np.abs(residual)))

    def cumulative_metrics(self) -> dict[str, float]:
        """Final-beat metrics from solver-integrated flows.

        Values use differences of the cumulative states rather than sampled
        post-hoc quadrature. Their numerical accuracy must still be established
        by tolerance refinement.
        """
        if self.cumulative_flows is None:
            raise ValueError("cumulative flows are unavailable")
        beat = self.final_beat
        duration = float(self.time[beat][-1] - self.time[beat][0])
        throughput = self.cumulative_flows[-1] - self.cumulative_flows[beat.start]
        sv = float(throughput[0])
        result = {
            "stroke_volume_cumulative_ml": sv,
            "cardiac_output_cumulative_l_min": sv / duration * 60.0 / 1000.0,
        }
        result.update({
            f"final_beat_net_throughput_{name}_ml": float(value)
            for name, value in zip(self.flow_names, throughput)
        })
        return result


def simulate(
    parameters: Parameters | None = None,
    cycles: int = 40,
    samples_per_cycle: int = 400,
    rtol: float = 1e-7,
    atol: float = 1e-8,
    max_step: float | None = None,
    method: str = "DOP853",
    cumulative_flows: bool = False,
) -> SimulationResult:
    """Integrate volume states; optionally integrate six cumulative flows.

    Tolerances are relative (dimensionless) and absolute (mL), respectively.
    The ideal-diode valves are integrated as smooth regimes separated by
    terminal pressure-gap events; activation boundaries also split integration.
    With ``cumulative_flows=True``, the same scalar ``atol`` in mL applies to
    six volumes and six local flow integrals. Integrals restart at zero at each
    regime and their offsets are accumulated, avoiding error scales that grow
    with run length. Output sampling does not control solver step size. No
    renormalization or positivity projection is applied to the trajectory.

    Runge-Kutta (and linear multistep) methods preserve linear invariants of
    an ODE; dV/dt and dC/dt are built from the same evaluated flow vector, and
    dense output is linear in the stage values, so the invariant also
    holds at output samples up to roundoff (~eps*|C|). Consequently,
    near-zero augmented local balance residuals verify incidence/sign wiring
    and roundoff only, not cumulative-flow quadrature accuracy. Establish the
    latter separately through tolerance refinement. Interpolants are used
    only on one side of a valve transition, not across its ideal-diode kink.
    """
    p = parameters if parameters is not None else Parameters()
    if not isinstance(cumulative_flows, bool):
        raise ValueError("cumulative_flows must be a bool")
    for name, value, minimum in (("cycles", cycles, 1), ("samples_per_cycle", samples_per_cycle, 4)):
        if isinstance(value, bool) or not isinstance(value, (int, np.integer)) or value < minimum:
            raise ValueError(f"{name} must be an integer >= {minimum}")
    controls = {"rtol": rtol, "atol": atol}
    if max_step is not None:
        controls["max_step"] = max_step
    for name, value in controls.items():
        if not np.isscalar(value) or not np.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be finite and positive")
    time = np.linspace(0.0, cycles * p.period, cycles * samples_per_cycle + 1)
    volume, cumulative = integrate(
        p, time, cycles, cumulative_flows, method, rtol, atol,
        p.period / 100.0 if max_step is None else max_step,
    )
    pressure = np.array([pressures(t, v, p) for t, v in zip(time, volume)])
    flow = np.array([flows(pr, p) for pr in pressure])
    return SimulationResult(
        time, volume, pressure, flow, p, samples_per_cycle,
        cumulative_flows=cumulative,
    )
