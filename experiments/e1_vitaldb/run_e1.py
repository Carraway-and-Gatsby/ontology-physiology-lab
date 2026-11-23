"""E1 driver: download, inventory, features, fit, score. See docs/validation/e1_vitaldb/PREREGISTRATION_E1.md.

    python -m experiments.e1_vitaldb.run_e1 <step> --set dev|test [options]

Recordings come only from https://physionet.org/files/vitaldb/1.0.0/ and are stored outside the repository
(E1_DATA_DIR). The test set is refused unless the working tree of the experiment is clean and HEAD equals
--freeze-commit.
"""
import argparse
import csv
import hashlib
import json
import multiprocessing as mp
import os
from pathlib import Path
import subprocess
import urllib.request

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DOCS = REPO / "docs" / "validation" / "e1_vitaldb"
DATA = Path(os.environ.get("E1_DATA_DIR", "<local path>")) / "physionet_vitaldb_1.0.0"
BASE_URL = "https://physionet.org/files/vitaldb/1.0.0/"


def case_ids(which: str) -> list[int]:
    lists = json.loads((DOCS / "case_lists.json").read_text())
    return {"test": lists["test"], "dev": sorted(lists["dev_pressure"] + lists["dev_co"])}[which]


def guard(args):
    if args.set != "test":
        return
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--", "experiments/e1_vitaldb", "docs/validation/e1_vitaldb"],
                           cwd=REPO, capture_output=True, text=True).stdout.strip()
    if not args.freeze_commit or not head.startswith(args.freeze_commit) or dirty:
        raise SystemExit("test set refused: need --freeze-commit equal to HEAD and a clean experiment tree")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def step_download(args):
    sums = {}
    for line in (DATA / "SHA256SUMS.txt").read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        sums[name.strip()] = digest
    names = ["clinical_data.csv"] + [f"vital_files/{c:04d}.vital" for c in case_ids(args.set)]
    log = []
    for name in names:
        dest = DATA / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            req = urllib.request.Request(BASE_URL + name, headers={"User-Agent": "research-client"})
            with urllib.request.urlopen(req, timeout=600) as r, open(dest, "wb") as f:
                while chunk := r.read(1 << 20):
                    f.write(chunk)
        ok = sha256(dest) == sums[name]
        log.append({"file": name, "bytes": dest.stat().st_size, "sha256_ok": ok})
        if not ok:
            raise SystemExit(f"checksum mismatch: {name}")
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    (out / f"download_{args.set}.json").write_text(json.dumps({"source": BASE_URL, "files": log}, indent=1))
    print(len(log), "files,", round(sum(x["bytes"] for x in log) / 1e9, 3), "GB, all checksums match")


