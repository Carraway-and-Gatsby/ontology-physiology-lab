"""Beat segmentation, artefact rejection, ensemble beat and the mechanical stationary-window rule (E1).

Pure numpy/scipy; the functions take arrays, never files. Every numeric setting lives in RULE and is declared in
docs/validation/e1_vitaldb/PREREGISTRATION_E1.md. Settings marked "design choice" there have no published source.
"""
from dataclasses import dataclass, field

import numpy as np
from scipy.signal import butter, filtfilt, find_peaks

RULE = {
    "fs_hz": 500.0,
    "lowpass_hz": 20.0,                 # zero-phase 4th-order Butterworth, used for detection and for the ensemble beat
    "min_peak_distance_s": 0.30,
    "peak_prominence_fraction": 0.30,   # of the 5th-95th percentile span of the surrounding block
    "local_span_s": 20.0,               # block length for that span
    "min_peak_prominence_mmhg": 5.0,
    "min_pulse_pressure_mmhg": 10.0,    # accepted beats
    "beat_period_tolerance": 0.20,      # accepted beats: period within +/-20 % of the median period
    "pulse_pressure_ratio": (0.5, 1.5), # accepted beats: pulse pressure relative to the median
    "sbp_range": (40.0, 300.0),
    "dbp_range": (20.0, 200.0),
    "template_correlation": 0.90,
    "ensemble_points": 50,
    "window_s": 600.0,
    "window_step_s": 60.0,
    "segment_s": 120.0,                 # final part of the window used for the pressure features
    "bin_s": 10.0,
    "hr_tolerance": 0.05,               # methodology v1 section 5.5
    "map_tolerance": 0.10,
    "co_tolerance": 0.10,
    "min_bin_coverage": 0.90,
    "min_accept_fraction": 0.80,
    "min_accepted_beats": 60,
    "min_numeric_readings_segment": 30,
    "min_co_readings": 3,
    "w2_gap_s": 1800.0,
    "require_co": True,                 # False only for development cases that have no thermodilution track
    # False = the registered TEST run: the 10-s heart-rate bins used beats that passed only the basic checks of
    # detect_beats (no missing sample, absolute ranges, minimum pulse pressure). True = post hoc variant that applies
    # the full acceptance of section 5 (period, pulse-pressure ratio, template correlation, relative to the window)
    # before the bins are formed. See docs/validation/e1_vitaldb/POSTHOC_E1.md.
    "hr_bins_full_acceptance": False,
    "plausible": {"map": (40.0, 160.0), "cvp": (-5.0, 30.0), "mpap": (5.0, 80.0), "co": (1.0, 15.0)},
}


@dataclass
class Beats:
    feet: np.ndarray            # sample index of each beat foot (len n+1 for n beats)
    accepted: np.ndarray        # bool per beat
    period_s: np.ndarray
    sbp: np.ndarray
    dbp: np.ndarray
    filtered: np.ndarray        # low-passed signal (NaN where the raw signal is NaN)
    fs: float

    @property
    def start_s(self) -> np.ndarray:
        return self.feet[:-1] / self.fs


def lowpass(x: np.ndarray, fs: float, cutoff: float) -> np.ndarray:
    """Zero-phase low-pass; NaN stretches are interpolated for filtering and restored as NaN afterwards."""
    x = np.asarray(x, dtype=float)
    bad = ~np.isfinite(x)
    if bad.all():
        return x.copy()
    filled = x.copy()
    idx = np.arange(len(x))
    filled[bad] = np.interp(idx[bad], idx[~bad], x[~bad])
    b, a = butter(4, cutoff / (fs / 2.0))
    y = filtfilt(b, a, filled)
    y[bad] = np.nan
    return y


def _resample(beat: np.ndarray, n: int) -> np.ndarray:
    """n equally spaced phase points over [foot, next foot)."""
    src = np.arange(len(beat), dtype=float)
    return np.interp(np.arange(n) * (len(beat) / n), src, beat)


