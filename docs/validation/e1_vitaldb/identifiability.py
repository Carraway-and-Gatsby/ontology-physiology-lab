"""E1 prerequisite (methodology v1, section 5.2): identifiability of the model from pressure observables.

No dataset is read. Run from the repository root:  python docs/validation/e1_vitaldb/identifiability.py
Writes docs/validation/e1_vitaldb/identifiability_results.json
"""
from dataclasses import replace
import json
from pathlib import Path

import numpy as np

from physiosim.models import COMPARTMENTS, Parameters
from physiosim.simulation import simulate

NAMES = ["emin_lv", "emax_lv", "emin_rv", "emax_rv", "systolic_fraction", "compliance_sa", "compliance_sv",
         "compliance_pa", "compliance_pv", "resistance_aortic", "resistance_systemic", "resistance_tricuspid",
         "resistance_pulmonary_valve", "resistance_pulmonary", "resistance_mitral", "stressed_volume"]
# Exponent of each parameter under the flow-scaling group k: elastances and resistances / k, compliances and
# stressed volumes * k, systolic_fraction unchanged.
SCALE = np.array([-1, -1, -1, -1, 0, 1, 1, 1, 1, -1, -1, -1, -1, -1, -1, 1], float)


def build(p0: Parameters, theta: np.ndarray) -> Parameters:
    """p0 with each parameter multiplied by exp(theta); the last entry scales every initial stressed volume."""
    kw = {n: getattr(p0, n) * float(np.exp(t)) for n, t in zip(NAMES[:-1], theta[:-1])}
    v0, vi = np.array(p0.unstressed_volumes), np.array(p0.initial_volumes)
    kw["initial_volumes"] = tuple(v0 + np.exp(theta[-1]) * (vi - v0))
    return replace(p0, **kw)


def observe(p: Parameters, cycles: int, n: int = 40):
    """40 samples of the arterial pressure beat, mean venous and mean pulmonary arterial pressure; CO separately."""
    r = simulate(parameters=p, cycles=cycles, samples_per_cycle=400)
    fb = r.final_beat
    pressure, t = r.pressures[fb], r.time[fb]
    idx = np.linspace(0, 400, n, endpoint=False).astype(int)
    mean = lambda c: float(np.trapezoid(pressure[:, COMPARTMENTS.index(c)], t) / (t[-1] - t[0]))
    return (np.concatenate([pressure[idx, COMPARTMENTS.index("sa")], [mean("sv"), mean("pa")]]),
            r.metrics()["cardiac_output_l_min"], r)


def scaling_check(p0: Parameters):
    base = simulate(parameters=p0, cycles=40, samples_per_cycle=400)
    rows = []
    for k in (0.5, 0.7, 1.0, 1.5, 2.0):
        r = simulate(parameters=build(p0, np.log(k) * SCALE), cycles=40, samples_per_cycle=400)
        rows.append({"k": k, "max_abs_pressure_difference_mmhg": float(np.max(np.abs(r.pressures - base.pressures))),
                     "cardiac_output_l_min": r.metrics()["cardiac_output_l_min"]})
    return rows


def sensitivity(p0: Parameters, h: float = 0.02, cycles: int = 60):
    cols, dco = [], []
    for i in range(len(NAMES)):
        e = np.zeros(len(NAMES)); e[i] = h
        yp, cp, _ = observe(build(p0, e), cycles); ym, cm, _ = observe(build(p0, -e), cycles)
        cols.append((yp - ym) / (2 * h)); dco.append((np.log(cp) - np.log(cm)) / (2 * h))
    jac = np.array(cols).T
    s = np.linalg.svd(jac, compute_uv=False)
    u = SCALE / np.linalg.norm(SCALE)
    return {"singular_values_mmhg_per_unit_log_change": [float(x) for x in s],
            "norm_of_jacobian_times_scaling_direction": float(np.linalg.norm(jac @ u)),
            "dlnCO_along_scaling_direction": float(np.array(dco) @ SCALE),
            "directions_above_1_percent_of_largest": int((s > 0.01 * s[0]).sum()),
            "directions_above_0p1_percent_of_largest": int((s > 0.001 * s[0]).sum())}


def main():
    points = {"default": Parameters(),
              "lower_pressure": replace(Parameters(), resistance_systemic=0.75, emax_lv=2.0, heart_rate=65.0,
                                        compliance_sa=2.0)}
    out = {"observables": "40 samples of P_sa over the final beat + mean P_sv + mean P_pa (42 values, mmHg)",
           "parameters": NAMES, "scaling_exponents": SCALE.tolist(), "points": {}}
    for label, p0 in points.items():
        y, co, _ = observe(p0, 60)
        out["points"][label] = {"mean_p_sa": float(y[:40].mean()), "mean_p_sv": float(y[40]), "mean_p_pa": float(y[41]),
                                "cardiac_output_l_min": co, "scaling": scaling_check(p0), "sensitivity": sensitivity(p0)}
    path = Path(__file__).with_name("identifiability_results.json")
    path.write_text(json.dumps(out, indent=2) + "\n")
    for label, d in out["points"].items():
        print(label, "| scaling:", [(r["k"], f'{r["max_abs_pressure_difference_mmhg"]:.1e}', round(r["cardiac_output_l_min"], 3)) for r in d["scaling"]])
        s = d["sensitivity"]
        print("   singular values:", np.round(s["singular_values_mmhg_per_unit_log_change"], 3))
        print("   |J u_scale| =", f'{s["norm_of_jacobian_times_scaling_direction"]:.2e}', "| dlnCO/dk =", round(s["dlnCO_along_scaling_direction"], 4),
              "| >1%:", s["directions_above_1_percent_of_largest"], "| >0.1%:", s["directions_above_0p1_percent_of_largest"])


if __name__ == "__main__":
    main()
