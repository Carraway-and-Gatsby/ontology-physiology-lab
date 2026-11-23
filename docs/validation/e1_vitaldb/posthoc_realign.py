"""Post hoc (not registered): correct the beat alignment of the ensemble and refit the affected W1 windows.

The registered foot is the minimum of the low-passed signal between two systolic peaks. In five cases that minimum
lies just after systole, not before the upstroke, so the ensemble beat starts in early diastole and its peak sits at
52 to 72 % of the cycle. Here the ensemble (a periodic curve) is rotated so that the minimum found in the 30 % of the
cycle before the peak is at phase 0. Windows whose ensemble does not change keep their registered fit.

    PYTHONPATH=src:. python docs/validation/e1_vitaldb/posthoc_realign.py
Writes results/e1_vitaldb/posthoc_failure_analysis/realigned.json
"""
import json
import multiprocessing as mp
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[3]
TEST = REPO / "results" / "e1_vitaldb" / "test"
OUT = REPO / "results" / "e1_vitaldb" / "posthoc_failure_analysis"


def realign(ens):
    e = np.asarray(ens, dtype=float)
    n = len(e)
    ipk = int(np.argmax(e))
    back = [(ipk - j) % n for j in range(0, int(0.3 * n) + 1)]
    foot = back[int(np.argmin(e[back]))]
    return np.roll(e, -foot), foot


def job(cid):
    from experiments.e1_vitaldb import calibrate
    w = json.loads((TEST / "features" / f"{cid:04d}.json").read_text())["windows"][0]
    e, foot = realign(w["ensemble"])
    obs = dict(w, ensemble=e.tolist())
    fit = calibrate.fit_window(obs)
    return {"caseid": cid, "shift_points": foot, "flow_index_l_min": fit.get("flow_index_l_min"), "ok": fit.get("ok"),
            "cost": fit.get("cost"), "rmse_waveform_mmhg": fit.get("rmse_waveform_mmhg"), "at_bound": fit.get("at_bound"),
            "model_pp": fit["model"]["sbp_mmhg"] - fit["model"]["dbp_mmhg"] if fit.get("ok") else None,
            "measured_pp": w["sbp_mmhg"] - w["dbp_mmhg"]}


def main():
    table = json.loads((TEST / "per_case_primary.json").read_text())
    shifts = {}
    for r in table:
        w = json.loads((TEST / "features" / f"{r['caseid']:04d}.json").read_text())["windows"][0]
        shifts[r["caseid"]] = realign(w["ensemble"])[1]
    changed = [c for c, s in shifts.items() if s != 0]
    with mp.Pool(min(12, max(1, len(changed))), maxtasksperchild=1) as pool:
        res = pool.map(job, changed, chunksize=1)
    (OUT / "realigned.json").write_text(json.dumps({"shifts": shifts, "refits": res}, indent=1))
    print("windows whose alignment changes:", {c: shifts[c] for c in changed})
    for r in res:
        print(r)


if __name__ == "__main__":
    main()
