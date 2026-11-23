"""Synthetic-data tests of the E1 pipeline (no dataset). Run from the repository root:

    PYTHONPATH=src:. python -m pytest -q -p no:cacheprovider experiments/e1_vitaldb/tests

Passing these tests shows that the code does what the pre-registration says on model-generated signals. It is not
evidence about real recordings and not validation of the model.
"""
from dataclasses import replace

import numpy as np
import pytest

from experiments.e1_vitaldb import anchor, signals
from experiments.e1_vitaldb.calibrate import REFERENCE, fit_window, model_features
from experiments.e1_vitaldb.steady import periodic_beat

FS = 500.0


def scaled_subject(k, mult=None, sf=None, stressed=1.0, hr=75.0):
    """A subject at flow scale k whose scale-free parameters differ from the reference by `mult`."""
    p, mult = REFERENCE, dict(mult or {})
    v0, vi = np.array(p.unstressed_volumes), np.array(p.initial_volumes)
    g = lambda n: mult.get(n, 1.0)
    return replace(
        p, heart_rate=hr, systolic_fraction=sf or p.systolic_fraction,
        emin_lv=p.emin_lv / k, emax_lv=p.emax_lv * g("emax_lv") / k, emin_rv=p.emin_rv * g("emin_rv") / k,
        emax_rv=p.emax_rv / k, compliance_sa=p.compliance_sa * k, compliance_sv=p.compliance_sv * k,
        compliance_pa=p.compliance_pa * k, compliance_pv=p.compliance_pv * k,
        resistance_aortic=p.resistance_aortic / k, resistance_systemic=p.resistance_systemic * g("resistance_systemic") / k,
        resistance_tricuspid=p.resistance_tricuspid / k, resistance_pulmonary_valve=p.resistance_pulmonary_valve / k,
        resistance_pulmonary=p.resistance_pulmonary * g("resistance_pulmonary") / k,
        resistance_mitral=p.resistance_mitral / k, initial_volumes=tuple(v0 + k * stressed * (vi - v0)))


def synthetic_art(beat_shape, period, seconds, rng, jitter=0.02, resp=2.0, noise=0.3):
    """Concatenate beats (foot first) with period jitter, respiratory baseline and white noise at 500 Hz."""
    out, t = [], 0.0
    while t < seconds:
        ti = period * (1.0 + rng.uniform(-jitter, jitter))
        n = int(round(ti * FS))
        out.append(np.interp(np.arange(n) * (len(beat_shape) / n), np.arange(len(beat_shape) + 1),
                             np.append(beat_shape, beat_shape[0])))
        t += n / FS
    x = np.concatenate(out)[: int(seconds * FS)]
    time = np.arange(len(x)) / FS
    return x + resp * np.sin(2 * np.pi * 0.2 * time) + rng.normal(0.0, noise, len(x))


@pytest.fixture(scope="module")
def reference_beat():
    beat = periodic_beat(replace(REFERENCE, resistance_systemic=0.7))
    return beat, model_features(beat, 200, lowpass_hz=None)["ensemble"], model_features(beat)


def test_flow_scaling_leaves_every_pressure_feature_unchanged():
    a = model_features(periodic_beat(scaled_subject(1.0)))
    b = model_features(periodic_beat(scaled_subject(0.6)))
    assert np.max(np.abs(a["ensemble"] - b["ensemble"])) < 1e-3
    assert abs(a["cvp_mmhg"] - b["cvp_mmhg"]) < 1e-3 and abs(a["mpap_mmhg"] - b["mpap_mmhg"]) < 1e-3
    assert b["co_l_min"] == pytest.approx(0.6 * a["co_l_min"], rel=1e-4)


def test_beat_detection_recovers_rate_mean_and_shape(reference_beat):
    beat, shape200, feat = reference_beat
    rng = np.random.default_rng(7)
    art = synthetic_art(shape200, REFERENCE.period, 180.0, rng)
    beats = signals.detect_beats(art, FS)
    out = signals.segment_features(beats, 30.0, 150.0)
    assert out["accept_fraction"] > 0.95
    assert out["heart_rate_bpm"] == pytest.approx(REFERENCE.heart_rate, rel=0.01)
    assert out["map_mmhg"] == pytest.approx(feat["map_mmhg"], abs=0.5)
    assert np.sqrt(np.mean((np.array(out["ensemble"]) - feat["ensemble"]) ** 2)) < 1.5
    assert out["sbp_mmhg"] == pytest.approx(feat["sbp_mmhg"], abs=2.0)
    assert out["dbp_mmhg"] == pytest.approx(feat["dbp_mmhg"], abs=2.0)


