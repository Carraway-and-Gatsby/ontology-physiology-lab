"""Versioned explicit eight-volume model; all parameters are caller supplied.

Units: s, mL, mmHg, mL/s. No fitted/reference physiological defaults.
"""
from dataclasses import dataclass, fields
from numbers import Real
import math
import numpy as np
from .cardiovascular import elastance

MODEL_ID = 'four_chamber_m1'
MODEL_VERSION = '1.0.0'
PRESSURE_REFERENCE = ('model gauge pressure relative to one common fixed external pressure of 0 mmHg; '
                      'no intrathoracic/pericardial pressure')
COMPARTMENTS = ('lv', 'sa', 'sv', 'ra', 'rv', 'pa', 'pv', 'la')


@dataclass(frozen=True)
class Edge:
    name: str
    source: str
    target: str
    kind: str


_ENDPOINTS = (
    ('aortic','lv','sa','diode'), ('systemic','sa','sv','resistor'),
    ('venous_return','sv','ra','resistor'), ('tricuspid','ra','rv','diode'),
    ('pulmonary_valve','rv','pa','diode'), ('pulmonary','pa','pv','resistor'),
    ('pulmonary_venous','pv','la','resistor'), ('mitral','la','lv','diode'))
EDGES = tuple(Edge(*row) for row in _ENDPOINTS)
EDGE_NAMES = tuple(e.name for e in EDGES)


def validate_incidence(matrix):
    a = np.asarray(matrix)
    if (a.shape != (8,8) or not np.isin(a, [-1,0,1]).all()
            or not np.all((a == 1).sum(axis=0) == 1)
            or not np.all((a == -1).sum(axis=0) == 1)):
        raise ValueError('incidence requires one source and one target per edge')


def validate_topology(compartments, edges):
    """Validate this version's named endpoint contract, not mass balance alone."""
    if tuple(compartments) != COMPARTMENTS or tuple(
            (e.name,e.source,e.target,e.kind) for e in edges) != _ENDPOINTS:
        raise ValueError('topology differs from the versioned M1 endpoint contract')


validate_topology(COMPARTMENTS, EDGES)
SOURCE = np.array([COMPARTMENTS.index(e.source) for e in EDGES])
TARGET = np.array([COMPARTMENTS.index(e.target) for e in EDGES])
VALVE_INDICES = np.array([i for i,e in enumerate(EDGES) if e.kind == 'diode'])
INCIDENCE = np.zeros((8,8))
INCIDENCE[SOURCE, np.arange(8)] = -1
INCIDENCE[TARGET, np.arange(8)] = 1
validate_incidence(INCIDENCE)
for _array in (SOURCE, TARGET, VALVE_INDICES, INCIDENCE):
    _array.setflags(write=False)


def positive_scalar(value, name):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real) or not math.isfinite(value) or value <= 0:
        raise ValueError(f'{name} must be a finite positive real scalar')


def vector(value, name):
    if isinstance(value, (tuple, list)) and any(isinstance(x, (bool, np.bool_)) for x in value):
        raise ValueError(f'{name} must not contain booleans')
    raw = np.asarray(value)
    if raw.shape != (8,) or raw.dtype.kind not in 'iuf' or not np.isfinite(raw).all():
        raise ValueError(f'{name} must contain eight finite real numbers')
    return raw.astype(float)


@dataclass(frozen=True)
class FourChamberM1Parameters:
    """Required inputs. E: mmHg/mL; C: mL/mmHg; R: mmHg*s/mL; V: mL.

    Volumes follow COMPARTMENTS, HR is beats/min, systolic_fraction dimensionless.
    Tuple canonicalization prevents mutation through caller-owned lists.
    """
    heart_rate: float
    systolic_fraction: float
    emin_lv: float
    emax_lv: float
    emin_rv: float
    emax_rv: float
    elastance_la: float
    elastance_ra: float
    compliance_sa: float
    compliance_sv: float
    compliance_pa: float
    compliance_pv: float
    resistance_aortic: float
    resistance_systemic: float
    resistance_venous_return: float
    resistance_tricuspid: float
    resistance_pulmonary_valve: float
    resistance_pulmonary: float
    resistance_pulmonary_venous: float
    resistance_mitral: float
    unstressed_volumes: tuple[float, ...]
    initial_volumes: tuple[float, ...]

    def __post_init__(self):
        for field in fields(self):
            value = getattr(self, field.name)
            if field.name.endswith('volumes'):
                a = vector(value, field.name)
                if np.any(a < 0) or (field.name == 'initial_volumes' and np.any(a <= 0)):
                    raise ValueError(f'{field.name} contains invalid volumes')
                object.__setattr__(self, field.name, tuple(float(x) for x in a))
            else:
                positive_scalar(value, field.name)
                object.__setattr__(self, field.name, float(value))
        if self.systolic_fraction >= 1 or self.emax_lv < self.emin_lv or self.emax_rv < self.emin_rv:
            raise ValueError('require systolic_fraction < 1 and Emax >= Emin')

    @property
    def period(self):
        return 60. / self.heart_rate


def pressures(time, volumes, parameters):
    """Common-gauge pressures, no volume or pressure clipping."""
    if isinstance(time, (bool, np.bool_)) or not isinstance(time, Real) or not math.isfinite(time):
        raise ValueError('time must be finite and real')
    p = parameters
    v = vector(volumes, 'volumes')
    elv, erv = elastance(time, p)
    coefficient = np.array([elv, 1/p.compliance_sa, 1/p.compliance_sv, p.elastance_ra,
                            erv, 1/p.compliance_pa, 1/p.compliance_pv, p.elastance_la])
    return coefficient*(v-p.unstressed_volumes)


def resistances(p):
    return np.array([getattr(p, 'resistance_'+e.name) for e in EDGES])


def edge_flows(pressure, parameters):
    """Signed resistors and exactly max(dp/R,0) for the four ideal diodes."""
    pressure = vector(pressure, 'pressure')
    q = (pressure[SOURCE]-pressure[TARGET])/resistances(parameters)
    q[VALVE_INDICES] = np.maximum(q[VALVE_INDICES], 0.)
    return q


def rhs(time, volumes, parameters):
    return INCIDENCE @ edge_flows(pressures(time, volumes, parameters), parameters)