def clinical() -> dict:
    rows = {}
    with open(DATA / "clinical_data.csv", newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            rows[int(r["caseid"])] = r
    return rows


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _features_one(job):
    cid, t_min, t_max, dev, full_acceptance = job
    from . import signals, vital_io
    path = DATA / "vital_files" / f"{cid:04d}.vital"
    require_co = not dev
    rule = dict(signals.RULE, require_co=require_co, hr_bins_full_acceptance=full_acceptance)
    try:
        required = ("cvp", "mpap", "co") if require_co else ("cvp", "mpap")
        sig, why = vital_io.load_case(path, t_min, t_max, required, dev_co_standin=dev)
        if sig is None:
            return cid, {"caseid": cid, "loaded": False, "reason": why}
        res = signals.select_windows(sig, rule)
        res.update({"caseid": cid, "loaded": True, "tracks_numeric": sorted(sig.numerics),
                    "infusion_tracks": sorted(sig.infusions), "require_co": require_co, "dev_co_standin": dev,
                    "hr_bins_full_acceptance": full_acceptance})
        return cid, res
    except Exception as exc:  # recorded per case, never silently dropped
        return cid, {"caseid": cid, "loaded": False, "reason": f"error: {type(exc).__name__}: {exc}"}


def step_features(args):
    guard(args)
    clin = clinical()
    lists = json.loads((DOCS / "case_lists.json").read_text())
    jobs = []
    for cid in case_ids(args.set):
        r = clin[cid]
        jobs.append((cid, _num(r["opstart"]) or 0.0, _num(r["opend"]) or float("inf"), args.set == "dev",
                     args.posthoc_full_acceptance))
    out = Path(args.out) / "features"; out.mkdir(parents=True, exist_ok=True)
    with mp.Pool(args.workers) as pool:
        for cid, res in pool.imap_unordered(_features_one, jobs):
            (out / f"{cid:04d}.json").write_text(json.dumps(res, indent=1))
            print(cid, "windows:", len(res.get("windows", [])), res.get("reason", ""), flush=True)


def _fit_one(job):
    cid, w, obs, weights = job
    from . import calibrate
    try:
        fit = calibrate.fit_window(obs, calibrate.EQUAL_WEIGHTS if weights == "equal" else calibrate.WEIGHTS)
    except Exception as exc:
        fit = {"ok": False, "reason": f"error: {type(exc).__name__}: {exc}"}
    return cid, w, fit


def step_fit(args):
    guard(args)
    feats = Path(args.out) / "features"
    out = Path(args.out) / ("fits" if args.weights == "primary" else "fits_equal_weights"); out.mkdir(parents=True, exist_ok=True)
    jobs = []
    for f in sorted(feats.glob("*.json")):
        d = json.loads(f.read_text())
        for w, win in enumerate(d.get("windows", []), start=1):
            if not (out / f"{d['caseid']:04d}_w{w}.json").exists():
                jobs.append((d["caseid"], w, win, args.weights))
    with mp.Pool(args.workers) as pool:
        for cid, w, fit in pool.imap_unordered(_fit_one, jobs):
            (out / f"{cid:04d}_w{w}.json").write_text(json.dumps(fit, indent=1))
            print(cid, w, "ok" if fit.get("ok") else fit.get("reason"), fit.get("flow_index_l_min"), flush=True)


def _rows(out: Path, fits_dir: str, window: int, clin: dict):
    from . import anchor
    rows, excluded = [], []
    for f in sorted((out / "features").glob("*.json")):
        d = json.loads(f.read_text())
        cid = d["caseid"]
        if not d.get("loaded"):
            excluded.append({"caseid": cid, "reason": d.get("reason")}); continue
        if len(d["windows"]) < window:
            excluded.append({"caseid": cid, "reason": "no qualifying window" if window == 1 else "no second window",
                             "rejections": d.get("rejections")}); continue
        win = d["windows"][window - 1]
        fp = out / fits_dir / f"{cid:04d}_w{window}.json"
        fit = json.loads(fp.read_text()) if fp.exists() else {"ok": False, "reason": "fit not run"}
        if not fit.get("ok"):
            excluded.append({"caseid": cid, "reason": "fit failed: " + str(fit.get("reason"))}); continue
        if fit["numerical_relative_difference_co"] >= 0.02:
            excluded.append({"caseid": cid, "reason": "inconclusive: numerical difference of CO >= 2 %"}); continue
        c = clin[cid]
        age, h, wt = _num(c["age"]), _num(c["height"]), _num(c["weight"])
        if win.get("co_ref_l_min") is None or None in (age, h, wt):
            excluded.append({"caseid": cid, "reason": "missing reference CO, age, height or weight"}); continue
        pp = win["sbp_mmhg"] - win["dbp_mmhg"]
        rows.append({"caseid": cid, "subject": c["subjectid"], "co_ref": win["co_ref_l_min"],
                     "flow_index": fit["flow_index_l_min"], "lz": win["heart_rate_bpm"] * pp / (win["sbp_mmhg"] + win["dbp_mmhg"]),
                     "bsa": anchor.bsa_du_bois(h, wt), "age": age, "sex": c.get("sex"), "window": win, "fit": fit})
    return rows, excluded


def step_score(args):
    guard(args)
    from . import anchor
    out = Path(args.out)
    clin = clinical()
    fits_dir = "fits" if args.weights == "primary" else "fits_equal_weights"
    rows, excluded = _rows(out, fits_dir, 1, clin)
    report = {"set": args.set, "weights": args.weights, "n_cases_listed": len(case_ids(args.set)),
              "n_scored": len(rows), "excluded": excluded}
    if len(rows) >= 8:
        res = anchor.evaluate(rows)
        report["primary"] = {k: v for k, v in res.items() if k != "predictions"}
        pred = np.array(res["predictions"]["MODEL"])
        k = pred / np.array([r["flow_index"] for r in rows])
        diag = {}
        for name, mk, wk in (("map", "map_mmhg", "map_mmhg"), ("sbp", "sbp_mmhg", "sbp_mmhg"), ("dbp", "dbp_mmhg", "dbp_mmhg"),
                             ("cvp", "cvp_mmhg", "cvp_mmhg"), ("mpap", "mpap_mmhg", "mpap_mmhg")):
            d = np.array([r["fit"]["model"][mk] - r["window"][wk] for r in rows])
            diag[name] = {"bias_mmhg": float(d.mean()), "sd_mmhg": float(d.std(ddof=1)), "mae_mmhg": float(np.abs(d).mean())}
        diag["waveform_rmse_mmhg_median"] = float(np.median([r["fit"]["rmse_waveform_mmhg"] for r in rows]))
        diag["fits_at_bound"] = int(sum(bool(r["fit"]["at_bound"]) for r in rows))
        report["fit_diagnostics_report_only"] = diag
        rv = {}
        for key, mk in (("rv_edv", "rv_edv_ml"), ("rv_esv", "rv_esv_ml")):
            pairs = [(ki * r["fit"]["model"][mk], r["window"].get(key)) for ki, r in zip(k, rows) if r["window"].get(key)]
            if pairs:
                d = np.array([a - b for a, b in pairs])
                rv[key] = {"n": len(pairs), "bias_ml": float(d.mean()), "sd_ml": float(d.std(ddof=1)) if len(d) > 1 else None,
                           "mae_ml": float(np.abs(d).mean()), "mean_ref_ml": float(np.mean([b for _, b in pairs]))}
        pairs = [(100.0 * (r["fit"]["model"]["rv_edv_ml"] - r["fit"]["model"]["rv_esv_ml"]) / r["fit"]["model"]["rv_edv_ml"],
                  r["window"].get("rvef")) for r in rows if r["window"].get("rvef")]
        if pairs:
            d = np.array([a - b for a, b in pairs])
            rv["rvef_percent"] = {"n": len(pairs), "bias": float(d.mean()), "sd": float(d.std(ddof=1)) if len(d) > 1 else None,
                                  "mae": float(np.abs(d).mean()), "mean_ref": float(np.mean([b for _, b in pairs]))}
        report["rv_volumetrics_report_only"] = rv
        rows2, _ = _rows(out, fits_dir, 2, clin)
        rep = []
        for r2 in rows2:
            train = [r for r in rows if r["subject"] != r2["subject"]]
            first = [(r, p) for r, p in zip(rows, pred) if r["caseid"] == r2["caseid"]]
            if first and len(train) > 3:
                p2 = float(anchor.fit_predict(train, [r2], "MODEL")[0])
                r1, p1 = first[0]
                rep.append({"caseid": r2["caseid"], "error_w1_l_min": float(p1 - r1["co_ref"]), "error_w2_l_min": p2 - r2["co_ref"],
                            "co_ref_w1": r1["co_ref"], "co_ref_w2": r2["co_ref"]})
        if rep:
            d = np.array([x["error_w2_l_min"] - x["error_w1_l_min"] for x in rep])
            report["reproducibility_w2_report_only"] = {
                "n": len(rep), "mean_change_of_error_l_min": float(d.mean()), "sd_change_of_error_l_min": float(d.std(ddof=1)) if len(d) > 1 else None,
                "pe_w2": anchor.agreement(np.array([x["error_w2_l_min"] + x["co_ref_w2"] for x in rep]), np.array([x["co_ref_w2"] for x in rep]))["percentage_error"]}
        table = [{"caseid": r["caseid"], "co_ref": r["co_ref"], "flow_index": r["flow_index"], "lz": r["lz"], "bsa": r["bsa"], "age": r["age"],
                  **{e: res["predictions"][e][i] for e in anchor.ESTIMATORS}} for i, r in enumerate(rows)]
        (out / f"per_case_{args.weights}.json").write_text(json.dumps(table, indent=1))
    else:
        report["primary"] = None
        report["note"] = "fewer than 8 scored cases: no agreement statistics"
    (out / f"score_{args.weights}.json").write_text(json.dumps(report, indent=1))
    print(json.dumps({k: v for k, v in report.items() if k != "excluded"}, indent=1)[:6000])
    print("excluded:", len(excluded))


def step_inventory(args):
    from . import vital_io
    lists = json.loads((DOCS / "case_lists.json").read_text())
    need = lists["eligibility_tracks"]
    out = {}
    for cid in case_ids(args.set):
        names = vital_io.track_inventory(DATA / "vital_files" / f"{cid:04d}.vital")
        out[cid] = {t: (t in names) for t in need + ["SNUADC/CVP", "Vigilance/EDV", "Vigilance/ESV", "Vigilance/RVEF"]}
    Path(args.out).mkdir(parents=True, exist_ok=True)
    (Path(args.out) / f"inventory_{args.set}.json").write_text(json.dumps(out, indent=1))
    miss = {c: [t for t in need if not v[t]] for c, v in out.items() if not all(v[t] for t in need)}
    print("cases:", len(out), "| cases missing an eligibility track according to the PhysioNet file:", miss)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["download", "inventory", "features", "fit", "score"])
    ap.add_argument("--set", choices=["dev", "test"], required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--weights", choices=["primary", "equal"], default="primary")
    ap.add_argument("--freeze-commit", default=None)
    ap.add_argument("--posthoc-full-acceptance", action="store_true",
                    help="post hoc variant of the window rule (features step); never the registered analysis")
    args = ap.parse_args()
    if args.out is None:
        args.out = str(REPO / "results" / "e1_vitaldb" / (args.set + ("_posthoc_full_acceptance" if args.posthoc_full_acceptance else "")))
    {"download": step_download, "inventory": step_inventory, "features": step_features, "fit": step_fit,
     "score": step_score}[args.step](args)


if __name__ == "__main__":
    main()
