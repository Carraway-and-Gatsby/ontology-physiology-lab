# Research Gate 1: independent evidence and model feasibility (2026-11-03, read-only)

Baseline `main@a0a1ef2` (`7b9e2e8` in the private repository). Verdict: Track A can become a falsifiable study only if the central question is asked honestly; today's validator is itself a hard-coded rule set, so the "ontology advantage" arm does not yet exist. Track B is BLOCKED at the reference-model stage: the Smith reference is not accepted against its paper, and the Korakianitis–Shi CellML is a simplified encoding whose valve dynamics differ from the paper. Superseding order of work (decided the same day): run the model verification methodology (`docs/verification/`) before either track.

## A. Independent benchmark specification (Track A)

**Universe.** Real annotated models, not the project registry. In-sample: Smith 2004 canonical CellML (76 variables, 32 equations) and the Korakianitis–Shi 2006 CellML (16 files, parameters in ParaHeart, ParaSys, ParaPul). Held-out, sealed until validators are frozen: Heldt 2002 (PMR CellML, CC BY 3.0, ODE, plus an independent C implementation on PhysioNet). Fixture types: within-model pairs, cross-model pairs, model-to-consumer-port pairs.

**Fault families, each with an independent source of truth.** (1) Physical property mismatch with equal dimensions. (2) Anatomy or compartment mismatch including named-lumen versus lumped-bed granularity. (3) Flow orientation reversal. (4) Reference or external-pressure mismatch from the Smith equations (chamber versus free-wall pressure, case R1). (5) Temporal aggregation mismatch. (6) Units: dimension error, missing scale, real mislabelled unit (kPa labels on mmHg values, C1). (7) Lumping: Smith venous compartment includes the atrium versus a separate Korakianitis–Shi atrium. (8) Overdetermination: two formulations of one quantity feeding a third (Neal 2015). (9) Payload provenance: correct metadata on the wrong numeric column (undetectable by metadata alone). (10) Valid with explicit conversion. (11) Valid identity. (12) Undecidable from annotation alone; correct output is abstention.

**Reference standard independent of the system under test.** Truth from primary artefacts: model equations, Smith author manuscript, Korakianitis–Shi paper, OPB and Uberon or FMA definitions, CellML 2.0 unit rules, documented real defects (22 SHACL violations in workspace 267; post-merge adjustments in Neal 2015). Two adjudicators with physiology or modelling background, blind to validator output, apply a written rubric citing an equation or definition per decision; a third resolves disagreement; Cohen's kappa reported. Validator authors neither write nor adjudicate fixtures.

**Sealing order.** Validator code frozen by commit hash first; fixtures authored afterwards by someone who has not read the validator, hashed, then unsealed. R1 to R13 are calibration only and excluded from the test set.

**Size and power.** Target at least 120 fixtures: at least 60 invalid across at least 8 families, at least 40 valid, at least 20 undecidable (design choice, not a sourced threshold). A paired power calculation (McNemar on discordant pairs) is recorded before unsealing.

**Negative and adversarial controls.** Valid pairs that look suspicious (same quantity, different names; cross-ontology identifiers via the Uberon–FMA bridge); unit aliases; subclass and part-of near misses; namespace lookalikes; label swaps; mutated equations with unchanged metadata.

**Reproducibility.** Pinned environments; fixture and code hashes; full confusion tables with denominators; replay on a second machine; artefacts in a DOI-minting repository.

## B. Matched-baseline comparison protocol

| Arm | What it is | Status |
|---|---|---|
| 0 Accept-all | Scripted manual baseline | Exists |
| 1 Units-only | Dimensional check plus explicit scale contract (libCellML or Modelica class) | Exists as Pint check; libCellML reads CellML 2.0 only |
| 2 Hard-coded rules | Exact string or IRI equality on property, anatomy, orientation, reference, temporal context, bearer, units | This is the current `validate_connection`; it is the rule-based arm, not the ontology arm |
| 3 Ontology-aware | Same fields resolved through ontology structure: Uberon–FMA cross-references, subsumption and part-of chains, OPB dependency classes, lumping via hasPart | Does not exist |
| 4 SemGen exact-match merger | Headless Py4J API, release 4.3.2, non-commercial licence acceptable for research | CellML 1.1 handling unconfirmed |
| 5 Human pilot | Optional, pre-registered, timed, small | Not started |

