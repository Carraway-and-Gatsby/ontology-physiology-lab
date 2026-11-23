"""Post hoc (not registered): are the five flat-waveform fits optimiser artefacts or the model's best fit?

Each degenerate W1 window is refitted from the fitted parameters of its three nearest non-degenerate cases (nearest in
standardised heart rate, MAP, pulse pressure, CVP and mean PAP), i.e. from pulsatile starting points.

    PYTHONPATH=src:. python docs/validation/e1_vitaldb/posthoc_degenerate_starts.py
Writes results/e1_vitaldb/posthoc_failure_analysis/degenerate_starts.json
"""
import json
import multiprocessing as mp
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[3]
TEST = REPO / "results" / "e1_vitaldb" / "test"
OUT = REPO / "results" / "e1_vitaldb" / "posthoc_failure_analysis"
DEGENERATE = [2872, 2326, 5837, 5607, 4800]
KEYS = ("heart_rate_bpm", "map_mmhg", "pp", "cvp_mmhg", "mpap_mmhg")


def load(cid):
    w = json.loads((TEST / "features" / f"{cid:04d}.json").read_text())["windows"][0]
    w["pp"] = w["sbp_mmhg"] - w["dbp_mmhg"]
    return w, json.loads((TEST / "fits" / f"{cid:04d}_w1.json").read_text())


def job(args):
    cid, donor, theta0 = args
    from scipy.optimize import least_squares
    from experiments.e1_vitaldb import calibrate as c
    from experiments.e1_vitaldb.steady import SteadyStateError, periodic_beat
    obs, _ = load(cid)
    target = np.asarray(obs["ensemble"]); hr = obs["heart_rate_bpm"]
    lo, hi = c._bounds(c.FREE)
    cache = {"guess": None, "scale": None}
    names = list(c.FREE); si = names.index("stressed_volume")

    def residual(theta):
        try:
            p = c.build(theta, hr, guess=cache["guess"], guess_scale=cache["scale"])
            beat = periodic_beat(p, relax_beats=4 if cache["guess"] is not None else 12)
        except (SteadyStateError, ValueError):
            return np.full(c.N_POINTS + 2, c.FAIL)
        cache["guess"], cache["scale"] = beat.volumes[0], float(np.exp(theta[si]))
        f = c.model_features(beat)
        return np.concatenate([(f["ensemble"] - target) / (c.WEIGHTS["art"] * np.sqrt(c.N_POINTS)),
                               [(f["cvp_mmhg"] - obs["cvp_mmhg"]) / c.WEIGHTS["cvp"],
                                (f["mpap_mmhg"] - obs["mpap_mmhg"]) / c.WEIGHTS["mpap"]]])

    x0 = np.clip(np.array(theta0), lo + 1e-6, hi - 1e-6)
    start_cost = float(0.5 * np.sum(residual(x0) ** 2))
    sol = least_squares(residual, x0, bounds=(lo, hi), method="trf", diff_step=2e-3, max_nfev=120, xtol=1e-6,
                        ftol=1e-8, gtol=1e-8)
    f = c.model_features(periodic_beat(c.build(sol.x, hr)))
    return {"caseid": cid, "donor": donor, "start_cost": start_cost, "cost": float(sol.cost),
            "flow_index_l_min": f["co_l_min"], "model_pp": f["sbp_mmhg"] - f["dbp_mmhg"], "measured_pp": obs["pp"],
            "rmse_waveform_mmhg": float(np.sqrt(np.mean((f["ensemble"] - target) ** 2))),
            "cvp_error": f["cvp_mmhg"] - obs["cvp_mmhg"], "mpap_error": f["mpap_mmhg"] - obs["mpap_mmhg"],
            "map_error": f["map_mmhg"] - obs["map_mmhg"]}


def main():
    from experiments.e1_vitaldb import calibrate as c
    table = json.loads((TEST / "per_case_primary.json").read_text())
    good = [r["caseid"] for r in table if r["caseid"] not in DEGENERATE]
    feats = {cid: load(cid) for cid in good + DEGENERATE}
    X = np.array([[feats[cid][0][k] for k in KEYS] for cid in good])
    mu, sd = X.mean(0), X.std(0)
    jobs = []
    for cid in DEGENERATE:
        z = (np.array([feats[cid][0][k] for k in KEYS]) - mu) / sd
        order = np.argsort(np.linalg.norm((X - mu) / sd - z, axis=1))[:3]
        for j in order:
            p = feats[good[j]][1]["parameters"]
            theta = [np.log(p[n]) if kind == "log" else p[n] for n, (kind, _, _) in c.FREE.items()]
            jobs.append((cid, good[j], theta))
    with mp.Pool(12, maxtasksperchild=1) as pool:
        res = pool.map(job, jobs, chunksize=1)
    summary = {cid: {k: feats[cid][0][k] for k in KEYS} for cid in DEGENERATE}
    (OUT / "degenerate_starts.json").write_text(json.dumps({"features": summary, "results": res}, indent=1))
    for r in res:
        print("%d from %d: start cost %.2f -> cost %.2f | X %.2f | model PP %.0f / measured %.0f | rmse %.1f | errors MAP %+.1f CVP %+.2f mPAP %+.2f"
              % (r["caseid"], r["donor"], r["start_cost"], r["cost"], r["flow_index_l_min"], r["model_pp"], r["measured_pp"],
                 r["rmse_waveform_mmhg"], r["map_error"], r["cvp_error"], r["mpap_error"]))
    print("features of the five:", json.dumps(summary))
    print("typical (median of non-degenerate):", dict(zip(KEYS, np.round(np.median(X, 0), 1))))


if __name__ == "__main__":
    main()
