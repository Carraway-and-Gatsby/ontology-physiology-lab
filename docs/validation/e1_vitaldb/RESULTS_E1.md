# E1 results: VitalDB thermodilution subset (run 2026-11-23)

Pre-registration: `PREREGISTRATION_E1.md` (sealed at 057d2f4). Code freeze: 74e1928 (`DEV_NOTES.md` lists the one
deviation made before the freeze). The TEST run used the frozen tree; `run_e1.py` checked this at each step.
Machine-readable results: `results/e1_vitaldb/test/` (`score_primary.json`, `score_equal.json`,
`per_case_primary.json`, `features/`, `fits/`, `fits_equal_weights/`, `inventory_test.json`, `download_test.json`).
Written by Claude (Mythos 5.2). No human has reviewed the analysis or this text.

## 1. Verdict on the pre-registered claim: NOT SUPPORTED

Primary analysis (W1 of each scored case, estimator MODEL, registered weights), n = 51 cases = 51 subjects, mean
thermodilution CO 7.43 L/min:

| Estimator | Percentage error (95 % bootstrap interval) | Bias (L/min) | SD (L/min) | Limits of agreement (L/min) |
|---|---|---|---|---|
| MODEL (model flow index, scale from other subjects) | 101.3 % (77.0 to 120.2) | +1.47 | 3.84 | -6.05 to +9.00 |
| B2 (pulse-pressure index, no model) | 51.1 % (38.8 to 61.3) | -0.05 | 1.94 | -3.84 to +3.75 |
| B1 (body size and age only) | 50.3 % (40.8 to 58.9) | -0.22 | 1.91 | -3.96 to +3.51 |
| B0 (mean of the other subjects) | 52.9 % (44.1 to 60.3) | -0.25 | 2.00 | -4.18 to +3.67 |

- Criterion (methodology v1, Critchley and Critchley 1999): percentage error <= 30 %. Observed 101.3 %: failed.
- Bias criterion: not triggered, by a narrow margin. The bias is +1.47 L/min and its 95 % interval, +0.42 to +2.53,
  excludes zero. The criterion also requires the bias to exceed the assumed reference precision, 20 % of the mean
  reference CO = 1.485 L/min; the observed 1.474 L/min is 0.011 L/min below it. The near-zero bias that the
  pre-registration expected from learning the scale on the other subjects did not occur for MODEL (the baselines have
  -0.05 to -0.25 L/min). Its cause was not analysed.
- Comparison with baselines: PE(MODEL) - PE(B2) = +24.1 to +73.8 points (95 % interval); the same sign against B1 and
  B0. The model is measurably worse than every baseline, including the mean of the other subjects.
- The expectation recorded in the pre-registration (PE above 30 %, no gain over B2) held; the size of the failure was
  not anticipated.
- None of the baselines meets the 30 % limit either.

Sensitivity S1 (equal residual weights, report-only): MODEL 106.0 % (80.0 to 126.1), bias +1.72 L/min (here the bias
criterion is also triggered); same reading.

## 2. Case flow

| Step | Cases |
|---|---|
| Listed from the index | 60 |
| Excluded: PhysioNet file has no `SNUADC/ART` (2016) | 1 |
| Excluded: PhysioNet file has no `Vigilance/CO` (2185, 5490) | 2 |
| Excluded: no qualifying stationary window (818, 1900, 3270, 3930, 5175, 5983) | 6 |
| Scored (W1) | 51 |
| of which with a second window (W2) | 42 |
| Fit failed or numerically inconclusive | 0 |

93 windows were fitted with each weight set (about 25 minutes per set on 12 processes).

## 3. Report-only results (no pass mark)

- Fit of the calibrated quantities (model minus measurement, 51 windows): MAP bias -0.08 (SD 0.10) mmHg; CVP +0.05
  (0.25); mean PAP +0.14 (0.24); SBP -10.2 (8.6); DBP -3.9 (5.6); median waveform RMSE 4.8 mmHg.
- 34 of 51 fits have at least one parameter at a bound: pulmonary resistance 29 (lower bound), systolic fraction 7,
  RV minimum elastance 2, systemic resistance 1.
- RV volumetrics against the Vigilance monitor: EDV bias -59 mL (SD 73, n 41, mean reference 210 mL); ESV bias -75 mL
  (SD 40, n 41, mean reference 121 mL); RVEF bias +21.6 points (SD 18.8, n 39, mean reference 42 %).
