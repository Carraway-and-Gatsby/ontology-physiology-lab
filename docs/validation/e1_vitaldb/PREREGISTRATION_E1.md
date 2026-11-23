# E1 pre-registration: VitalDB thermodilution subset (written 2026-11-23, before any recording was opened)

Parent document: `../physiological_validation_methodology_v1.md` (methodology v1, experiments A and C, minimal
experiment E1). This file fixes everything that methodology v1 left open and lists every deviation from it. It is
sealed by the commit that adds it; the commit hash is the seal. Written by Claude (Mythos 5.2) in a Claude Code session
on the owner's instruction "VitalDB 첫 번째 검증 실험 진행해라"; the three design decisions marked [OWNER] were made
by the owner on 2026-11-23.

## 0. What was known when this was sealed

Read before sealing (metadata only, no physiological sample, no clinical value):
- the public track index of vitaldb.net (`https://api.vitaldb.net/trks`: case id, track name, track id);
- from PhysioNet `vitaldb` 1.0.0: `LICENSE.txt`, `SHA256SUMS.txt`, `track_names.csv`, `clinical_parameters.csv` (the
  field dictionary, not `clinical_data.csv`) and the file index of `vital_files/` (names and sizes).

Not opened before sealing: any `.vital` file, `clinical_data.csv`, `lab_data.csv`.
Code state at sealing: `experiments/e1_vitaldb/` passes its synthetic-data tests (9 tests, model-generated signals).
The reader `vital_io.py` and the driver `run_e1.py` have never been run on a real file.

## 1. Question and claim under test

Methodology v1 states E1 as "calibrate on pressures, predict thermodilution CO". `IDENTIFIABILITY_RECORD.md` shows
that this is impossible as stated: the model has an exact flow-scaling symmetry, so no pressure data determine CO.
[OWNER] The flow scale is therefore learned from other subjects (leave-one-subject-out), as section 5.5 of
methodology v1 allows ("between-subject split").

Claim under test: the flow index X that the calibrated model derives from a subject's arterial waveform, CVP and mean
PAP, multiplied by a scale learned from other subjects' body size, age and thermodilution CO, predicts that subject's
thermodilution CO within the agreement limit of Critchley and Critchley (1999), and does so better than a
pulse-pressure index used in the same way.

Expectation recorded now so that it can be refuted (author's judgement, not a result): the percentage error will
exceed 30 %, and the model will not be measurably better than baseline B2.

## 2. Data and routes

- Recordings: PhysioNet `vitaldb` 1.0.0, https://physionet.org/content/vitaldb/1.0.0/ (open access, CC BY 4.0, DOI
  10.13026/czw8-9p62; Lee et al. 2022). Every downloaded file is checked against `SHA256SUMS.txt`.
- Case selection: the vitaldb.net track index (terms of that site: CC BY-NC-SA 4.0 with a data use agreement). Only
  case ids and track names are taken from it; the presence of the tracks is re-checked from the PhysioNet files
  (`run_e1.py inventory`), and a case is used only if the PhysioNet file contains them. [OWNER]
- Raw files are kept outside the repository. The repository receives only derived per-case numbers.

## 3. Case sets (`case_lists.json`)

- TEST: the 60 cases whose index entry has all of `SNUADC/ART`, `Vigilance/CO`, `Solar8000/PA_MBP`,
  `Solar8000/CVP`. 49 of them also list `Vigilance/EDV` and `Vigilance/ESV`.
- DEV (never scored): 8 cases drawn with seed 20261123 from the 21 cases that have the three pressure tracks but no
  `Vigilance/CO` (pressure pipeline), and the 2 cases that have `Vigilance/CO`, ART and CVP but no `PA_MBP` (format
  of the thermodilution track). DEV cases are used to make the reader and the pipeline run on real files.
- Procedure: seal (this commit) -> DEV files only -> fixes -> code-freeze commit -> TEST files. `run_e1.py` refuses
  the TEST set unless HEAD equals the freeze commit and the experiment tree is clean. Every change between the seal
  and the freeze is listed in `DEV_NOTES.md` with its reason; changes of anything in sections 4 to 8 are deviations
  and are listed as such. Nothing is changed after the first TEST file is read; later analyses go in a new file and
  are labelled post hoc.
- Subjects: LOSO and the bootstrap group cases by `subjectid` of `clinical_data.csv`.

## 4. Stationary-window rule (mechanical; no human adjudication) [OWNER]

Methodology v1 asked for a clinician blind to model output. The owner chose a purely mechanical rule; this is a
deviation (section 10). The rule uses measured signals only and is applied by code before any model is fitted.

Candidate windows are 600 s long and start every 60 s between operation start and operation end (`opstart`, `opend`).
A window qualifies if all of the following hold (`signals.RULE`):

