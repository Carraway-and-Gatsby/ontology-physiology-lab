# E1 development notes: changes between the seal (057d2f4) and the code freeze (2026-11-23)

Only the 10 development recordings and `clinical_data.csv` were opened in this phase (downloaded from PhysioNet,
checksums verified: `results/e1_vitaldb/dev/download_dev.json`). No TEST recording was downloaded or opened.

## 1. Deviation from the sealed pre-registration (section 5, beat detection)

Sealed text: systolic peaks need a prominence of at least 30 % of the 5th-95th percentile span "of the analysed
stretch", which the code applied to the whole recording.
Problem seen on development case 2331: flush and disconnection stretches near 295 mmHg inflate the whole-record span,
and only 204 beats were found in 7 hours although 10-minute blocks contain about 850 beats each.
Change (`signals.py`): the span is taken from the 20-s block that contains the peak; candidate peaks need at least
5 mmHg prominence; accepted beats need a pulse pressure of at least 10 mmHg (noise on a flat line is not a beat).
The three numbers are design choices without a published source. After the change the eight pressure cases give
24,038 to 52,358 beats each. The synthetic-data tests still pass.

## 2. Development-only addition

`vital_io.load_case(..., dev_co_standin=True)` uses `EV1000/CO` (pulse-contour) where a development file has no
`Vigilance/CO`, so that the cardiac-output code path runs. It is switched on for the development set only and its
values are never scored or used as a reference.

## 3. Finding: the vitaldb.net index and the PhysioNet files name some tracks differently

- Development cases 2174 and 3849 are listed in the vitaldb.net index with `Vigilance/CI, CO, SV, SVI` and no EV1000
  track. The PhysioNet 1.0.0 files contain no Vigilance track for them; they contain nine `EV1000/*` tracks instead
  (CO, CI, SV, SVI, SVR, SVRI, SVV, ART_MBP, CVP). Neither case has `Solar8000/PA_MBP`, so no pulmonary artery
  catheter is evident. In the PhysioNet files their cardiac output is a pulse-contour estimate, not thermodilution.
- In the index, 65 cases list `Vigilance/CO`: 59 also list a thermodilution-specific track (`BT_PA`, `SVO2` or
  `EDV`) and `PA_MBP`; 5 list neither and have no `PA_MBP` (the pattern of 2174 and 3849); 1 lists `PA_MBP` but no
  thermodilution-specific track.
- Consequences. (a) The two development cases meant to show the format of the thermodilution track do not contain
  one, so `Vigilance/CO` has not been seen before the TEST run; the numeric record format and its 2-s cadence were
  checked on `Vigilance/SVO2`, `Vigilance/BT_PA` and `EV1000/CO` instead. (b) The pre-registered rule already
  requires the track to be present in the PhysioNet file; a TEST case whose file has no `Vigilance/CO` is excluded
  with that reason. (c) Cases that have a thermodilution track in the PhysioNet files but not in the index cannot be
  found without scanning all 6,388 files (95 GB); none was looked for.
- For the eight pressure development cases the index and the files agree on all Vigilance and EV1000 tracks.

## 4. Observations on development data (no change made)

Window selection: 7 of 8 pressure cases have at least one qualifying window (13 windows; 14 with the stand-in cases
counted twice). Fits: 14 of 14 converged; MAP, CVP and mean PAP are matched within 0.5 mmHg; waveform RMSE 1.6 to
6.8 mmHg; model SBP is 0 to 12 mmHg below and model DBP 1 to 7 mmHg below the radial values; `resistance_pulmonary`
is at its lower bound in 4 windows and `systolic_fraction` at its upper bound in 1 (several others within 0.01 of
it); numerical difference of CO below 0.3 %. The flow index of the two windows of a case differs by 0.0 to 21.7 % (seven cases: 5.0, 5.8, 0.0, 4.4, 21.7, 7.2, 15.8 %).
Bounds, weights and the free-parameter set were left as sealed: there is no reference CO in the development set to
tune against, and fits at a bound are kept and counted as the pre-registration says.

## 5. Not changed

Sections 3, 4, 6, 7, 8 of the pre-registration (case sets, window rule, calibration, estimators, analysis and
criteria) are as sealed.
