# E1 post hoc analysis: window rule with full beat acceptance in the heart-rate bins (2026-11-23)

Status: post hoc. Made after the registered TEST result was known, in response to a review finding on PR #11 of [private repository]. It does
not replace the registered result in `RESULTS_E1.md` and cannot change its verdict. Written by Claude (Mythos 5.2);
not reviewed by a human.

## The discrepancy

`PREREGISTRATION_E1.md` section 4 item 4: "Heart rate from accepted beats, in 10-s bins". Section 5 defines an
accepted beat by five conditions (no missing sample, pressure ranges, period within +/-20 % of the median, pulse
pressure within 0.5 to 1.5 times the median, correlation of at least 0.90 with the median shape). The code that ran
(`signals.window_report` at 74e1928) formed the bins from `Beats.accepted`, which holds only the first two conditions
(and, since the development fix, the 10 mmHg minimum pulse pressure). The last three conditions were applied only in
the 120-s analysis segment. A beat rejected for its period, pulse-pressure ratio or shape could therefore count
towards bin coverage and enter a bin's median heart rate.

## The variant

`signals.RULE["hr_bins_full_acceptance"]` (default False = the registered behaviour). With True, the full acceptance
is evaluated over the beats of the 600-s window (medians and template of that window) and only fully accepted beats
enter the bins. Driver flag: `run_e1.py features --posthoc-full-acceptance`; results in
`results/e1_vitaldb/test_posthoc_full_acceptance/`. Code at 3718a9e. Checks: with the default, the new code reproduces
the registered window selection of all 60 cases exactly; a synthetic test separates the two behaviours.
Fits were reused from the registered run for the 85 windows whose features are identical; 9 windows were fitted anew.

## Result

| | Registered run | Post hoc variant |
|---|---|---|
| Cases with W1 / with W2 | 51 / 42 | 51 / 43 |
| Cases whose W1 differs | - | 2 (55, 5682) |
| Cases whose W2 differs or is new | - | 7 (55, 397, 2326, 2332, 2738, 5304, 5687) |
| MODEL percentage error | 101.3 % (77.0 to 120.2) | 99.2 % (74.4 to 118.2) |
| B2 / B1 / B0 percentage error | 51.1 / 50.3 / 52.9 % | 47.7 / 51.5 / 52.1 % |
| PE(MODEL) - PE(B2), 95 % interval | +24.1 to +73.8 | +25.4 to +74.9 |
| MODEL bias (95 % interval), L/min | +1.47 (+0.42 to +2.53) | +1.48 (+0.44 to +2.52) |
| 20 % of mean reference CO, L/min | 1.485 | 1.505 |
| Label by the registered rules | NOT SUPPORTED | NOT SUPPORTED |
| W2 percentage error | 97.5 % (n 42) | 99.2 % (n 43) |

The discrepancy changes which window is used in a few cases and does not change any conclusion.