1. No listed vasoactive infusion rate changes from 60 s before the window to its end (phenylephrine, norepinephrine,
   epinephrine, dopamine, dobutamine, nitroglycerin, nitroprusside, vasopressin, PGE1, milrinone, diltiazem; a track
   that is absent counts as no infusion; rates are step functions, zero before their first reading).
2. At least 3 `Vigilance/CO` readings in the window, all within +/-10 % of their median.
3. At least 30 readings each of `Solar8000/CVP` and `Solar8000/PA_MBP` in the last 120 s.
4. Heart rate from accepted beats, in 10-s bins: at least 90 % of bins have 3 or more beats and every such bin is
   within +/-5 % of the window median (the +/-5 % is from methodology v1 section 5.5).
5. Mean of the low-passed arterial signal in 10-s bins: at least 90 % of bins are 90 % complete and each is within
   +/-10 % of the window median.
6. In the last 120 s (the analysis segment): at least 60 accepted beats and at least 80 % of detected beats accepted.
7. Plausibility: MAP 40-160 mmHg, CVP -5 to 30 mmHg, mean PAP 5-80 mmHg, CO 1-15 L/min, and CVP < mean PAP < MAP.

W1 is the earliest qualifying window. W2 is the earliest qualifying window that starts at least 1,800 s after W1 ends.
A case without W1 is excluded and its rejection counts are reported. The numbers in items 1-3 and 5-7 (600 s, 120 s,
+/-10 %, 90 %, 80 %, 60 beats, the ranges, 1,800 s) are design choices without a published source; they select data
and are not acceptance criteria.

## 5. Measured features (`signals.py`)

- Arterial signal: `SNUADC/ART` at 500 Hz, zero-phase 4th-order Butterworth low-pass at 20 Hz.
- Beats: systolic peaks at least 0.30 s apart with prominence of at least 30 % of the 5th-95th percentile span; the
  foot is the minimum between consecutive peaks. A beat is accepted if it has no missing sample, SBP 40-300 mmHg,
  DBP 20-200 mmHg, period within +/-20 % of the segment median, pulse pressure within 0.5-1.5 times the segment
  median, and correlation of at least 0.90 with the median beat shape.
- Heart rate = 60 / median accepted beat period. Ensemble beat = mean of accepted beats, each resampled to 50
  equally spaced phase points from its foot. MAP = time-weighted mean over accepted beats. SBP, DBP = maximum and
  minimum of the ensemble beat.
- CVP and mean PAP = mean of the monitor numerics (`Solar8000/CVP`, `Solar8000/PA_MBP`) over the analysis segment.
- Reference CO = median of `Vigilance/CO` over the whole 600-s window. RV EDV, ESV, RVEF = medians of
  `Vigilance/EDV`, `ESV`, `RVEF` over the window where present.
- Respiration: the segment is 120 s of mechanical ventilation and all accepted beats are averaged; beats are not
  selected by ventilatory phase (deviation, section 10).

## 6. Calibration at the reference scale (`calibrate.py`, `steady.py`)

- Arterial compliance is held at the project default (1.5 mL/mmHg); this fixes the reference flow scale.
- Imposed: heart rate (measured). Estimated (6): systemic resistance, LV peak elastance, systolic fraction, total
  stressed volume, pulmonary resistance, RV minimum elastance. All other parameters stay at the project defaults,
  which are author-chosen values without a published source (methodology v1 section 9).
- The model is evaluated at its periodic state (fixed point of the one-beat map, then the project periodicity report
  with 3 beats and 1e-4 mL). The model arterial waveform receives the same 20 Hz low-pass and is aligned at its
  minimum, like the measured beat.
- Residuals: 50 waveform differences divided by (4 mmHg x sqrt(50)), the CVP difference divided by 2 mmHg, the mean
  PAP difference divided by 3 mmHg. These weights are design choices, not uncertainty claims.
- Optimiser: bounded trust-region least squares on log-parameters (systolic fraction on its own scale, 0.15-0.60),
  3 starts (defaults, then two seeded perturbations, seed 20261123), lowest cost kept.
- Output: flow index X = model CO at the reference scale.
- Exclusions decided here: no valid fit ("fit failed"); CO at 400 versus 200 samples per beat differs by 2 % or more
  ("inconclusive", methodology v1 section 8: numerical uncertainty must be 10 times smaller than the 20 % reference
  precision). Fits with a parameter at a bound are kept and counted.

## 7. Estimators (`anchor.py`)

All four are least-squares fits of log(reference CO) on the other subjects (LOSO by subject), with identical
covariates log(BSA / 1.73 m2) and (age - 60) / 10. BSA by the Du Bois formula (0.007184 W^0.425 H^0.725).

| Name | Offset | Meaning |
|---|---|---|
| MODEL | log X | model flow index, scale learned from other subjects |
| B2 | log(HR x PP / (SBP + DBP)) | pulse-pressure index (Liljestrand-Zander form, as evaluated by Sun et al. 2009), no model |
| B1 | none | body size and age only |
| B0 | none, intercept only | mean of the other subjects |

