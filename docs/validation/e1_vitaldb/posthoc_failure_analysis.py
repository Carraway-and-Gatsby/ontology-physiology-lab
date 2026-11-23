"""Post hoc failure analysis of E1 (not registered). Reads only saved features, fits and the post hoc refits.

    PYTHONPATH=src:. python docs/validation/e1_vitaldb/posthoc_failure_analysis.py
Run posthoc_refits.py, posthoc_degenerate_starts.py and posthoc_realign.py first.
Writes results/e1_vitaldb/posthoc_failure_analysis/summary.json
"""
import json
from pathlib import Path

import numpy as np
from scipy.stats import pearsonr, spearmanr

from experiments.e1_vitaldb import anchor

REPO = Path(__file__).resolve().parents[3]
TEST = REPO / "results" / "e1_vitaldb" / "test"
OUT = REPO / "results" / "e1_vitaldb" / "posthoc_failure_analysis"
C_REF = 1.5


def load():
    table = json.loads((TEST / "per_case_primary.json").read_text())
    equal = {r["caseid"]: r for r in json.loads((TEST / "per_case_equal.json").read_text())}
    realigned = {r["caseid"]: r for r in json.loads((OUT / "realigned.json").read_text())["refits"]}
    rows = []
    for r in table:
        cid = r["caseid"]
        wins = json.loads((TEST / "features" / f"{cid:04d}.json").read_text())["windows"]
        w = wins[0]
        f = json.loads((TEST / "fits" / f"{cid:04d}_w1.json").read_text())
        ens = np.array(w["ensemble"])
        pp = w["sbp_mmhg"] - w["dbp_mmhg"]
        row = dict(cid=cid, co=r["co_ref"], x=r["flow_index"], x_equal=equal[cid]["flow_index"], lz=r["lz"], age=r["age"],
                   bsa=r["bsa"], hr=w["heart_rate_bpm"], map=w["map_mmhg"], pp=pp, cvp=w["cvp_mmhg"], mpap=w["mpap_mmhg"],
                   peak_phase=float(np.argmax(ens) / len(ens)), rmse=f["rmse_waveform_mmhg"], bound=bool(f["at_bound"]),
                   flat=(f["model"]["sbp_mmhg"] - f["model"]["dbp_mmhg"]) < 0.5 * pp, pred=r["MODEL"],
                   x_fixed=float(realigned[cid]["flow_index_l_min"]) if cid in realigned else r["flow_index"],
                   residual=((np.array(f["model"]["ensemble"]) - ens) / pp).tolist(), params=f["parameters"])
        if len(wins) > 1:
            w2 = wins[1]
            f2 = json.loads((TEST / "fits" / f"{cid:04d}_w2.json").read_text())
            pp2 = w2["sbp_mmhg"] - w2["dbp_mmhg"]
            row["second"] = dict(co=w2["co_ref_l_min"], x=f2["flow_index_l_min"], hr=w2["heart_rate_bpm"], map=w2["map_mmhg"],
                                 pp=pp2, lz=w2["heart_rate_bpm"] * pp2 / (w2["sbp_mmhg"] + w2["dbp_mmhg"]),
                                 flat=(f2["model"]["sbp_mmhg"] - f2["model"]["dbp_mmhg"]) < 0.5 * pp2,
                                 peak_phase=float(np.argmax(w2["ensemble"]) / len(w2["ensemble"])))
        rows.append(row)
    return rows


def loso(X, y):
    pred = np.zeros(len(y))
    for i in range(len(y)):
        m = np.ones(len(y), bool); m[i] = False
        b, *_ = np.linalg.lstsq(X[m], y[m], rcond=None)
        pred[i] = X[i] @ b
    return pred