Matching rules: identical fixtures and inputs; one output vocabulary (ACCEPT, REJECT with reason, ABSTAIN); equal logged implementation time for arms 2 and 3; arm authors blind to fixtures; parity review before freezing. Metrics with Wilson 95 percent intervals and per-family breakdown: sensitivity, specificity, false-positive and false-negative rates, abstention rate under a declared policy, integration success (accepted connections that execute with conservation and refinement intact), human effort (pilot only, including annotation authoring time), computational overhead, two-machine reproducibility. Arm differences by paired McNemar. Minimal important difference declared before unsealing. Numerical consistency after semantic validation: every accepted executable connection is executed and compared against the unconnected originals with tolerance refinement, cross-solver agreement and conservation; payload-class faults checked by provenance chain plus numeric replay.

Failure criterion for the primary question: if arm 3's false-negative interval overlaps arm 2's and no family is detected by arm 3 alone, report "no measurable advantage over equivalent rules" and mark A2 REFUTED.

## C. Ontology-specific contributions and their falsification

- Cross-ontology identity (Uberon on one side, FMA on the other): exact matching rejects valid pairs; reasoning over the bridge accepts. Falsified if arm 2 with a static synonym table matches arm 3.
- Partonomy and granularity (blood in LV cavity versus LV organ; lumped venous bed containing an atrium): reasoning returns "related, not identical" and abstains. Falsified if abstention precision is no better than arm 2.
- Overdetermination through OPB dependency classes: requires a dependency graph. Falsified if a hand-written dependency check catches the family equally.
- Not a contribution: property, anatomy, orientation, temporal and reference equality checks (typed schema); unit checks (libCellML, Pint); identifier version drift (provenance).

Expected: any advantage shows only on heterogeneous cross-model pairs. If none survives, the publishable result is the bounded negative finding plus the SHACL shapes as a semantic quality-control instrument.

## D. Published model feasibility matrix (Track B)

| Model | Equations and source | Provenance and licence | Solver | Parameters and ICs | Published reference outputs | Independent implementation | Feasibility without touching the Phase 1 model |
|---|---|---|---|---|---|---|---|
| Smith 2004 | Canonical CellML 1.0, 14 components, retained with hash; author manuscript read | PMR exposure, translated from authors' Matlab, CC BY 3.0 | ODE plus one nonlinear algebraic septum equation (KINSOL); piecewise valve law; 14 beats encoded | Complete in CellML; none in paper; partial in Paeme 2011; thesis Tables 1 to 3 (private-study rights) | Abstract numbers; Figure 7 not digitised | OpenCOR RK4 runs (default CVODE failed, cause unknown); scipy re-implementation not independent | HIGH as separate reproduction; blocked by CVODE failure, unsourced C3, C7, C9, C1 decision |
| Korakianitis–Shi 2006 | CellML 1.1 with imports (Shi and Hose encoding); original C code | PMR exposure c49d416a..., CC BY 3.0 | ODE in CellML; valve dynamics simplified relative to the original | In three parameter files; paper tables unconfirmed, paper paywalled | None on exposure; paper figures not open | None found | MEDIUM: the CellML is reproducible but is not the paper's model; fidelity audit needed |
| Heldt 2002 | PMR CellML plus CVSim C code | CC BY 3.0 and Open Data Commons Attribution | ODE, runs in COR | In both implementations | Exposure states it reproduces published results | Two independent implementations | HIGH; best held-out generalisation model and reproduction exemplar |
| Pulse engine | Large C++ circuit engine | Apache 2.0 | Circuit solver | Internal | Validation tables; heart failure not validated | Itself | MEDIUM as black-box comparator only |
| CircAdapt | Framework wheel, no PyPI | EULA forbids modification and derivatives; revocable | ODE | Internal | Published | Itself | LOW for composition |
| Burkhoff and Tyberg 1993 | Paper only, paywalled | No CellML found | ODE | Unconfirmed | In paper | None | LOW to MEDIUM |
| Mynard and Smolich 2015 | Paper; code unconfirmed | n/a | ODE plus 1D network | n/a | In paper | None | LOW |
| Paeme 2011, Pironet 2013 | Open text; Pironet MATLAB under CC BY | CC BY | ODE | Partial tables; Pironet set is a dog sarcomere model | Yes | Yes | Parameter cross-checks only |

Tooling constraints: libCellML 0.7.2 is CellML 2.0 only; OpenCOR 0.8.3 archived but exposes solver settings through Python; SemGen CellML 1.1 handling unconfirmed.

## E. Prerequisites and acceptance criteria for independent numerical reproduction

