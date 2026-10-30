"""Regenerate local numeric evidence; runs only this project's model."""
from dataclasses import asdict, replace
from pathlib import Path
import json
import platform

import numpy as np
import scipy

from physiosim.models import Parameters
from physiosim.simulation import simulate

out = Path(__file__).resolve().parent
p = Parameters()
baseline = simulate(p)
reduced = simulate(replace(p, emax_lv=p.emax_lv * 0.5))
tight = simulate(p, rtol=1e-9, atol=1e-10, max_step=p.period / 200)
report = {
    "status": "exploratory model execution, not clinical validation or published replication",
    "versions": {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__},
    "settings": {"cycles": 40, "samples_per_cycle": 400, "rtol": 1e-7, "atol_ml": 1e-8, "max_step_s": p.period / 100, "method": "DOP853"},
    "parameters": asdict(p),
    "baseline": baseline.metrics(),
    "reduced_contractility": reduced.metrics(),
    "tight": tight.metrics(),
    "baseline_vs_tight_max_volume_difference_ml": float(np.max(np.abs(baseline.volumes - tight.volumes))),
    "total_initial_volume_ml": float(sum(p.initial_volumes)),
    "minimum_volume_ml": float(baseline.volumes.min()),
    "minimum_valve_flow_ml_s": float(baseline.flows[:, [0, 2, 3, 5]].min()),
}
(out / "a_core_results.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
provenance = []
for name, value in asdict(p).items():
    if name.startswith("resistance"):
        unit = "mmHg s/mL"
    elif name.startswith("compliance"):
        unit = "mL/mmHg"
    elif name.startswith("em"):
        unit = "mmHg/mL"
    elif name.endswith("volumes"):
        unit = "mL; order lv,sa,sv,rv,pa,pv"
    else:
        unit = {"heart_rate": "beat/min", "systolic_fraction": "1"}[name]
    provenance.append({"parameter": name, "default": value, "unit": unit,
        "provenance": "author-selected exploratory default", "source_id": None,
        "fitted": False, "clinical_validation": False})
(out / "a_parameter_provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
print(json.dumps(report, indent=2, allow_nan=False))