Prediction = exp(offset + fitted linear term). No retransformation correction.

## 8. Analysis and criteria

Primary analysis: W1 of every scored TEST case, estimator MODEL, weights of section 6.

- Bland-Altman bias, SD and 95 % limits of agreement of (prediction - reference); percentage error
  PE = 1.96 SD / mean reference CO (Critchley and Critchley 1999).
- Acceptance, unchanged from methodology v1 sections 6.A and 8: PE <= 30 %. Failure: PE > 30 %, or a bias whose 95 %
  confidence interval excludes zero and which exceeds the assumed reference precision (20 % of mean reference CO).
  Because the scale is learned from the other subjects' CO, a near-zero bias is expected by construction and is not
  evidence for the model.
- 95 % interval of PE: percentile bootstrap over subjects, 10,000 resamples, seed 20261123, predictions held fixed.
- Comparison with baselines (procedure, no absolute number): bootstrap interval of PE(MODEL) - PE(baseline) for B2,
  B1, B0. Reading fixed now: "the model adds measurable information" only if the upper end of the interval for B2 is
  below zero; otherwise "no measurable gain over the pulse-pressure index".
- The three-way label for the primary claim: SUPPORTED if PE <= 30 % and the model adds measurable information over
  B2; NOT SUPPORTED if PE > 30 %; INCONCLUSIVE otherwise (within the limit but not better than a baseline that needs
  no model).
- If fewer than 8 cases are scored, no agreement statistics are computed.

Report-only (no pass mark, never described as passed):
- fit diagnostics: bias, SD and MAE of model minus measurement for MAP, SBP, DBP, CVP, mean PAP; waveform RMSE;
- RV EDV and ESV: model value at the reference scale multiplied by the subject's predicted scale, against the
  Vigilance values; RVEF: model value against Vigilance RVEF;
- W2: prediction for W2 from the scale fitted on W1 of the other subjects; change of error between W1 and W2;
- sensitivity S1: the whole analysis with equal residual weights (1 mmHg each).

## 9. Measurement-uncertainty statements used

| Quantity | Statement | Source |
|---|---|---|
| Thermodilution CO | precision assumed +/-20 % | Critchley and Critchley 1999 (abstract read via PubMed; full text not read) |
| Arterial pressure, CVP, PAP | no uncertainty value is used in any criterion; transducer levelling, zeroing and damping are not documented in VitalDB (methodology v1 section 3.1) | - |
| Continuous CO averaging time and delay of the Vigilance monitor | not verified in a primary source; handled by the 600-s stationarity requirement | - |
| Vigilance RV volumetrics | accuracy not retrieved; report-only | - |

## 10. Deviations from methodology v1

1. Flow scale learned from other subjects instead of "pressures -> CO" (forced by the identifiability result).
2. No clinician adjudication of windows; mechanical rule only.
3. Identifiability: structural result and local sensitivity are recorded; profile likelihood on synthetic data
   (section 5.2 step 3) is replaced by a synthetic recovery test of the fit (flow index recovered within 3 % on a
   scaled synthetic subject). No structural-identifiability software was used.
4. No propagation of parameter and measurement uncertainty, no prediction intervals, no coverage test (section 7 and
   experiment F). Intervals reported are bootstrap intervals of agreement statistics only.
5. Beats are not averaged over integer ventilatory cycles; all accepted beats of 120 s are averaged.
6. Fixed parameters have no published source and their effect is not carried as input uncertainty.
7. Waveform-morphology comparison against Windkessel baselines (experiment B) is not part of this run.
8. The Liljestrand-Zander form and the Du Bois formula are written from general knowledge; they define a baseline and
   a covariate, not acceptance criteria. The primary texts were not read.

## 11. What this experiment cannot show, whatever the result

- Validity of the model for any use: one centre, one ethnicity, anaesthetised ventilated surgical patients who
  received a pulmonary artery catheter (a selected, sicker subgroup), radial pressure, no LV data.
- That the physics matters, unless MODEL is better than B2: both use the same reference CO of other subjects.
- Anything about responses to perturbations (experiments D, E2, E3).

## 12. Sources

- Critchley LA, Critchley JA. J Clin Monit Comput 1999;15(2):85-91. https://doi.org/10.1023/a:1009982611386
- Sun JX, Reisner AT, Saeed M, Heldt T, Mark RG. Crit Care Med 2009;37(1):72-80. https://doi.org/10.1097/CCM.0b013e3181930174
- Bland JM, Altman DG. Stat Methods Med Res 1999;8(2):135-60. https://doi.org/10.1177/096228029900800204
- Lee HC, Park Y, Yoon SB, Yang SM, Park D, Jung CW. Sci Data 2022;9:279. https://doi.org/10.1038/s41597-022-01411-5
- VitalDB on PhysioNet, version 1.0.0. https://doi.org/10.13026/czw8-9p62

Bibliographic details and abstracts of the four articles were retrieved from PubMed on 2026-11-23.
