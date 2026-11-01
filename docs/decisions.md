# Architectural and scientific decision record

- Scope: Phase 1 six-compartment, closed-loop, deterministic ODE prototype. No patient data, remote deployment, or clinical prediction.
- Independently developed model and annotations. External source code is not executed. Source/license review is delegated separately.
- Compartment volumes are state variables; pressure and flow are algebraic observables. This permits direct conservation auditing.
- Ontology annotations describe mathematical variables; annotations alone do not establish biological compatibility or model validity.
- Local concepts must be explicitly distinguished from verified external ontology concepts.
- Baseline and reduced-contractility experiments use the same numerical engine, not adjusted outputs.
- Mechanistic intervention effects are parameter changes, not drug-dose predictions.
- Verification distinguishes implementation correctness, broad plausibility, and external biological validation. The latter is not established by this milestone.
- Renal feedback and clinical therapy models are deferred until the cardiovascular core passes verification.
- Roles: Agent A model/equation implementation; Agent B semantic implementation; Agent C independent scientific source review, followed by independent code verification; parent integration and reproducibility.
- Canonical experiment: 60 cycles, DOP853 rtol=1e-9, atol=1e-10 mL, max step T/200, 400 output samples/cycle. This is tighter than the core API defaults; full default-tolerance transients showed a non-negligible refinement difference.
- Milestone periodicity gate: <=0.1 mL last/prior-beat six-volume waveform difference. The broader prospective 1e-4 mL for multiple successive beats is not silently substituted or claimed complete.
- Integration review corrected SV annotation to the actual flow-integrated metric, added executable numeric bindings, and limited gauge-pressure references to pressure variables.
- Synthetic benchmark deliberately retains a false acceptance: actual RV output with falsely assigned LV metadata. Metadata validation is not numerical provenance validation.
- Package was built as a wheel, installed in a separate environment, and executed twice in isolated Python mode. Numerical CSV replay and parsed summaries matched exactly on this host; no cross-platform identity claim.
- Smith 2004 OpenCOR reference run (2026-11-01, user-approved): fixed-step RK4 replaces CVODE only, because the default run failed with a KINSOL iteration-limit error. KINSOL, model, parameters and units are unchanged; results are labelled RK4 and do not explain the CVODE failure.
- Smith 2004 run comparison (2026-11-01, user-approved): output times are treated as equal when |dt| <= 1e-9 s (far below the 5e-6 s smaller step). Applies to the time axis only; raw CSVs are not altered, and the tolerance was fixed before inspecting value differences.
- Current numerical baseline is elevated-pressure and all default values remain exploratory; no tuning was performed to manufacture normality or positive findings.
