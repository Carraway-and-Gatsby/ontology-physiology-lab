"""Reading local VitalDB .vital files (PhysioNet vitaldb 1.0.0) into CaseSignals. Needs the `vitaldb` package.

Only local files are read; nothing is fetched from vitaldb.net here.
"""
from pathlib import Path

import numpy as np

from .signals import RULE, CaseSignals

ART = "SNUADC/ART"
NUMERIC = {"cvp": "Solar8000/CVP", "mpap": "Solar8000/PA_MBP", "co": "Vigilance/CO", "rv_edv": "Vigilance/EDV",
           "rv_esv": "Vigilance/ESV", "rvef": "Vigilance/RVEF", "sv_ref": "Vigilance/SV"}
VASOACTIVE = ["Orchestra/PHEN_RATE", "Orchestra/NEPI_RATE", "Orchestra/EPI_RATE", "Orchestra/DOPA_RATE",
              "Orchestra/DOBU_RATE", "Orchestra/NTG_RATE", "Orchestra/NPS_RATE", "Orchestra/VASO_RATE",
              "Orchestra/PGE1_RATE", "Orchestra/MRN_RATE", "Orchestra/DTZ_RATE"]


def track_inventory(path: str | Path) -> list[str]:
    from vitaldb import VitalFile
    return sorted(VitalFile(str(path), header_only=True).get_track_names())


def _numeric(vf, name: str):
    """(time from case start in s, value) of a numeric track, from its records (no resampling)."""
    trk = vf.find_track(name)
    if trk is None or not trk.recs:
        return None
    t = np.array([r["dt"] for r in trk.recs], dtype=float) - vf.dtstart
    v = np.array([r["val"] for r in trk.recs], dtype=float)
    order = np.argsort(t, kind="stable")
    return t[order], v[order]


DEV_CO_STANDIN = "EV1000/CO"   # pulse-contour CO; development runs only, never a reference


def load_case(path: str | Path, t_min: float = 0.0, t_max: float = float("inf"), required=("cvp", "mpap", "co"),
              dev_co_standin: bool = False):
    """CaseSignals of one file, or (None, reason) if a required track is missing.

    dev_co_standin=True (development set only) uses EV1000/CO in place of a missing Vigilance/CO so that the
    cardiac-output code path can be exercised; such values are pulse-contour estimates and are never scored."""
    from vitaldb import VitalFile
    wanted = [ART] + list(NUMERIC.values()) + VASOACTIVE + ([DEV_CO_STANDIN] if dev_co_standin else [])
    vf = VitalFile(str(path), wanted)
    present = set(vf.get_track_names())
    if ART not in present:
        return None, "no arterial waveform"
    art = vf.to_numpy([ART], 1.0 / RULE["fs_hz"])
    art = np.asarray(art, dtype=float).reshape(len(art), -1)[:, 0]
    numerics = {}
    for key, name in NUMERIC.items():
        tv = _numeric(vf, name) if name in present else None
        if tv is not None:
            numerics[key] = tv
    if dev_co_standin and "co" not in numerics and DEV_CO_STANDIN in present:
        tv = _numeric(vf, DEV_CO_STANDIN)
        if tv is not None:
            numerics["co"] = tv
    for key in required:
        if key not in numerics:
            return None, f"missing {NUMERIC[key]}"
    infusions = {}
    for name in VASOACTIVE:
        tv = _numeric(vf, name) if name in present else None
        if tv is not None:
            infusions[name] = tv
    return CaseSignals(art=art, numerics=numerics, infusions=infusions, t_min=float(t_min), t_max=float(t_max),
                       fs=RULE["fs_hz"]), "ok"
