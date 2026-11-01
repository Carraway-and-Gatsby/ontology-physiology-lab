# Initial research report: experimental Phase 1

Generated from `results/phase1/summary.json`, `semantic_benchmark.json`, `results/reproducibility.json`, and `results/tests.xml`; not from assumed physiological outcomes. Regenerate with `python scripts/generate_report.py` after executing the experiments and tests.

## Question and claim boundary

The question is whether biomedical semantics can improve reliable model composition. This milestone tests a narrow part of it: an independently implemented, fixed-topology cardiovascular model plus annotated output-port equivalence checks. It does **not** establish arbitrary model composition, clinical reliability, patient-specific validity or improved human productivity.

The numerical core operates without an LLM. Three role-separated workstreams supplied physiology, semantic engineering and independent verification. The source/license review and equations are documented in `ecosystem.md`, `physiology.md` and `ontology.md`; the independent executed checks are in `independent_verification.md`. Earlier `verification_protocol.md` is a prospective plan, not a statement that every proposed criterion passed.

## Executed scenarios

All physiological parameters are explicitly exploratory and unfitted. The baseline is an elevated-pressure computational reference, **not a normal healthy adult**. Each scenario starts from identical initial compartment volumes. Reduced contractility halves LV Emax alone; partial restoration multiplies the impaired Emax by 1.5. Neither intervention is a drug-dose model, and these are separate parameter runs, not a timed treatment-response series.

| Scenario | LV Emax (mmHg/mL) | CO (L/min) | Forward SV (mL) | Mean systemic P (mmHg) | LV EDV (mL) | LV ESV (mL) | Mean PV P (mmHg) |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline | 2.500 | 7.6993 | 102.658 | 133.499 | 177.735 | 75.135 | 10.938 |
| reduced_contractility | 1.250 | 6.6993 | 89.325 | 116.434 | 214.082 | 124.705 | 12.999 |
| partial_contractility_restoration | 1.875 | 7.3310 | 97.746 | 127.282 | 190.919 | 93.136 | 11.685 |

Values are computed from the final complete beat. Forward SV integrates aortic flow; EDV/ESV are sampled extrema. PV pressure is a lumped pulmonary venous reservoir pressure, not an atrial measurement or a diagnosis of edema. For this parameter set, reduced LV Emax lowered output and increased ESV and PV pressure. This is a conditional mechanistic result, not a universal monotonicity theorem.

## Numerical verification and reproducibility

- Clean installed-wheel test run: **64 tests, 0 failures, 0 errors, 0 skipped**, as recorded in JUnit XML. RDFLib emits five dependency-internal deprecation warnings during the serialization round trip; they are not silently suppressed.
- Three canonical numerical CSV trajectories were rerun using the installed wheel: **all identical bytes**, with identical parsed summaries (`summary_equal=True`). This is same-host/same-dependency determinism, not cross-platform proof.
- Maximum total-volume drift across the three canonical runs: **3.18323e-11 mL**. Runtime gate: 1e-6 mL; no clipping or renormalization is used to repair volume conservation.
- Maximum final/prior-beat six-volume waveform difference: **2.29051e-05 mL**. The canonical gate is 0.1 mL. This is not the prospective criterion requiring multiple consecutive beats below 1e-4 mL.
- Solver: DOP853; 60 beats; 400 output samples/beat; relative tolerance 1e-09; absolute tolerance 1e-10 mL; maximum adaptive step T/200.
- Tests include mathematical-domain checks, conservation, valve directionality, independent incidence/constitutive checks, units, cross-solver comparisons, semantic rejection, internal regression, and end-to-end CLI failure handling. Numerical tolerance details and incomplete protocol criteria are separated in the independent report.
- Insufficiently settled two-cycle runs deliberately return exit status 2 and retain outputs labeled transient. A one-beat periodicity metric is unavailable, not zero.

The canonical CLI uses tighter settings than the core API default. Independent verification locates the default-versus-tight 0.3153 mL maximum discrepancy at 28.856 s in the systemic arterial compartment, not just during initialization. Tight solution accuracy, temporal settling and output quadrature are distinct questions; successful conservation alone proves none of them.

Independent refinement found a roughly 0.057–0.059% change in forward SV when sampling the same solution at 400 versus 1600 points per beat. Displayed digits are retained for reproducibility, not claimed physiological or quadrature precision. Trapezoidal integration at native adaptive nodes leaves whole-run local flow-balance residuals of about 6.76 mL (baseline) and 4.47 mL (reduced) even at the finest tested ODE settings. Those postprocessing failures coexist with nearly exact global state-volume conservation; stronger cumulative-flow claims are explicitly withheld.