def detect_beats(art: np.ndarray, fs: float = RULE["fs_hz"], rule: dict = RULE) -> Beats:
    """Feet = minimum of the low-passed signal between consecutive systolic peaks; then per-beat acceptance."""
    y = lowpass(art, fs, rule["lowpass_hz"])
    ok = np.isfinite(y)
    empty = Beats(np.array([], int), np.array([], bool), np.array([]), np.array([]), np.array([]), y, fs)
    if ok.sum() < 5 * fs:
        return empty
    z = np.where(ok, y, np.nanmedian(y))
    cand, props = find_peaks(z, distance=int(rule["min_peak_distance_s"] * fs),
                             prominence=rule["min_peak_prominence_mmhg"])
    # the prominence threshold follows the local signal span, so that flush or disconnection stretches elsewhere in
    # the record do not hide genuine beats
    blk = int(rule["local_span_s"] * fs)
    nblk = int(np.ceil(len(z) / blk))
    span = np.array([np.subtract(*np.percentile(z[i * blk:(i + 1) * blk], [95, 5])) for i in range(nblk)])
    peaks = cand[props["prominences"] >= rule["peak_prominence_fraction"] * span[cand // blk]]
    if len(peaks) < 3:
        return empty
    feet = np.array([a + int(np.argmin(z[a:b])) for a, b in zip(peaks[:-1], peaks[1:])])
    n = len(feet) - 1
    if n < 2:
        return empty
    period = np.diff(feet) / fs
    sbp = np.array([np.max(z[feet[i]:feet[i + 1]]) for i in range(n)])
    dbp = z[feet[:-1]]
    nan_free = np.array([ok[feet[i]:feet[i + 1]].all() for i in range(n)])
    acc = nan_free.copy()
    acc &= (sbp >= rule["sbp_range"][0]) & (sbp <= rule["sbp_range"][1])
    acc &= (dbp >= rule["dbp_range"][0]) & (dbp <= rule["dbp_range"][1])
    acc &= (sbp - dbp) >= rule["min_pulse_pressure_mmhg"]
    return Beats(feet, acc, period, sbp, dbp, y, fs)


def accept_in_stretch(beats: Beats, i0: int, i1: int, rule: dict = RULE):
    """Final acceptance of beats i0..i1-1 relative to the stretch medians; returns (mask, ensemble or None)."""
    idx = np.arange(i0, i1)
    if len(idx) == 0:
        return np.zeros(0, bool), None
    base = beats.accepted[idx]
    if base.sum() < 3:
        return np.zeros(len(idx), bool), None
    t_med = np.median(beats.period_s[idx][base])
    pp = beats.sbp[idx] - beats.dbp[idx]
    pp_med = np.median(pp[base])
    m = base & (np.abs(beats.period_s[idx] / t_med - 1.0) <= rule["beat_period_tolerance"])
    m &= (pp >= rule["pulse_pressure_ratio"][0] * pp_med) & (pp <= rule["pulse_pressure_ratio"][1] * pp_med)
    n = rule["ensemble_points"]
    shapes = np.full((len(idx), n), np.nan)
    for j, i in enumerate(idx):
        if m[j]:
            shapes[j] = _resample(beats.filtered[beats.feet[i]:beats.feet[i + 1]], n)
    if m.sum() < 3:
        return np.zeros(len(idx), bool), None
    template = np.nanmedian(shapes[m], axis=0)
    for j in np.where(m)[0]:
        c = np.corrcoef(shapes[j], template)[0, 1]
        if not np.isfinite(c) or c < rule["template_correlation"]:
            m[j] = False
    if m.sum() < 3:
        return np.zeros(len(idx), bool), None
    return m, shapes[m].mean(axis=0)


def segment_features(beats: Beats, t0: float, t1: float, rule: dict = RULE) -> dict | None:
    """Pressure features of the analysis segment [t0, t1): heart rate, ensemble beat, MAP, SBP, DBP."""
    starts = beats.start_s
    sel = np.where((starts >= t0) & (beats.feet[1:] / beats.fs <= t1))[0]
    if len(sel) == 0:
        return None
    mask, ensemble = accept_in_stretch(beats, sel[0], sel[-1] + 1, rule)
    if ensemble is None:
        return None
    acc = sel[mask]
    period = float(np.median(beats.period_s[acc]))
    # time-weighted mean over accepted beats = sum of beat integrals / sum of beat durations
    total, dur = 0.0, 0.0
    for i in acc:
        seg = beats.filtered[beats.feet[i]:beats.feet[i + 1]]
        total += float(seg.sum()); dur += len(seg)
    return {"heart_rate_bpm": 60.0 / period, "period_s": period, "ensemble": ensemble.tolist(),
            "map_mmhg": total / dur, "sbp_mmhg": float(ensemble.max()), "dbp_mmhg": float(ensemble.min()),
            "n_beats": int(len(sel)), "n_accepted": int(mask.sum()), "accept_fraction": float(mask.mean())}


def _step_constant(t: np.ndarray, v: np.ndarray, t0: float, t1: float) -> bool:
    """A forward-filled step series (0 before its first reading) does not change on [t0, t1]."""
    keep = np.isfinite(v)
    t, v = t[keep], v[keep]
    if len(t) == 0:
        return True
    before = v[t <= t0]
    start = before[-1] if len(before) else 0.0
    inside = v[(t > t0) & (t <= t1)]
    return bool(np.all(inside == start))


def _in_window(t: np.ndarray, v: np.ndarray, t0: float, t1: float) -> np.ndarray:
    keep = np.isfinite(v) & (t >= t0) & (t < t1)
    return v[keep]


@dataclass
class CaseSignals:
    """Arrays of one case. Numeric tracks are (time_s, value) pairs; art is uniformly sampled from time 0."""
    art: np.ndarray
    numerics: dict                      # name -> (t, v): "cvp", "mpap", "co", optional "rv_edv", "rv_esv", "rvef"
    infusions: dict = field(default_factory=dict)   # track name -> (t, v)
    t_min: float = 0.0                  # allowed analysis interval (operation start/end)
    t_max: float = float("inf")
    fs: float = RULE["fs_hz"]


def window_report(sig: CaseSignals, beats: Beats, t0: float, rule: dict = RULE) -> tuple[bool, str]:
    """Does the window [t0, t0 + window_s) satisfy every condition of the stationary-window rule?"""
    t1 = t0 + rule["window_s"]
    s0 = t1 - rule["segment_s"]
    if t0 < sig.t_min or t1 > sig.t_max:
        return False, "outside operation interval"
    for name, (t, v) in sig.infusions.items():
        if not _step_constant(t, v, t0 - 60.0, t1):
            return False, "vasoactive infusion rate changed"
    co_med = None
    if "co" in sig.numerics or rule.get("require_co", True):
        co = _in_window(*sig.numerics["co"], t0, t1)
        if len(co) < rule["min_co_readings"]:
            return False, "too few cardiac output readings"
        co_med = float(np.median(co))
        if np.any(np.abs(co / co_med - 1.0) > rule["co_tolerance"]):
            return False, "cardiac output not stationary"
    cvp = _in_window(*sig.numerics["cvp"], s0, t1)
    mpap = _in_window(*sig.numerics["mpap"], s0, t1)
    if min(len(cvp), len(mpap)) < rule["min_numeric_readings_segment"]:
        return False, "too few CVP or PA readings"
    # 10-s bins over the whole window: heart rate from accepted beats, mean pressure from the low-passed signal
    starts = beats.start_s
    nb = int(round(rule["window_s"] / rule["bin_s"]))
    usable = beats.accepted
    if rule.get("hr_bins_full_acceptance", False):
        usable = np.zeros(len(beats.accepted), bool)
        sel = np.where((starts >= t0) & (beats.feet[1:] / beats.fs <= t1))[0]
        if len(sel):
            mask, _ = accept_in_stretch(beats, sel[0], sel[-1] + 1, rule)
            usable[sel[mask]] = True
    hr_bins, map_bins = [], []
    for k in range(nb):
        a, b = t0 + k * rule["bin_s"], t0 + (k + 1) * rule["bin_s"]
        in_bin = (starts >= a) & (starts < b) & usable
        if in_bin.sum() >= 3:
            hr_bins.append(60.0 / np.median(beats.period_s[in_bin]))
        seg = beats.filtered[int(a * beats.fs):int(b * beats.fs)]
        if len(seg) and np.isfinite(seg).mean() >= 0.9:
            map_bins.append(float(np.nanmean(seg)))
    if len(hr_bins) < rule["min_bin_coverage"] * nb or len(map_bins) < rule["min_bin_coverage"] * nb:
        return False, "arterial signal coverage too low"
    hr_bins, map_bins = np.array(hr_bins), np.array(map_bins)
    if np.any(np.abs(hr_bins / np.median(hr_bins) - 1.0) > rule["hr_tolerance"]):
        return False, "heart rate not stationary"
    if np.any(np.abs(map_bins / np.median(map_bins) - 1.0) > rule["map_tolerance"]):
        return False, "mean arterial pressure not stationary"
    feat = segment_features(beats, s0, t1, rule)
    if feat is None or feat["n_accepted"] < rule["min_accepted_beats"] or feat["accept_fraction"] < rule["min_accept_fraction"]:
        return False, "too few accepted beats in the analysis segment"
    pl = rule["plausible"]
    vals = {"map": feat["map_mmhg"], "cvp": float(np.mean(cvp)), "mpap": float(np.mean(mpap)), "co": co_med}
    for k, (lo, hi) in pl.items():
        if vals[k] is not None and not lo <= vals[k] <= hi:
            return False, f"{k} outside plausibility range"
    if not vals["cvp"] < vals["mpap"] < vals["map"]:
        return False, "pressure ordering violated"
    return True, "ok"


def window_features(sig: CaseSignals, beats: Beats, t0: float, rule: dict = RULE) -> dict:
    """Features of a qualifying window (call only after window_report returned True)."""
    t1 = t0 + rule["window_s"]
    s0 = t1 - rule["segment_s"]
    out = segment_features(beats, s0, t1, rule)
    out.update({"window_start_s": float(t0), "window_end_s": float(t1),
                "cvp_mmhg": float(np.mean(_in_window(*sig.numerics["cvp"], s0, t1))),
                "mpap_mmhg": float(np.mean(_in_window(*sig.numerics["mpap"], s0, t1))),
                "co_ref_l_min": None, "n_co_readings": 0})
    if "co" in sig.numerics:
        co = _in_window(*sig.numerics["co"], t0, t1)
        out.update({"co_ref_l_min": float(np.median(co)), "n_co_readings": int(len(co))})
    for key in ("rv_edv", "rv_esv", "rvef", "sv_ref"):
        if key in sig.numerics:
            v = _in_window(*sig.numerics[key], t0, t1)
            out[key] = float(np.median(v)) if len(v) else None
    return out


def select_windows(sig: CaseSignals, rule: dict = RULE) -> dict:
    """W1 = earliest qualifying window; W2 = earliest qualifying window starting >= w2_gap_s after the end of W1."""
    beats = detect_beats(sig.art, sig.fs, rule)
    duration = len(sig.art) / sig.fs
    reasons: dict = {}
    found = []
    t0 = max(0.0, np.ceil(sig.t_min / rule["window_step_s"]) * rule["window_step_s"])
    last = min(duration, sig.t_max) - rule["window_s"]
    earliest = t0
    while t0 <= last and len(found) < 2:
        if t0 >= earliest:
            ok, why = window_report(sig, beats, t0, rule)
            if ok:
                found.append(window_features(sig, beats, t0, rule))
                earliest = t0 + rule["window_s"] + rule["w2_gap_s"]
            else:
                reasons[why] = reasons.get(why, 0) + 1
        t0 += rule["window_step_s"]
    return {"windows": found, "rejections": reasons, "n_beats_detected": int(max(len(beats.feet) - 1, 0)),
            "duration_s": float(duration)}