1. Canonical source file with hash, changeset, licence and attribution record.
2. Complete parameter and initial-condition table with per-value provenance and unit resolution from the authors' text.
3. Documented solver requirements (Smith: nonlinear algebraic solve per step plus event-aware valve switching; Korakianitis–Shi CellML: ODE, paper valve model may not be).
4. Pre-registered quantities of interest (Smith: aortic systolic and diastolic pressure, LV pressure range, stroke volume per beat, valve timing, P_th and R_sys experiments; Korakianitis–Shi: E/A ratio, regurgitant closure flow).
5. Tolerances derived, not invented: implementation-to-implementation agreement within combined numerical uncertainty from step refinement; paper agreement reported against digitisation uncertainty with no pass or fail line unless a sourced context-of-use tolerance exists.
6. Two independent implementations by different authors, blind, different solver families, observed convergence order reported.
7. Limit-cycle criterion under refinement; conservation; pinned environments; two-machine replay.
8. Evidence categories kept separate: software verification, model reproduction, scientific validation (not attempted), comparative methodological evidence, novel contribution.

## F. Critical blockers (dependency first, then scientific weight)

1. Smith reference not accepted (CVODE failure, Figure 7, unsourced features). Gates all of Track B and A4.
2. Korakianitis–Shi paper inaccessible; CellML simplifies valve dynamics. Gates the second model.
3. No independent fixture author or adjudicators identified. Gates Track A credibility.
4. No ontology-aware validator arm; the current validator is the rule-based control.
5. Tooling: libCellML 2.0-only, OpenCOR archived, SemGen headless path unconfirmed.
6. No identified accessible physiological dataset for any Track B prediction.
7. Unreviewed branches must stay outside both evidence bases; PR #5 fails CI under wheel install.
8. No parameter crosswalk between Smith and Korakianitis–Shi exists even on paper.

## G. Highest-information experiments (each needs approval)

Track A. **A-G1 re-expression test**: hypothesis that the ontology-aware arm detects nothing the equal-effort rule arm misses; sealed blind-adjudicated fixtures; per-family detection matrix, paired McNemar; confounders: leakage from R1 to R13, unequal effort, adjudicator anchoring; failure: identical detection sets, A2 REFUTED. **A-G2 corpus semantic quality control**: shapes applied to the other 42 workspace-267 models and BioModels OMEX annotations; two blind adjudicators label each flag defect, style or false alarm; precision floor set in a pilot; confounders: shapes designed on Smith, pre-OMEX form counted as style; failure: precision interval below the floor. **A-G3 held-out generalisation**: Heldt 2002 and Smith × Korakianitis–Shi cross-model pairs; error rates not worse than in-sample by more than a pre-set margin; confounder: annotation sparsity (57 of 90 Smith entries free text); failure: degradation beyond the margin.

Track B. **B-G1 Smith reference acceptance**: Figure 7 digitised, CVODE failure diagnosed, blind second implementation, P_th and R_sys experiments; confounders: CellML differs from paper (C3, C7, C9, C11), C1 units, 14-beat encoding; failure: unexplained discrepancy, CellML blocked as reference. **B-G2 Korakianitis–Shi fidelity audit**: obtain the paper, diff CellML against paper equations, three step sizes in OpenCOR with CVODE, compare E/A and regurgitant flows; failure: defining valve dynamics absent. **B-G3 integration desk study**: paper-only crosswalk, identifiability sketch, dataset inventory, novelty check against Mynard and Smolich 2015 and Broomé 2013; failure: no accessible dataset or no prediction beyond prior art, discovery route BLOCKED.

## H. Gate criteria

- **Track A PASS**: protocol frozen and hashed; one independent fixture author and two blind adjudicators confirmed; ontology-aware arm specified and parity-reviewed; power calculation recorded; Heldt 2002 sealed; SemGen arm included or documented as BLOCKED. **BLOCKED**: no adjudicators, or A-G1 shows identical detection sets with no plausible ontology-only family left (write the negative result instead). **INSUFFICIENT_EVIDENCE**: pilot kappa below 0.6 or fewer fixtures than the power calculation requires.
- **Track B PASS to coupling**: B-G1 and B-G2 accepted; composite specification and crosswalk written; pre-registered prediction with confirmed dataset access. **BLOCKED**: Smith CellML cannot be reconciled with the paper, or Korakianitis–Shi CellML lacks the valve dynamics, or no dataset. **INSUFFICIENT_EVIDENCE**: only one reference accepted.
- **Both**: journal targets remain aspirational; Nature Portfolio requires code during review and a data-availability statement.

Resourcing decisions that are the owner's: library access to the Korakianitis–Shi paper, naming independent adjudicators, approving the Smith acceptance package.
