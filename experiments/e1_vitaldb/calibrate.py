"""Per-window calibration of the model to pressure features at the reference flow scale (E1).

Cardiac output is not identifiable from pressures (docs/validation/e1_vitaldb/IDENTIFIABILITY_RECORD.md), so the fit is
done with the arterial compliance held at the project default (the reference scale). Its output is the flow index
X = model cardiac output at the reference scale, which is proportional to the subject's cardiac output with an unknown
subject factor k = C_sa(subject) / C_sa(reference). The factor is supplied by anchor.py, never by this module.
"""
from dataclasses import replace

import numpy as np
from scipy.optimize import least_squares
from scipy.signal import butter, filtfilt

from physiosim.models import COMPARTMENTS, Parameters

from .signals import RULE
from .steady import Beat, SteadyStateError, periodic_beat

REFERENCE = Parameters()
N_POINTS = RULE["ensemble_points"]
LOWPASS_HZ = RULE["lowpass_hz"]
# name -> (kind, lower, upper): "log" = multiplier of the default on a log scale, "abs" = the value itself
FREE = {
    "resistance_systemic": ("log", 0.05, 20.0),
    "emax_lv": ("log", 0.10, 20.0),
    "systolic_fraction": ("abs", 0.15, 0.60),
    "stressed_volume": ("log", 0.20, 5.0),
    "resistance_pulmonary": ("log", 0.05, 20.0),
    "emin_rv": ("log", 0.05, 10.0),
}
# Fit weights (mmHg): design choices, not uncertainty claims. The 50 waveform points share the weight of one
# observable group, so the waveform does not outvote CVP and mean PAP by its number of samples.
WEIGHTS = {"art": 4.0, "cvp": 2.0, "mpap": 3.0}
EQUAL_WEIGHTS = {"art": 1.0, "cvp": 1.0, "mpap": 1.0}
STARTS = 3
START_SEED = 20261123
FAIL = 1.0e3


def build(theta: np.ndarray, heart_rate: float, free: dict = FREE, base: Parameters = REFERENCE,
          guess: np.ndarray | None = None, guess_scale: float | None = None) -> Parameters:
    """Parameters at the reference scale for the free-parameter vector theta."""
    kw = {"heart_rate": float(heart_rate)}
    scale = 1.0
    for value, (name, (kind, _, _)) in zip(theta, free.items()):
        v = float(np.exp(value)) if kind == "log" else float(value)
        if name == "stressed_volume":
            scale = v
        else:
            kw[name] = v * getattr(base, name) if kind == "log" else v
    v0, vi = np.asarray(base.unstressed_volumes), np.asarray(base.initial_volumes)
    if guess is not None and guess_scale:
        stressed = (np.asarray(guess) - v0) * (scale / guess_scale)
    else:
        stressed = scale * (vi - v0)
    kw["initial_volumes"] = tuple(float(x) for x in v0 + np.maximum(stressed, 1e-3))
    if "emax_lv" in kw and kw["emax_lv"] < base.emin_lv:
        kw["emax_lv"] = base.emin_lv
    if "emin_rv" in kw and kw["emin_rv"] > base.emax_rv:
        kw["emin_rv"] = base.emax_rv
    return replace(base, **kw)


def _lowpassed_cycle(p: np.ndarray, period: float, cutoff: float) -> np.ndarray:
    """One period of the model waveform after the same zero-phase low-pass that the measured signal receives."""
    m = len(p)
    b, a = butter(4, cutoff / (0.5 * m / period))
    return filtfilt(b, a, np.tile(p, 5))[2 * m:3 * m]


def model_features(beat: Beat, n: int = N_POINTS, lowpass_hz: float | None = LOWPASS_HZ) -> dict:
    """Arterial beat at n phase points starting at its minimum, plus mean venous and pulmonary arterial pressure.

    The arterial waveform is low-passed like the measured one (signals.RULE["lowpass_hz"]) before the foot is located,
    so that model and measurement are compared after identical processing."""
    raw = beat.pressures[:-1, COMPARTMENTS.index("sa")]
    period = float(beat.time[-1] - beat.time[0])
    p = _lowpassed_cycle(raw, period, lowpass_hz) if lowpass_hz else raw
    m = len(p)
    k = int(np.argmin(p))
    rolled = np.roll(p, -k)
    shape = np.interp(np.arange(n) * (m / n), np.arange(m + 1), np.append(rolled, rolled[0]))
    return {"ensemble": shape, "map_mmhg": beat.mean_pressure("sa"), "sbp_mmhg": float(p.max()),
            "dbp_mmhg": float(p.min()), "cvp_mmhg": beat.mean_pressure("sv"), "mpap_mmhg": beat.mean_pressure("pa"),
            "co_l_min": beat.cardiac_output_l_min, "sv_ml": beat.stroke_volume_ml,
            "rv_edv_ml": beat.extrema("rv")[0], "rv_esv_ml": beat.extrema("rv")[1],
            "lv_edv_ml": beat.extrema("lv")[0], "lv_esv_ml": beat.extrema("lv")[1],
            "p_pv_mmhg": beat.mean_pressure("pv")}