def test_flush_gap_and_damped_beats_are_rejected(reference_beat):
    beat, shape200, feat = reference_beat
    rng = np.random.default_rng(8)
    art = synthetic_art(shape200, REFERENCE.period, 180.0, rng)
    art[int(60 * FS):int(63 * FS)] = 300.0                     # flush
    art[int(90 * FS):int(92 * FS)] = np.nan                    # gap
    seg = slice(int(110 * FS), int(118 * FS))
    art[seg] = art[seg].mean() + 0.2 * (art[seg] - art[seg].mean())   # damped line
    beats = signals.detect_beats(art, FS)
    out = signals.segment_features(beats, 30.0, 150.0)
    assert 0.80 < out["accept_fraction"] < 0.97
    assert out["heart_rate_bpm"] == pytest.approx(REFERENCE.heart_rate, rel=0.01)
    assert out["map_mmhg"] == pytest.approx(feat["map_mmhg"], abs=0.7)
    assert out["sbp_mmhg"] < 200.0


def _case(reference_beat, minutes=80.0):
    beat, shape200, feat = reference_beat
    rng = np.random.default_rng(9)
    seconds = minutes * 60.0
    art = synthetic_art(shape200, REFERENCE.period, seconds, rng)
    t2 = np.arange(0.0, seconds, 2.0)
    tco = np.arange(0.0, seconds, 30.0)
    co = np.where(tco < 900.0, 4.0 + 2.0 * tco / 900.0, 6.0)   # drifting for 15 min, then constant
    sig = signals.CaseSignals(
        art=art,
        numerics={"cvp": (t2, np.full(len(t2), 6.0)), "mpap": (t2, np.full(len(t2), 20.0)), "co": (tco, co)},
        infusions={"Orchestra/PHEN_RATE": (np.array([0.0, 1500.0]), np.array([10.0, 20.0]))},
        t_min=300.0, t_max=seconds - 120.0)
    return sig, feat


def test_window_rule_skips_drift_and_infusion_change_and_spaces_the_second_window(reference_beat):
    sig, feat = _case(reference_beat)
    res = signals.select_windows(sig)
    assert len(res["windows"]) == 2
    w1, w2 = res["windows"]
    # CO is not stationary until 900 s; the infusion rate changes at 1500 s, so no window may contain 1440..1500 s
    assert w1["window_start_s"] >= 1500.0 or w1["window_end_s"] <= 1500.0
    assert w1["window_start_s"] >= 300.0
    assert w2["window_start_s"] >= w1["window_end_s"] + 1800.0
    assert w1["co_ref_l_min"] == pytest.approx(6.0, rel=0.1)
    assert w1["cvp_mmhg"] == pytest.approx(6.0) and w1["mpap_mmhg"] == pytest.approx(20.0)
    assert w1["map_mmhg"] == pytest.approx(feat["map_mmhg"], abs=0.5)
    assert res["rejections"]


def test_window_rule_rejects_a_case_without_stationary_output(reference_beat):
    sig, _ = _case(reference_beat, minutes=30.0)
    tco = sig.numerics["co"][0]
    sig.numerics["co"] = (tco, 3.0 + 9.0 * tco / tco.max())    # 3 -> 12 L/min in 30 min: never stationary
    assert signals.select_windows(sig)["windows"] == []


