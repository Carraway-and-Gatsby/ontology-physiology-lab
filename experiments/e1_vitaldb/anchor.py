"""Flow-scale anchor learned from other subjects (leave-one-subject-out) and agreement statistics (E1).

Each row is one case-window: subject, co_ref (L/min), flow_index (model CO at the reference scale, L/min),
lz (Liljestrand-Zander pressure index HR * PP / (SBP + DBP)), bsa (m2), age (years).
All four estimators are linear regressions of log(co_ref) with the same covariates; they differ only in the offset:
  MODEL  offset log(flow_index)      (the physics model supplies the subject's flow index)
  B2     offset log(lz)              (pulse-pressure index, no model)
  B1     no offset                   (body size and age only)
  B0     intercept only              (mean of the other subjects)
"""
import numpy as np

ESTIMATORS = ("MODEL", "B2", "B1", "B0")
REFERENCE_PRECISION = 0.20   # thermodilution, Critchley and Critchley 1999
PE_LIMIT = 30.0              # percent, Critchley and Critchley 1999
BOOTSTRAP = 10000
BOOT_SEED = 20261123


def bsa_du_bois(height_cm: float, weight_kg: float) -> float:
    return 0.007184 * weight_kg ** 0.425 * height_cm ** 0.725


def _design(rows, estimator):
    n = len(rows)
    ones = np.ones(n)
    cov = np.column_stack([ones, np.log(np.array([r["bsa"] for r in rows]) / 1.73),
                           (np.array([r["age"] for r in rows]) - 60.0) / 10.0])
    if estimator == "B0":
        return ones[:, None], np.zeros(n)
    if estimator == "B1":
        return cov, np.zeros(n)
    key = "flow_index" if estimator == "MODEL" else "lz"
    return cov, np.log(np.array([r[key] for r in rows], dtype=float))


def loso_predictions(rows: list, estimator: str) -> np.ndarray:
    """Predicted CO for every row, each from a fit that excludes all rows of the same subject."""
    if estimator not in ESTIMATORS:
        raise ValueError(estimator)
    x, offset = _design(rows, estimator)
    y = np.log(np.array([r["co_ref"] for r in rows], dtype=float))
    subjects = np.array([r["subject"] for r in rows])
    pred = np.full(len(rows), np.nan)
    for s in np.unique(subjects):
        test = subjects == s
        train = ~test
        if train.sum() <= x.shape[1]:
            raise ValueError("too few training rows")
        beta, *_ = np.linalg.lstsq(x[train], (y - offset)[train], rcond=None)
        pred[test] = np.exp(offset[test] + x[test] @ beta)
    return pred


def fit_predict(train: list, test: list, estimator: str) -> np.ndarray:
    """Predictions for `test` rows from a fit on `train` rows (caller guarantees disjoint subjects)."""
    x, offset = _design(train, estimator)
    y = np.log(np.array([r["co_ref"] for r in train], dtype=float))
    beta, *_ = np.linalg.lstsq(x, y - offset, rcond=None)
    xt, ot = _design(test, estimator)
    return np.exp(ot + xt @ beta)


def agreement(pred: np.ndarray, ref: np.ndarray) -> dict:
    """Bland-Altman bias and limits, and the percentage error of Critchley and Critchley (1.96 SD / mean reference)."""
    d = np.asarray(pred, float) - np.asarray(ref, float)
    bias, sd = float(d.mean()), float(d.std(ddof=1))
    mean_ref = float(np.mean(ref))
    return {"n": int(len(d)), "bias_l_min": bias, "sd_l_min": sd, "loa_low_l_min": bias - 1.96 * sd,
            "loa_high_l_min": bias + 1.96 * sd, "mean_ref_l_min": mean_ref,
            "percentage_error": 100.0 * 1.96 * sd / mean_ref,
            "bias_ci95_l_min": [bias - 1.96 * sd / np.sqrt(len(d)), bias + 1.96 * sd / np.sqrt(len(d))],
            "mean_abs_relative_error": float(np.mean(np.abs(d) / np.asarray(ref, float)))}


def bootstrap(rows: list, preds: dict, n_boot: int = BOOTSTRAP, seed: int = BOOT_SEED) -> dict:
    """Subject-cluster percentile bootstrap of the percentage error and of its difference to each baseline.

    Predictions are held fixed (the leave-one-subject-out fits are not repeated inside the bootstrap)."""
    ref = np.array([r["co_ref"] for r in rows], dtype=float)
    subjects = np.array([r["subject"] for r in rows])
    uniq = np.unique(subjects)
    groups = [np.where(subjects == s)[0] for s in uniq]
    rng = np.random.default_rng(seed)
    pe = {k: [] for k in preds}
    for _ in range(n_boot):
        idx = np.concatenate([groups[j] for j in rng.integers(0, len(groups), len(groups))])
        for k, p in preds.items():
            d = p[idx] - ref[idx]
            pe[k].append(100.0 * 1.96 * d.std(ddof=1) / ref[idx].mean())
    pe = {k: np.array(v) for k, v in pe.items()}
    out = {k: {"pe_ci95": [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]} for k, v in pe.items()}
    for k in preds:
        if k != "MODEL" and "MODEL" in preds:
            diff = pe["MODEL"] - pe[k]
            out[k]["model_minus_this_pe_ci95"] = [float(np.percentile(diff, 2.5)), float(np.percentile(diff, 97.5))]
    return out


def verdict(stats: dict) -> dict:
    """Pre-registered reading of the primary result (methodology v1 sections 6.A and 8)."""
    pe = stats["percentage_error"]
    lo, hi = stats["bias_ci95_l_min"]
    bias_fails = (lo > 0 or hi < 0) and abs(stats["bias_l_min"]) > REFERENCE_PRECISION * stats["mean_ref_l_min"]
    return {"pe_within_limit": bool(pe <= PE_LIMIT), "bias_failure": bool(bias_fails),
            "accepted": bool(pe <= PE_LIMIT and not bias_fails)}


def evaluate(rows: list, n_boot: int = BOOTSTRAP, seed: int = BOOT_SEED) -> dict:
    ref = np.array([r["co_ref"] for r in rows], dtype=float)
    preds = {e: loso_predictions(rows, e) for e in ESTIMATORS}
    stats = {e: agreement(p, ref) for e, p in preds.items()}
    boot = bootstrap(rows, preds, n_boot, seed)
    for e in ESTIMATORS:
        stats[e].update(boot[e])
    v = verdict(stats["MODEL"])
    gain = stats["B2"]["model_minus_this_pe_ci95"][1] < 0.0
    v["adds_information_over_b2"] = bool(gain)
    v["label"] = "NOT SUPPORTED" if not v["accepted"] else ("SUPPORTED" if gain else "INCONCLUSIVE")
    return {"n_rows": len(rows), "n_subjects": int(len({r["subject"] for r in rows})), "estimators": stats,
            "verdict_model": v,
            "predictions": {e: p.tolist() for e, p in preds.items()}}
