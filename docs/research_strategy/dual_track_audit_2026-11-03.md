# Dual-track research baseline and evidence framework: first report (2026-11-03)

Read-only audit of `main@a0a1ef2` (`7b9e2e8` in the private repository) plus unmerged branches. Nothing was modified, committed, pushed or published to produce this report. Literature section: see [novelty_and_prior_work.md](novelty_and_prior_work.md).

## 1. Current research baseline

**Established, software level only** (117 tests pass locally with isolated Python; CI installs a wheel on Ubuntu, Python 3.12):

- Six-compartment closed-loop ODE model: volumes as states, ideal-diode valves, cosine elastance. Every parameter exploratory and unfitted. Baseline is elevated-pressure. Explicitly not a Smith 2004 reproduction.
- Independent implementation verification (`docs/independent_verification.md`): topology and constitutive oracles, conservation, unit covariance, analytic reservoir limit, tolerance refinement. Bounded milestone PASS. Strict three-beat periodicity at 1e-4 mL MIXED at canonical tolerances, passes only at fine settings. Sampling quadrature changes stroke volume by about 0.06 percent.
- Byte-identical replay of the three canonical trajectories from an installed wheel on the same host; no cross-platform identity claim.
- Semantic registry of 34 variables (OPB, Uberon primary with FMA cross-reference, GO), equality-based `validate_connection`, RDF named-graph export, `bqbiol:isPartOf` and `bqbiol:occursIn`. Anatomical node specification v2 applied (PR #4).
- 12-fixture synthetic fault-injection benchmark. Semantic: 3 correct accepts, 8 correct rejects, 1 unsafe accept. Units-only: 3, 3, 6. Accept-all: 3, 0, 9. Ground truth assigned by the validator's own authors. The unsafe accept (RV data labelled LV, 129.8 mmHg error) is retained by design.
- Smith 2004 evidence base: canonical CellML (CC BY 3.0) retained with hash; 76-variable dictionary (10 ODE states, 1 implicit algebraic septum variable, 21 algebraic, 43 parameters or initial conditions; 32 equations); OpenCOR 0.8.3 RK4 runs A, B, C with PROV-O record; SHACL shapes for OMEX Metadata 1.2 and the Smith annotations with controls; 22 violations in the PMR SemSim annotation (workspace 267: 33 structured, 57 free-text entries); SHACL result reproduced on a second machine.

**Not established:**

- No external physiological validation of anything. No parameter fitting, sensitivity, uncertainty or identifiability analysis.
- Smith reference run not compared with the paper's Figure 7. Default CVODE run failed for an unknown reason. RK4 runs show convergence order near 1, not 4, near valve switches. CellML features C3, C7, C9, C10 have no located source. kPa-versus-mmHg reading rests on a user decision (C1), not an author parameter table.
- No numeric comparison between the project model and the Smith reference (permitted since C1, not done).
- Korakianitis and Shi 2006: no file, licence record, dictionary, run or annotation in any branch; only citations inside captured third-party texts.
- Validator accepts an equation change with unchanged metadata; source context not enforced; no reasoner; no held-out task set; no human study; no comparison with SemGen or libCellML.
- Unmerged, unreviewed or partially reviewed: PR #5 draft (four-chamber M1 with passive atria and LA–mitral–LV sidecar; base snapshot marked UNREVIEWED; 30 CI failures under wheel install), PR #6 draft (graph viewer), PR #7 (skills backup), hackathon branches (LLM experiment agent; ontology-completion rounds 1 to 3d, rounds 1 and 2 privately reviewed PASS_WITH_NOTES, 3c and 3d pending; public site at medical-ontology-research.pages.dev). None of this counts as evidence for either track.

## 2. Evidence registers

See [track_a_methodological_register.md](track_a_methodological_register.md) and [track_b_discovery_register.md](track_b_discovery_register.md).

## 3. Novelty assessment (abridged)

Track A closest prior work: Gennari 2011, Neal 2014, 2015, 2019 (SemGen lineage), Shahidi 2021 and 2022 (bond graphs plus SemGen matching), CelOWS 2009, semanticSBML 2010, libCellML units checking, OMEX Metadata 1.2. None quantified fault-detection rates; Neal 2015 states no formal quantification was performed. Novel if done: a controlled fault-injection benchmark with units-only and accept-all ablations, and SHACL conformance shapes for OMEX 1.2 applied to curated repository annotations. Non-novel if claimed: "first ontology-based composition", unit-mismatch rejection as the contribution, generic semantic merging.

Track B closest prior work: Paeme 2011 and Pironet 2013 (same lineage); Sun 1997, Olansen 2000, Lumens 2009, Broomé 2013, Mynard and Smolich 2015 (already combine atria, septum, pericardium and dynamic valves). No Smith × Korakianitis–Shi hybrid found. The combination by itself is not a discovery.

## 4. Shared dependencies

Smith reference acceptance gates A4, B2 and B3. Korakianitis–Shi intake gates A5, A3 breadth and B2. One composite execution engine serves A4 and B2. Refinement, periodicity and conservation tooling, PROV-O and SHACL serve both. Registers stay separate; cross-reference by ID only. A Track A result never establishes a Track B discovery and vice versa.

## 5. Critical gaps

Track A: self-authored ground truth; no reasoner or parity arm; no comparison with SemGen or libCellML; one real model; no coupled execution; no human data. Track B: second model absent; reference not accepted against its paper; no composite; no data; no sensitivity analysis; prior art already holds the ingredients. Both: nothing physiologically validated; unreviewed branches must stay out.

## 6. Prioritised roadmap

1. Smith reference acceptance (Figure 7 digitisation, CVODE failure diagnosis, blind second implementation, the two paper experiments).
2. Korakianitis–Shi 2006 intake through the same pipeline.
3. Pre-registered Track A benchmark v2; arms: semantic, libCellML units-only, SemGen exact-match, accept-all.
4. Corpus SHACL study with blind adjudication (A3).
5. One substitution composite with refinement, cross-solver and conservation checks (A4, B2).
6. Sensitivity and identifiability on the composite; pre-registered B3 prediction; data confrontation.
7. Reasoner parity study (A2) and pilot user study (A6) only after 3 and 4.

(Superseded in order by the 2026-11-03 decision to run the model verification methodology first; see `docs/verification/`.)

## 7. Publication readiness

Track A, Nature Computational Science: not ready (one model, 12 fixtures, no reasoner, no generalisation). Realistic after roadmap items 1 to 5: PLoS Computational Biology or Bioinformatics (requires real-model data); Journal of Integrative Bioinformatics for the SHACL shapes. Track B, Nature Communications: not ready (no second model, no composite, no data). Realistic after items 1 to 6 with data: Medical Engineering and Physics, Frontiers in Physiology, AJP-Heart if mechanistic insight is shown. No acceptance probabilities estimated.

## 8. Next three actions proposed on 2026-11-03

1. Smith reference acceptance package: pre-registered quantities (aortic systolic and diastolic pressure, LV pressure range, stroke volume per beat, valve times, CO change for P_th -4 to 0 mmHg, pressures for doubled R_sys); Figure 7 digitised; blind second implementation. Accept when both implementations agree within refinement-derived error and the Figure 7 comparison is reported without a pass or fail line.
2. Korakianitis–Shi 2006 intake: canonical PMR CellML with hash and CC BY 3.0 record; three-step-size OpenCOR run; variable dictionary; comparison with the paper's E/A ratio and regurgitant flow. Accept when three runs complete with reported order, full variable coverage and a tabulated discrepancy list.
3. Track A benchmark v2 protocol: frozen and hashed before any fixture exists; fixtures from both dictionaries by someone who has not seen the validator; at least 60 fixtures across 6 families; blind adjudication; inter-rater agreement; Wilson intervals; comparators fixed.
