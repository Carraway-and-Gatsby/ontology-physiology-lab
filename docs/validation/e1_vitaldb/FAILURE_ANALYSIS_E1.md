# E1 failure analysis (post hoc, 2026-11-23)

Status: post hoc and exploratory. Everything here was done after the registered result (`RESULTS_E1.md`: NOT
SUPPORTED, percentage error 101.3 % against a 30 % limit) was known, on the same 51 scored cases. It explains the
failure; it does not change the registered verdict, and no number below is a validation result. Written by Claude
(Mythos 5.2); not reviewed by a human.

Reproduce: `posthoc_refits.py`, `posthoc_degenerate_starts.py`, `posthoc_realign.py`, then
`posthoc_failure_analysis.py` (all in this folder). Numbers: `results/e1_vitaldb/posthoc_failure_analysis/`.
No recording was re-read; the scripts use the saved window features and fits.

## 1. Summary

The failure has two layers of different kinds.

| Layer | Cause | Evidence | Effect on the percentage error of MODEL |
|---|---|---|---|
| 1 | A defect in the beat segmentation of this pipeline (not in the model): in 5 of 51 windows the beat was cut in early diastole instead of at the foot of the upstroke | Section 2 | 101.3 % -> 47.4 % when the alignment of those 5 windows is corrected |
| 2 | What remains after the correction: the model's flow index is essentially arterial compliance x pulse pressure x heart rate, and arterial compliance differs between patients (and changes within a patient) in a way that age and body size do not predict | Sections 3 to 5 | 47.4 % (34.9 to 59.0), the same as body size and age alone (50.3 %) and far from 30 % |

Ruled out as main causes: the optimiser's starting points, the residual weights, and the parameters held at
unsourced defaults (section 6). Not separable with these data: radial versus central pressure, and the true precision
of the thermodilution reference (section 7).