def test_full_acceptance_variant_removes_partly_rejected_beats_from_the_heart_rate_bins(reference_beat):
    """Registered rule: bins use beats that pass the basic checks. Post hoc variant: bins use fully accepted beats."""
    beat, shape200, feat = reference_beat
    rng = np.random.default_rng(11)
    art = synthetic_art(shape200, REFERENCE.period, 700.0, rng, resp=0.0)
    for k in range(7):                                          # seven 10-s stretches with a damped line
        seg = slice(int((50 + 60 * k) * FS), int((60 + 60 * k) * FS))
        art[seg] = art[seg].mean() + 0.3 * (art[seg] - art[seg].mean())
    t2 = np.arange(0.0, 700.0, 2.0)
    sig = signals.CaseSignals(art=art, numerics={"cvp": (t2, np.full(len(t2), 6.0)), "mpap": (t2, np.full(len(t2), 20.0)),
                                                   "co": (t2, np.full(len(t2), 6.0))}, t_min=0.0, t_max=700.0)
    beats = signals.detect_beats(art, FS)
    registered = signals.window_report(sig, beats, 0.0, signals.RULE)
    variant = signals.window_report(sig, beats, 0.0, dict(signals.RULE, hr_bins_full_acceptance=True))
    assert registered == (True, "ok")                           # damped beats still pass the basic checks
    assert variant == (False, "arterial signal coverage too low")   # 7 of 60 bins lose their beats


@pytest.mark.slow
def test_fit_recovers_the_flow_index_of_a_scaled_subject():
    k = 0.7
    truth = scaled_subject(k, {"resistance_systemic": 0.8, "emax_lv": 1.3, "resistance_pulmonary": 1.4, "emin_rv": 0.8},
                           sf=0.36, stressed=1.1, hr=68.0)
    f = model_features(periodic_beat(truth))
    obs = {"heart_rate_bpm": 68.0, "ensemble": f["ensemble"].tolist(), "cvp_mmhg": f["cvp_mmhg"],
           "mpap_mmhg": f["mpap_mmhg"]}
    fit = fit_window(obs)
    assert fit["ok"]
    assert fit["flow_index_l_min"] == pytest.approx(f["co_l_min"] / k, rel=0.03)
    assert fit["rmse_waveform_mmhg"] < 0.5
    assert fit["numerical_relative_difference_co"] < 0.02


def _population(n=45, noise=0.10, seed=3):
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n):
        bsa, age = rng.uniform(1.4, 2.1), rng.uniform(35, 80)
        x = rng.uniform(4.0, 9.0)
        k = np.exp(-0.1 + 0.8 * np.log(bsa / 1.73) - 0.06 * (age - 60) / 10 + rng.normal(0, noise))
        rows.append({"subject": i, "co_ref": x * k, "flow_index": x, "lz": x * np.exp(rng.normal(0, 0.3)),
                     "bsa": bsa, "age": age})
    return rows


def test_anchor_recovers_scale_and_ranks_estimators():
    rows = _population()
    res = anchor.evaluate(rows, n_boot=300)
    pe = {e: res["estimators"][e]["percentage_error"] for e in anchor.ESTIMATORS}
    assert pe["MODEL"] < 30.0 < pe["B0"]
    assert pe["MODEL"] < pe["B2"] and pe["MODEL"] < pe["B1"]
    assert res["verdict_model"]["accepted"]
    lo, hi = res["estimators"]["B0"]["model_minus_this_pe_ci95"]
    assert hi < 0


def test_leave_one_subject_out_never_uses_the_held_out_subject():
    rows = _population(n=30)
    rows.append(dict(rows[0], subject=0))               # second case of subject 0
    base = anchor.loso_predictions(rows, "MODEL")
    changed = [dict(r) for r in rows]
    for r in changed:
        if r["subject"] == 0:
            r["co_ref"] *= 50.0                          # absurd reference for both cases of subject 0
    again = anchor.loso_predictions(changed, "MODEL")
    idx0 = [i for i, r in enumerate(rows) if r["subject"] == 0]
    assert np.allclose(base[idx0], again[idx0])          # its own prediction ignores its own reference
    assert not np.allclose(np.delete(base, idx0), np.delete(again, idx0))


def test_percentage_error_formula():
    ref = np.array([4.0, 5.0, 6.0, 5.0])
    pred = ref + np.array([0.5, -0.5, 0.5, -0.5])
    s = anchor.agreement(pred, ref)
    assert s["bias_l_min"] == pytest.approx(0.0)
    assert s["percentage_error"] == pytest.approx(100 * 1.96 * np.std([0.5, -0.5, 0.5, -0.5], ddof=1) / 5.0)