The tight baseline fails the independent final-three-beat 1e-4 mL criterion (residuals about 2.33e-4, 7.37e-5 and 2.29e-5 mL); finer integration passes for baseline and reduced conditions. This does not invalidate the declared 0.1 mL milestone, but it leaves the stronger prospective convergence requirement incomplete.

## Semantic experiment: successes and failure

There are 34 registered variables. Exact external labels are checked against retained source evidence; aggregate compartments and several physical quantities are clearly marked local extensions. The current RDF export separates source-verified labels from project assertions.

The following **12-fixture synthetic fault-injection benchmark** is not a user study. The manual condition is scripted acceptance without a validator. The units-only condition checks dimensions and explicit scaling. The semantic condition also checks anatomy, property, reference, time context, bearer and direction. Ground-truth labels are hand-assigned, not independent held-out clinical evidence.

| Condition | Correct accepts | Correct rejects | Unsafe accepts | Incorrect rejects |
|---|---:|---:|---:|---:|
| manual | 3 | 0 | 9 | 0 |
| units_only | 3 | 3 | 6 | 0 |
| semantic | 3 | 8 | 1 | 0 |

The semantic layer rejects wrong-anatomy pressure connections that dimensions alone accept. Explicit mmHg-to-Pa and mL/s-to-L/min conversion is supported and actually applied to numeric values. The integration tests verify that the report's semantically transferred cardiac output agrees with the direct numerical metric within floating-point roundoff.

**Known failure:** correct-looking LV metadata attached to actual RV pressure is accepted. The unsafe transfer was exercised with computed arrays; its maximum error against the intended LV pressure was **129.793 mmHg**. This is an output-port corruption experiment, not a modified ODE integration. It demonstrates why metadata provenance and executable field binding need independent review.

The independent reviewer also found that two endpoints with equally missing anatomy identifiers or references could be accepted. A regression test first reproduced the bug, then required-field and flow-orientation checks were added. The original review snapshot remains unchanged; `results/independent/c_verify_results.json` records the post-fix rerun. Equation strings and free-text source contexts still do not establish mathematical/model-assumption compatibility.

Human integration effort was **not measured**. Changes in solver stability or conservation under dynamically composed models were **not measured**, because the model topology is fixed. General semantic connection accuracy and automatic anatomical equivalence remain unestablished.

## Artifacts and limitations

Open `../results/phase1/index.html` for plots, parameters and annotations. CSV, JSON and TriG exports plus output/source checksums are in that directory. `results/tests.xml` and `results/reproducibility.json` record executable evidence. `requirements.lock` pins the dependency environment and `dist/` contains the built wheel.

No external reference trajectory has been reproduced; no physiological parameter estimation, patient data, confidence intervals, identifiability analysis or clinical validation are claimed. Numerical domain checks are not physiological range validation. The model omits separate atria, nonlinear passive ventricular mechanics, septal/pericardial interaction, valve inertia, baroreflex, respiratory and renal feedback, and drug pharmacology. The entire prospective verification plan is not complete.

The existing external cardiac simulator was accessible and reviewed, but no external engine was executed or incorporated. Its eight-state architecture is not silently treated as equivalent to this six-state model. Artifact-specific license restrictions are documented. The Smith 2004 CellML captures fall under the Physiome Model Repository CC BY 3.0 statement and may be redistributed with the attribution recorded in physiology.md; the originally parsed workspace-267 capture lacks all parameter and initial values, so only the canonical exposure file can serve as a reference simulation input.

## Next scientifically justified step

1. Reproduce one explicitly licensed reference model/parameter set with an independently generated reference trajectory; retain the current exploratory baseline rather than relabeling it healthy.
2. Strengthen periodic stopping, native adaptive-step diagnostics, valve-event timing and quadrature refinement; quantify sensitivity and parameter uncertainty before interpreting clinical phenotypes.
3. Expand the semantic benchmark with independently authored held-out tasks, model-version provenance and binding checks. Test a small actual coupled component, not just descriptors, before claims of general model composition.
4. Only then introduce a minimal renal perfusion/fluid-balance research module. Define arterial/venous pressure inputs, renal-flow output, volume input/elimination terms and exact units. Replace closed-loop conservation with an explicitly tested source-minus-sink inventory law. GFR, sodium balance, RAAS and clinical drug response require further sourced models and are not implemented.