Correction to `RESULTS_E1.md` section 4: it attributed the five flat fits to the optimiser ("a weakness of the
calibration procedure"). That was wrong. They are the best fit of the model to a mis-segmented beat.

## 2. Layer 1: beat segmentation defect

- The five windows with a flat fitted waveform (cases 2872, 2326, 5837, 5607, 4800) have the systolic peak of their
  ensemble beat at 52 to 72 % of the cycle. In the other 46 windows it is at 8 to 30 %.
- Cause: `signals.detect_beats` defines the foot as the minimum of the low-passed signal between two systolic peaks. In
  these five recordings (heart rate 90 to 109 /min) the lowest point lies just after systole and diastole is flat or
  slightly rising, so the "foot" is placed about half a cycle early. All beats of a window are cut the same way, so
  the acceptance checks (period, pulse pressure, template correlation) pass.
- The model beat is aligned at its own minimum, which is the end of diastole. Against a measured beat that starts in
  early diastole, any pulsatile model waveform fits worse than a flat line at the mean pressure. The flat solutions
  are therefore the true optimum of the registered cost for these inputs:
  - 12 starts instead of 3: the same solutions, the same cost (2.80 to 9.78);
  - starts from the fitted parameters of the three most similar non-flat patients (pulsatile starting points, cost 11.8
    to 47.8): the fit returns to a flat solution (cost 2.80 to 10.1, model pulse pressure 1 to 12 mmHg) in all 15 runs.
- Correction tested: rotate the ensemble so that the minimum within the 30 % of the cycle before the peak is at phase
  0. It changes exactly these five windows. Refitted with the registered settings they give pulsatile fits (model
  pulse pressure 23 to 53 mmHg, cost 1.4 to 2.9) and flow indices of 4.2 to 10.0 L/min instead of 0.17 to 1.6.
- Registered estimators recomputed with the five corrected indices (n = 51):

| Estimator | Registered run | Alignment corrected |
|---|---|---|
| MODEL | 101.3 % (77.0 to 120.2) | 47.4 % (34.9 to 59.0), bias +0.07 L/min |
| B2 pulse-pressure index | 51.1 % | 51.1 % (unchanged: it does not use the alignment) |
| B1 body size and age | 50.3 % | 50.3 % |
| B0 mean of the others | 52.9 % | 52.9 % |
| PE(MODEL) - PE(B2), 95 % interval | +24.1 to +73.8 | -17.3 to +9.3 |

  With the correction the model is no longer worse than the baselines, and it is not measurably better either. The
  label by the registered rules stays NOT SUPPORTED.
- Why it was not caught: the synthetic tests use model-generated beats whose minimum is at the foot; none of the ten
  development recordings showed the pattern; the pre-registration had no check that the fitted waveform resembles the
  measured one.

## 3. Layer 2: what the model's flow index is

Alignment-corrected, 51 cases.

- The index X is close to `C_ref x pulse pressure x heart rate`: correlation of the logarithms 0.86, median ratio 1.15.
  For predicting cardiac output from pressures, the six-compartment closed loop reduces to "stroke volume = arterial
  compliance x pulse pressure". The venous, pulmonary and right-heart parts are fitted to CVP and mean PAP but do not
  inform the flow.
- X is related to the reference cardiac output (Spearman 0.56; pulse-pressure index 0.45; heart rate 0.34; age -0.31;
  body surface area 0.21; pulse pressure alone 0.21; MAP 0.11), but not in proportion: with a free exponent the
  leave-one-out fit gives CO proportional to X^0.52, not X^1. The physics of the model fixes the exponent at 1, which
  overstates differences between patients.
- The subject scale k = CO / X (equivalent to arterial compliance relative to the reference value) ranges from 0.58 to
  2.07 (quartiles 0.84, 0.93, 1.17); SD of log k is 0.267, as large as the SD of log CO itself (0.268). So after
  dividing by the model index, as much unexplained variation remains as there was to begin with.
- k is lower when pulse pressure is higher (Spearman -0.41) and when MAP is higher (-0.31); it is weakly related to age
  (-0.31) and body surface area (+0.33). Between patients, a large pulse pressure indicates a stiff arterial tree about
  as much as a large stroke volume. The model has one linear arterial compliance, and age and body size capture little
  of its variation.

Exploratory leave-one-out fits on the same 51 cases (chosen after seeing the data; optimistic by construction):

| Predictors | Percentage error |
|---|---|
| mean only | 52.9 % |
| body size, age | 50.3 % |
| registered form: X (exponent 1) + body size, age | 47.4 % |
| X with a free exponent (0.52) + body size, age | 41.7 % |
| X (exponent 1), scale also depends on pulse pressure | 43.5 % |
| X (exponent 1), scale also depends on MAP | 48.2 % |
| no model: body size, age, heart rate, pulse pressure, MAP | 46.8 % |

No variant comes near 30 %.

## 4. Layer 2 within patients: tracking between the two windows

In a change between two windows of the same patient the patient's scale cancels, so this tests the index without the
between-patient problem. 35 patients have two non-flat windows; in 17 the reference CO changed by more than 10 %.

| Index | Correlation of changes (Pearson / Spearman) | Same direction when CO changed > 10 % | Slope of CO change on index change |
|---|---|---|---|
| Model index X | 0.45 / 0.59 | 82 % (14 of 17) | 0.38 |
| Pulse-pressure index (B2 form) | 0.42 / 0.36 | 76 % | 0.44 |
| Pulse pressure x heart rate | 0.25 / 0.27 | 65 % | 0.25 |
| Heart rate alone | -0.07 / -0.05 | 53 % | -0.14 |
| MAP alone | -0.24 / -0.31 | 29 % | -0.31 |

- The model index follows the direction of change better than the simpler indices, but below the 90 to 95 %
  concordance that methodology v1 section 8 takes from Critchley 2010 for trending (that criterion was not part of E1
  and the windows were not chosen for it).
- A change in the index overstates the change in CO: slope 0.38, and the SD of (change in log CO - change in log X) is
  0.28, larger than the SD of the change in log CO itself (0.24). Assuming the index changes in proportion to CO is
  worse than assuming no change.
- So the patient's effective compliance is not constant over time either. MAP and CO change in opposite directions
  (r -0.24), which is what changes of vascular tone produce; the model's single linear compliance cannot follow them.

## 5. Systematic waveform misfit

Non-flat fits (46). Mean of (model - measured) as a percentage of the measured pulse pressure, every 10 % of the cycle
from the foot: -10, +1, -11, -3, +9, +11, +6, +1, -2, -6 (SD 3 to 11). The model is too low at the foot and at the
systolic peak, too high in mid-cycle and too low at end-diastole: it cannot produce the sharp peak and the dicrotic
region of a radial waveform. Fitted parameters relative to the defaults (median, IQR): systemic resistance 0.51
(0.44 to 0.61), LV peak elastance 0.35 (0.24 to 0.54), systolic fraction 0.44 (0.36 to 0.56), stressed volume 1.07,
RV minimum elastance 1.80, pulmonary resistance 0.05 (at its lower bound in most fits). The pulmonary resistance at
its bound means that the mean PAP cannot be matched with the left-heart filling fixed at its default; this affects the
right side of the fit, not the flow index (section 6). The size of the CO error is only weakly related to the
waveform RMSE (Spearman 0.24).

## 6. Ruled out as main causes

- Optimiser starting points: section 2 (12 starts and pulsatile starts give the same solutions).
- Residual weights: the index with equal weights differs from the registered one by a median of 0.1 %.
- Parameters fixed at unsourced defaults: 12 windows refitted with one fixed parameter changed at a time. Median
  change of the index: LV minimum elastance x2 -5.0 % (range -21.6 to +7.4 %), /2 +0.3 %; RV peak elastance x2 -0.1 %;
  venous compliance x2 0.0 %; pulmonary venous compliance x2 0.0 %; pulmonary arterial compliance x2 +0.1 %; aortic
  valve resistance x3 +0.4 % (one window +25.7 %). Changes of a few percent against a between-patient spread of the
  scale of 0.58 to 2.07.
- Bias: with the alignment corrected the bias is +0.07 L/min. The +1.47 L/min of the registered run came from the
  five flat fits.

## 7. Not separable with these data

- Radial versus central pressure. The model has one arterial node and no wave propagation; radial systolic pressure is
  amplified and the waveform differs from the central one. This may contribute to the patient-specific scale and to
  the waveform misfit, but VitalDB has no central pressure, so its share cannot be measured here.
- The reference. Thermodilution precision is assumed to be +/-20 % (Critchley and Critchley 1999). A perfect predictor
  would then show a percentage error of about 20 %. The leave-one-out mean gives 52.9 %, so most of the between-patient
  spread is real, but how much of the remaining 47 % is reference error is unknown; continuous thermodilution was not
  compared with anything else in these recordings.
- Selection. The cases received a pulmonary artery catheter; mean CO is 7.4 L/min. Whether the result would be
  different in other patients is unknown.

## 8. What follows, and what does not

- For the model: with pressures only it is a pulse-pressure method with an unknown compliance per patient. The
  methodology already cites a percentage error of 30 % or more for uncalibrated pulse-contour devices (Slagt 2014,
  cited there from a secondary reading). The corrected result (47 %) is in that range. The closed-loop structure does
  not help with this question.
- What would be needed to predict flow (hypotheses, not tested): one flow measurement per patient to set the scale,
  then a test of tracking; a pressure-dependent arterial compliance; a central pressure or a radial-to-central
  transfer step. Any of these changes the question from "pressures predict flow" to "calibrated model tracks flow".
- For the pipeline, before any further run: define the foot at the onset of the upstroke (for example the minimum in
  a fixed fraction of the cycle before the peak, or a tangent method), add a synthetic test with a waveform whose
  minimum is not at the foot, and add a pre-registered check that rejects fits whose waveform does not resemble the
  measured one.
- Not allowed to follow: reporting 47.4 % or 41.7 % as a result. The first is a correction made after seeing the
  outcome; the second was selected on the test cases. These 51 cases are no longer unseen data for this model; a
  confirmatory test of any change needs other recordings.