def _bounds(free: dict):
    lo = [np.log(a) if kind == "log" else a for kind, a, _ in free.values()]
    hi = [np.log(b) if kind == "log" else b for kind, _, b in free.values()]
    return np.array(lo), np.array(hi)


def _start(free: dict, rng: np.random.Generator | None) -> np.ndarray:
    x = np.array([0.0 if kind == "log" else getattr(REFERENCE, name) for name, (kind, _, _) in free.items()])
    if rng is not None:
        lo, hi = _bounds(free)
        jitter = np.array([rng.uniform(-0.5, 0.5) if kind == "log" else rng.uniform(-0.08, 0.08)
                           for kind, _, _ in free.values()])
        x = np.clip(x + jitter, lo + 1e-6, hi - 1e-6)
    return x


def fit_window(obs: dict, weights: dict = WEIGHTS, free: dict = FREE, starts: int = STARTS,
               seed: int = START_SEED, max_nfev: int = 60) -> dict:
    """Least-squares fit of the free parameters to one window's pressure features.

    obs needs heart_rate_bpm, ensemble (N_POINTS values), cvp_mmhg, mpap_mmhg. Returns the best of `starts` starts.
    """
    target = np.asarray(obs["ensemble"], dtype=float)
    if target.shape != (N_POINTS,):
        raise ValueError("ensemble must have N_POINTS values")
    hr = float(obs["heart_rate_bpm"])
    lo, hi = _bounds(free)
    names = list(free)
    scale_index = names.index("stressed_volume") if "stressed_volume" in names else None
    rng = np.random.default_rng(seed)
    best = None
    for s in range(starts):
        cache = {"guess": None, "scale": None, "evals": 0, "failures": 0}

        def residual(theta):
            cache["evals"] += 1
            try:
                p = build(theta, hr, free, guess=cache["guess"], guess_scale=cache["scale"])
                beat = periodic_beat(p, relax_beats=4 if cache["guess"] is not None else 12)
            except (SteadyStateError, ValueError):
                cache["failures"] += 1
                return np.full(N_POINTS + 2, FAIL)
            cache["guess"] = beat.volumes[0]
            cache["scale"] = float(np.exp(theta[scale_index])) if scale_index is not None else 1.0
            f = model_features(beat)
            return np.concatenate([(f["ensemble"] - target) / (weights["art"] * np.sqrt(N_POINTS)),
                                   [(f["cvp_mmhg"] - obs["cvp_mmhg"]) / weights["cvp"],
                                    (f["mpap_mmhg"] - obs["mpap_mmhg"]) / weights["mpap"]]])

        x0 = _start(free, None if s == 0 else rng)
        try:
            sol = least_squares(residual, x0, bounds=(lo, hi), method="trf", diff_step=2e-3, max_nfev=max_nfev,
                                xtol=1e-6, ftol=1e-8, gtol=1e-8)
        except Exception as exc:  # optimiser failure is recorded, not hidden
            sol = None
            err = str(exc)
        if sol is None or not np.all(np.isfinite(sol.fun)) or np.max(np.abs(sol.fun)) >= FAIL:
            continue
        if best is None or sol.cost < best["cost"]:
            best = {"theta": sol.x, "cost": float(sol.cost), "status": int(sol.status), "start": s,
                    "evals": cache["evals"], "steady_failures": cache["failures"],
                    "at_bound": [n for n, v, a, b in zip(names, sol.x, lo, hi) if min(v - a, b - v) < 1e-4]}
    if best is None:
        return {"ok": False, "reason": "no start produced a valid fit"}
    p = build(best["theta"], hr, free)
    beat = periodic_beat(p)
    f = model_features(beat)
    fine = periodic_beat(p, samples_per_cycle=400)
    values = {}
    for value, (name, (kind, _, _)) in zip(best["theta"], free.items()):
        values[name] = float(np.exp(value)) if kind == "log" else float(value)
    out = {"ok": True, "flow_index_l_min": f["co_l_min"],
           "numerical_relative_difference_co": abs(fine.cardiac_output_l_min / f["co_l_min"] - 1.0),
           "parameters": values, "cost": best["cost"], "status": best["status"], "start": best["start"],
           "evals": best["evals"], "steady_failures": best["steady_failures"], "at_bound": best["at_bound"],
           "max_beat_residual_ml": beat.max_beat_residual_ml,
           "rmse_waveform_mmhg": float(np.sqrt(np.mean((f["ensemble"] - target) ** 2)))}
    out["model"] = {k: (v.tolist() if isinstance(v, np.ndarray) else float(v)) for k, v in f.items()}
    return out
