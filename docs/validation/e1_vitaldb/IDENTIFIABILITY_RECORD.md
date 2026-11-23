# E1 prerequisite: identifiability from pressure observables (2026-11-23)

Status: recorded before any VitalDB file was opened. No dataset was read. Model: `src/physiosim/models/cardiovascular.py`
at `main@1124a00`. Script: `identifiability.py`; numbers: `identifiability_results.json`. This covers steps 1 and 2 of
section 5.2 of `../physiological_validation_methodology_v1.md` (structural result and local sensitivity). Step 3
(profile likelihood on synthetic data) is not done.

## Result 1: cardiac output is structurally non-identifiable from pressures

The equations are `P_i = E_i (V_i - V0_i)` and `Q = (P_up - P_down) / R` (diodes clip at zero). For any `k > 0`, the
change

- stressed volumes `(V_i - V0_i) -> k (V_i - V0_i)`, compliances `C -> k C`,
- elastances `E -> E / k`, resistances `R -> R / k`, `systolic_fraction` and heart rate unchanged

leaves every pressure unchanged at every time and multiplies every flow by `k`. This follows from the equations
(each `P_i` keeps its value; each `dV_i/dt` is multiplied by `k`, as is `V_i - V0_i`). Numerical confirmation with the
project solver, 40 cycles, all six pressures at all samples:

| k | max abs pressure difference (mmHg), default point | CO (L/min) | same, lower-pressure point | CO (L/min) |
|---|---|---|---|---|
| 0.5 | 1.1e-05 | 3.850 | 6.2e-06 | 3.593 |
| 0.7 | 5.6e-06 | 5.390 | 3.8e-06 | 5.030 |
| 1.0 | 0 | 7.699 | 0 | 7.186 |
| 1.5 | 4.5e-06 | 11.549 | 3.0e-06 | 10.779 |
| 2.0 | 6.0e-06 | 15.399 | 4.2e-06 | 14.372 |

Consequence for E1 as written in section 10 ("estimate the identifiable subset from ART waveform, CVP mean, PA mean ->
predict CO"): no set of pressure measurements, however complete, determines CO, SV or any volume in this model. A
prediction of CO needs one quantity that fixes the flow scale and that does not come from the subject's pressures.
The same holds for RV EDV and ESV (they scale with `k` up to the fixed unstressed volume).

This also corrects the expectation stated in section 5.2 of the methodology: the listed subset (`emax_lv`,
`systolic_fraction`, `C_sa`, `R_systemic`, total stressed volume, ...) is identifiable only when an independent flow or
volume measurement is among the calibration observables. With pressures alone, only scale-free combinations are
identifiable (for example `R_systemic * C_sa`, `emax_lv * C_sa`).

## Result 2: local sensitivity (16 log-parameters, 42 pressure observables)

Observables: 40 samples of `P_sa` over the final beat, mean `P_sv`, mean `P_pa`. Central differences, 2 % steps, 60
cycles. Singular values of the Jacobian (mmHg per unit log-change):

| Point | Singular values | above 1 % of the largest | above 0.1 % |
|---|---|---|---|
| default (mean P_sa 133.5, P_sv 5.3, P_pa 23.8) | 1161, 166, 117, 19.5, 8.6, 4.2, 1.5, 0.33, 0.056, 0.023, 0.001, 0, 0, 0, 0, 0 | 4 | 7 |
| lower pressure (95.2, 5.3, 23.0) | 831, 131, 88.5, 18.7, 6.6, 4.3, 0.71, 0.46, 0.070, 0.032, 0.001, 0, 0, 0, 0, 0 | 4 | 6 |

- The scaling direction lies in the null space: the Jacobian applied to it has norm 0.019 and 0.013 mmHg (largest
  singular values 1161 and 831), while `d ln CO / d ln k` along it is 1.00 and 0.97.
- At least five directions have no measurable effect on these observables. The weakest are dominated by the valve
  resistances and `C_pv`, as section 5.1 expected.
- With a noise level of the order of 1 mmHg on beat-averaged pressures, roughly four to seven parameter combinations
  are practically constrained. This is a local statement at two nominal points, not a global one.

## Not established here

- Practical identifiability under the declared measurement-noise model (profile likelihood, section 5.2 step 3).
- Whether real radial waveforms constrain the same combinations (the model has no propagation or dicrotic notch).
- Anything about agreement with data.