def main():
    rows = load()
    out = {"n": len(rows)}
    A = lambda k, rs: np.array([r[k] for r in rs], dtype=float)
    flat = [r for r in rows if r["flat"]]
    good = [r for r in rows if not r["flat"]]
    out["flat_fits"] = [dict(cid=r["cid"], hr=r["hr"], peak_phase=r["peak_phase"], x=r["x"], x_after_realignment=r["x_fixed"],
                             co=r["co"]) for r in flat]
    out["peak_phase_other_cases"] = [float(A("peak_phase", good).min()), float(A("peak_phase", good).max())]

    # registered estimators, alignment corrected in the five windows
    rr = [dict(subject=r["cid"], co_ref=r["co"], flow_index=r["x_fixed"], lz=r["lz"], bsa=r["bsa"], age=r["age"]) for r in rows]
    res = anchor.evaluate(rr)
    out["after_realignment"] = {e: {k: s[k] for k in ("percentage_error", "pe_ci95", "bias_l_min") if k in s} |
                                ({"model_minus_this_pe_ci95": s["model_minus_this_pe_ci95"]} if "model_minus_this_pe_ci95" in s else {})
                                for e, s in res["estimators"].items()}
    out["after_realignment"]["label"] = res["verdict_model"]["label"]

    # what the flow index is, and the between-subject scale (alignment-corrected, all 51)
    co, x = A("co", rows), A("x_fixed", rows)
    k = co / x
    x_pp = C_REF * A("pp", rows) * A("hr", rows) / 1000.0
    out["index"] = {
        "r_log_x_vs_log_cref_pp_hr": float(pearsonr(np.log(x), np.log(x_pp))[0]),
        "median_x_over_cref_pp_hr": float(np.median(x / x_pp)),
        "spearman_with_co": {n: float(spearmanr(co, v)[0]) for n, v in
                             (("x", x), ("pp_hr", x_pp), ("lz", A("lz", rows)), ("hr", A("hr", rows)), ("pp", A("pp", rows)),
                              ("map", A("map", rows)), ("age", A("age", rows)), ("bsa", A("bsa", rows)))},
        "r_log_x_log_co": float(pearsonr(np.log(x), np.log(co))[0]),
        "sd_log_co": float(np.log(co).std(ddof=1)), "sd_log_x": float(np.log(x).std(ddof=1)),
        "sd_log_k": float(np.log(k).std(ddof=1)), "k_min": float(k.min()), "k_max": float(k.max()),
        "k_quartiles": [float(v) for v in np.percentile(k, [25, 50, 75])],
        "spearman_k": {n: float(spearmanr(k, A(n, rows))[0]) for n in ("age", "bsa", "map", "pp", "hr", "cvp", "mpap")},
        "x_primary_vs_equal_weights_median_abs_diff": float(np.median(np.abs(A("x_equal", good) / A("x", good) - 1))),
    }

    # exploratory leave-one-out models (alignment-corrected, 51 cases)
    y = np.log(co); one = np.ones(len(co)); lb = np.log(A("bsa", rows) / 1.73); ag = (A("age", rows) - 60) / 10
    pe = lambda p: float(100 * 1.96 * (np.exp(p) - co).std(ddof=1) / co.mean())
    models = {
        "mean only": (one[:, None], 0.0),
        "bsa, age": (np.column_stack([one, lb, ag]), 0.0),
        "registered form: offset log X + bsa, age": (np.column_stack([one, lb, ag]), np.log(x)),
        "free exponent on X + bsa, age": (np.column_stack([one, lb, ag, np.log(x)]), 0.0),
        "offset log X, scale ~ bsa, age, log PP": (np.column_stack([one, lb, ag, np.log(A("pp", rows))]), np.log(x)),
        "offset log X, scale ~ bsa, age, log MAP": (np.column_stack([one, lb, ag, np.log(A("map", rows))]), np.log(x)),
        "no model: bsa, age, log HR, log PP, log MAP": (np.column_stack([one, lb, ag, np.log(A("hr", rows)), np.log(A("pp", rows)), np.log(A("map", rows))]), 0.0),
    }
    out["exploratory_loso"] = {}
    for name, (X, off) in models.items():
        off = np.zeros(len(co)) + off
        b, *_ = np.linalg.lstsq(X, y - off, rcond=None)
        out["exploratory_loso"][name] = {"pe": pe(loso(X, y - off) + off), "coefficients": [float(v) for v in b]}

    # within-subject change between the two windows (the subject's scale cancels)
    pairs = [r for r in rows if "second" in r and not r["flat"] and not r["second"]["flat"]]
    d = lambda a, b: np.log(np.array([r["second"][b] for r in pairs]) / np.array([r[a] for r in pairs]))
    dco = d("co", "co")
    idx = {"x": d("x", "x"), "lz": d("lz", "lz"), "hr": d("hr", "hr"), "map": d("map", "map"),
           "pp_hr": np.log(np.array([r["second"]["pp"] * r["second"]["hr"] for r in pairs]) / np.array([r["pp"] * r["hr"] for r in pairs]))}
    big = np.abs(dco) > np.log(1.10)
    out["within_subject"] = {"n_pairs": len(pairs), "n_change_over_10_percent": int(big.sum()), "sd_dlog_co": float(dco.std(ddof=1))}
    for name, v in idx.items():
        out["within_subject"][name] = {"r": float(pearsonr(v, dco)[0]), "spearman": float(spearmanr(v, dco)[0]),
                                       "direction_agreement": float(np.mean(np.sign(v[big]) == np.sign(dco[big]))),
                                       "slope": float(np.polyfit(v, dco, 1)[0]), "sd_dlog_index": float(v.std(ddof=1)),
                                       "sd_of_dco_minus_dindex": float((dco - v).std(ddof=1))}

    # waveform misfit and fitted parameters (non-flat fits)
    resid = np.array([r["residual"] for r in good])
    out["waveform"] = {"mean_residual_percent_of_pp_every_10_percent_of_cycle": [float(v) for v in 100 * resid.mean(0)[::5]],
                       "sd": [float(v) for v in 100 * resid.std(0, ddof=1)[::5]],
                       "spearman_abs_rel_error_vs_rmse": float(spearmanr(np.abs(A("pred", good) - A("co", good)) / A("co", good), A("rmse", good))[0])}
    out["fitted_parameters_median_iqr"] = {n: [float(v) for v in np.percentile([r["params"][n] for r in good], [50, 25, 75])]
                                           for n in good[0]["params"]}

    # refits: more starts, pulsatile starts, fixed-parameter sensitivity
    ref = json.loads((OUT / "refits.json").read_text())
    base = {r["cid"]: r["x"] for r in rows}
    out["flat_fits_12_starts"] = [dict(cid=r["caseid"], x=r["flow_index_l_min"], cost=r["cost"], model_pp=r["model_pp"],
                                       measured_pp=r["measured_pp"]) for r in ref["results"] if r["kind"] == "A"]
    sens = {}
    for r in ref["results"]:
        if r["kind"] == "B":
            sens.setdefault(r["variant"], []).append(r["flow_index_l_min"] / base[r["caseid"]] - 1)
    out["fixed_parameter_sensitivity"] = {v: {"median_change": float(np.median(a)), "median_abs_change": float(np.median(np.abs(a))),
                                              "min": float(np.min(a)), "max": float(np.max(a)), "n": len(a)} for v, a in sens.items()}
    ds = json.loads((OUT / "degenerate_starts.json").read_text())
    out["flat_fits_pulsatile_starts"] = [dict(cid=r["caseid"], donor=r["donor"], start_cost=r["start_cost"], cost=r["cost"],
                                              x=r["flow_index_l_min"], model_pp=r["model_pp"]) for r in ds["results"]]
    (OUT / "summary.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("after_realignment", "index", "exploratory_loso", "within_subject", "waveform",
                                           "fitted_parameters_median_iqr", "fixed_parameter_sensitivity", "peak_phase_other_cases")}, indent=1))


if __name__ == "__main__":
    main()
