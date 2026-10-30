"""Exploratory six-compartment circulation; see docs/physiology.md.

Internal units: s, mL, mmHg. This is not a reproduction of Smith 2004.
"""
from dataclasses import dataclass, fields
import math

import numpy as np

COMPARTMENTS = ("lv", "sa", "sv", "rv", "pa", "pv")


@dataclass(frozen=True)
class Parameters:
    """All numeric defaults are exploratory design choices, not fitted data.

    Elastances: mmHg/mL; compliances: mL/mmHg; resistances: mmHg s/mL;
    heart_rate: beats/min; volumes: mL; systolic_fraction: dimensionless.
    Tuple order is COMPARTMENTS.
    """

    heart_rate: float = 75.0
    emin_lv: float = 0.06
    emax_lv: float = 2.5
    emin_rv: float = 0.03
    emax_rv: float = 0.8
    systolic_fraction: float = 0.4
    compliance_sa: float = 1.5
    compliance_sv: float = 100.0
    compliance_pa: float = 5.0
    compliance_pv: float = 20.0
    resistance_aortic: float = 0.01
    resistance_systemic: float = 1.0
    resistance_tricuspid: float = 0.01
    resistance_pulmonary_valve: float = 0.01
    resistance_pulmonary: float = 0.1
    resistance_mitral: float = 0.01
    unstressed_volumes: tuple[float, ...] = (10.0, 700.0, 2500.0, 10.0, 100.0, 400.0)
    initial_volumes: tuple[float, ...] = (140.0, 850.0, 3200.0, 140.0, 180.0, 490.0)

    def __post_init__(self) -> None:
        for field in fields(self):
            value = getattr(self, field.name)
            if field.name in ("initial_volumes", "unstressed_volumes"):
                values = np.asarray(value, dtype=float)
                if values.shape != (6,) or not np.isfinite(values).all():
                    raise ValueError(f"{field.name} must contain six finite volumes")
                if np.any(values < 0) or (field.name == "initial_volumes" and np.any(values <= 0)):
                    raise ValueError(f"{field.name} contains invalid volumes")
            elif not math.isfinite(value) or value <= 0:
                raise ValueError(f"{field.name} must be finite and positive")
        if self.systolic_fraction >= 1:
            raise ValueError("systolic_fraction must lie strictly between zero and one")
        if self.emax_lv < self.emin_lv or self.emax_rv < self.emin_rv:
            raise ValueError("maximum elastance must not be below minimum elastance")

    @property
    def period(self) -> float:
        """Cardiac cycle length in seconds."""
        return 60.0 / self.heart_rate


def elastance(time: float, parameters: Parameters) -> tuple[float, float]:
    """Synchronous smooth cosine activation, zero outside systole."""
    phase = (time % parameters.period) / parameters.period
    activation = (
        0.5 * (1.0 - math.cos(2.0 * math.pi * phase / parameters.systolic_fraction))
        if phase < parameters.systolic_fraction else 0.0
    )
    return (
        parameters.emin_lv + (parameters.emax_lv - parameters.emin_lv) * activation,
        parameters.emin_rv + (parameters.emax_rv - parameters.emin_rv) * activation,
    )


def pressures(time: float, volumes: np.ndarray, parameters: Parameters) -> np.ndarray:
    """Six pressures (mmHg) from six volumes (mL); no clipping."""
    elv, erv = elastance(time, parameters)
    coefficients = np.array([
        elv, 1.0 / parameters.compliance_sa, 1.0 / parameters.compliance_sv,
        erv, 1.0 / parameters.compliance_pa, 1.0 / parameters.compliance_pv,
    ])
    return coefficients * (np.asarray(volumes) - parameters.unstressed_volumes)


FLOW_NAMES = ("aortic", "systemic", "tricuspid", "pulmonary_valve", "pulmonary", "mitral")
VALVE_INDICES = (0, 2, 3, 5)


def flows(pressure: np.ndarray, parameters: Parameters) -> np.ndarray:
    """Directed ring-edge flows (mL/s), four ideal diodes and two resistors."""
    pressure = np.asarray(pressure)
    resistance = np.array([
        parameters.resistance_aortic, parameters.resistance_systemic,
        parameters.resistance_tricuspid, parameters.resistance_pulmonary_valve,
        parameters.resistance_pulmonary, parameters.resistance_mitral,
    ])
    flow = (pressure - np.roll(pressure, -1)) / resistance
    flow[list(VALVE_INDICES)] = np.maximum(flow[list(VALVE_INDICES)], 0.0)
    return flow


def rhs(time: float, volumes: np.ndarray, parameters: Parameters) -> np.ndarray:
    """Volume rates (mL/s); each edge appears once with each sign."""
    q = flows(pressures(time, volumes, parameters), parameters)
    return np.roll(q, 1) - q
