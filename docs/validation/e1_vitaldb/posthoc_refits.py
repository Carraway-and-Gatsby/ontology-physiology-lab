"""Post hoc refits for the E1 failure analysis (not registered). Uses only the saved window features.

    PYTHONPATH=src:. python docs/validation/e1_vitaldb/posthoc_refits.py

A. The five degenerate W1 fits again with 12 starts: does a non-degenerate solution of lower cost exist?
B. Twelve non-degenerate W1 windows refitted with one fixed parameter changed at a time: how much does the flow
   index depend on parameters that were held at unsourced defaults?
Writes results/e1_vitaldb/posthoc_failure_analysis/refits.json
"""
from dataclasses import replace
import json
import multiprocessing as mp
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
TEST = REPO / "results" / "e1_vitaldb" / "test"
OUT = REPO / "results" / "e1_vitaldb" / "posthoc_failure_analysis"
DEGENERATE = [2872, 2326, 5837, 5607, 4800]
VARIANTS = {"emin_lv x2": {"emin_lv": 2.0}, "emin_lv /2": {"emin_lv": 0.5}, "emax_rv x2": {"emax_rv": 2.0},
            "compliance_sv x2": {"compliance_sv": 2.0}, "compliance_pv x2": {"compliance_pv": 2.0},
            "compliance_pa x2": {"compliance_pa": 2.0}, "resistance_aortic x3": {"resistance_aortic": 3.0}}


def window(cid):
    return json.loads((TEST / "features" / f"{cid:04d}.json").read_text())["windows"][0]


def job(args):
    kind, cid, name = args
    from experiments.e1_vitaldb import calibrate
    obs = window(cid)
    if kind == "A":
        fit = calibrate.fit_window(obs, starts=12, seed=777)
    else:
        base = calibrate.REFERENCE
        base = replace(base, **{k: getattr(base, k) * v for k, v in VARIANTS[name].items()})
        calibrate.build.__defaults__ = (calibrate.FREE, base, None, None)   # fixed parameters of this variant
        fit = calibrate.fit_window(obs)
    keep = {k: fit.get(k) for k in ("ok", "flow_index_l_min", "cost", "rmse_waveform_mmhg", "at_bound", "start", "parameters")}
    if fit.get("ok"):
        keep["model_pp"] = fit["model"]["sbp_mmhg"] - fit["model"]["dbp_mmhg"]
    return {"kind": kind, "caseid": cid, "variant": name, "measured_pp": obs["sbp_mmhg"] - obs["dbp_mmhg"], **keep}


def main():
    table = json.loads((TEST / "per_case_primary.json").read_text())
    good = [r["caseid"] for r in table if r["caseid"] not in DEGENERATE]
    subset = good[::4][:12]
    jobs = [("A", c, "12 starts") for c in DEGENERATE] + [("B", c, v) for c in subset for v in VARIANTS]
    with mp.Pool(12, maxtasksperchild=1) as pool:
        res = pool.map(job, jobs, chunksize=1)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "refits.json").write_text(json.dumps({"subset": subset, "results": res}, indent=1))
    print("done", len(res))


if __name__ == "__main__":
    main()
