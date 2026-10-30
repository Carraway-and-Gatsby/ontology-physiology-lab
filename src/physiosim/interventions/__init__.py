"""Explicit immutable parameter perturbations, without pharmacology claims."""
from dataclasses import asdict, dataclass, replace


@dataclass(frozen=True)
class ParameterChange:
    name: str
    target: str
    factor: float
    mechanism: str
    rationale: str
    limitations: str = 'Exploratory parameter change; not a drug-dose or clinical outcome prediction.'

    def __post_init__(self):
        import math
        if not math.isfinite(self.factor) or self.factor <= 0:
            raise ValueError('factor must be finite and strictly positive')

    def apply(self, parameters, *, time_s: float = 0.0):
        import math
        if not math.isfinite(time_s) or time_s < 0:
            raise ValueError('time_s must be finite and nonnegative')
        before = getattr(parameters, self.target)
        after = before * self.factor
        altered = replace(parameters, **{self.target: after})
        return altered, {**asdict(self), 'before': before, 'after': after, 'time_s': time_s}