- Second window (n 42): percentage error 97.5 %; change of error between the windows of a case: mean -0.06 L/min,
  SD 4.40 L/min.

## 4. Post hoc description (not registered; cannot change the verdict)

Looked at after the registered numbers were known, to see where the error comes from.

- The flow index X spans 0.17 to 11.6 L/min (quartiles 5.35, 7.23, 8.70) while the reference CO spans 3.8 to 12.1.
  SD of log X is 0.85 against 0.27 for log CO. Spearman correlation with reference CO: X 0.36, pulse-pressure index
  0.45.
- Five fits are degenerate: the fitted model waveform is almost flat (model pulse pressure 1 to 9 mmHg against 35 to
  52 mmHg measured; waveform RMSE 9.5 to 17.7 mmHg) and X is 0.17 to 1.6 L/min (cases 2872, 2326, 5837, 5607, 4800).
  The optimiser ended, in all three starts, at a solution that matches the mean pressures and not the waveform. The
  pre-registration had no rule against this (only "no valid fit" and the numerical check), so these cases were
  scored. This is a weakness of the calibration procedure, not shown by the synthetic tests or by the ten
  development recordings.
- Without those five cases (n 46): MODEL 50.4 %, B2 52.6 %, B1 50.6 %, B0 52.4 %; PE(MODEL) - PE(B2) = -18.4 to
  +11.6 points. So even when the calibration behaves, the model index is not distinguishable from body size and age
  alone, or from the mean of the other subjects, and stays far from the 30 % limit.
- Restricted to the 17 fits with no parameter at a bound: MODEL 112.5 %.

## 5. What this establishes and what it does not

Established for this dataset and this procedure:
- The six-compartment model, calibrated to radial pressure, CVP and mean PAP, does not predict thermodilution cardiac
  output within the accepted agreement limit, with a flow scale learned from other patients.
- The model-derived flow index carries no measurable information about cardiac output beyond what age and body size
  give, in the 46 cases where the fit is not degenerate, and is harmful in the registered analysis.
- The calibration reproduces what it is fitted to (mean pressures) and misses the radial systolic and diastolic
  pressures by several mmHg in a consistent direction.
- The model's right ventricle is far too small and ejects too large a fraction compared with the monitor's values.

Not established:
- That no lumped model can do this. This run tests one model, one calibration recipe (six free parameters, the others
  at unsourced defaults), one window rule and one centre.
- The cause of the failure. Candidate causes that this run cannot separate: radial versus central pressure (the model
  has no wave propagation); fixed parameters without a source (LV minimum elastance, venous and pulmonary
  compliances); the reference itself (continuous thermodilution, precision assumed, not measured here); between-patient
  variation of arterial compliance that age and body size do not capture.
- Anything about responses to perturbations.

Population caveat: the 51 scored cases are adults who received a pulmonary artery catheter during non-cardiac surgery
at one hospital; their mean cardiac output (7.4 L/min) is high for anaesthetised adults, which suggests a selected
group. Diagnoses and operation types were not analysed.

## 6. Deviations and incidents during the TEST run

- PhysioNet returned HTTP 502 three times during the download; the same command was repeated until all 61 files
  matched `SHA256SUMS.txt`. No code was changed.
- No change to code, rules or criteria was made between the first reading of a TEST file and the registered scoring.
  Section 4 above and `POSTHOC_E1.md` are analyses added afterwards and are labelled post hoc.
- Discrepancy between the pre-registration and the code that ran (found in review of PR #11 of [private repository], after the run): sections
  4 and 5 say that the 10-s heart-rate bins of the window rule use accepted beats, but the code formed them from
  beats that had passed only the basic checks (no missing sample, absolute pressure ranges, minimum pulse pressure),
  not the period, pulse-pressure-ratio and template-correlation checks. The registered numbers above are from the
  code as it ran and are unchanged. `POSTHOC_E1.md` repeats the analysis with the rule as written: the first window
  changes in 2 of 51 cases and the percentage error of MODEL is 99.2 % (74.4 to 118.2); the verdict is the same.
- Correction of this file (2026-11-23, after review): the first version said that the 95 % interval of the bias
  includes zero. It does not; the bullet on the bias criterion in section 1 now states the actual reason.
- Attribution: recordings from VitalDB (Lee et al. 2022, https://doi.org/10.1038/s41597-022-01411-5) through
  PhysioNet version 1.0.0 (https://doi.org/10.13026/czw8-9p62), CC BY 4.0. Case selection used the vitaldb.net track
  index (case ids and track names only).
