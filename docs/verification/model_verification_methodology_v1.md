# Model Verification Methodology, Version 1 (design only, 2026-11-03)

Question: does the currently implemented mathematical and computational model correctly solve the equations it claims to implement, within demonstrable numerical uncertainty? This document designs the verification; it does not declare anything verified and it does not modify the model.

Baseline confirmed: `main@7b9e2e82715ce4a2322e15520e7e670ef233ed8a`, clean working tree, no stash. SHA-256 of the files under verification: `models/cardiovascular.py` 41be2225…3492, `simulation/__init__.py` 615a83da…67e2, `simulation/_hybrid.py` 6c413537…cc77, `validation/__init__.py` 37cb257a…0c53, `experiments/runner.py` 97c05606…2f82. Installed solver: SciPy 1.17.1 (DOP853 order 8, error-estimator order 7, RMS error norm; event roots by brentq with xtol = rtol = 4·eps on the dense output, `_ivp/ivp.py:52-57`). NumPy 2.4.6, Python 3.11.15. Test count 117 = cardiovascular 24, hybrid 15, cumulative 13, periodicity 24, validation 7, interventions 8, independent 12, experiments 2, ontology 8, semantic binding 4.

**Headline findings.** (1) The integrated system is not literally the clipped-flow ODE the documentation describes: the integrator solves a hybrid system of smooth valve regimes joined by event location, and the clipped law lives only in post-processing. (2) No Level-3 independent implementation exists; the "independent" evidence generator calls the production right-hand side and `simulate`. (3) Valve event times are never checked. (4) Several test thresholds were set from the implementation's own measured behaviour and are regression bounds, not verification criteria.

**Framework.** ASME V&V 10-2019 (code verification concepts), ASME V&V 20-2009 (solution verification, Richardson-based uncertainty), ASME V&V 40-2018 and the FDA final guidance of November 2023 (docket FDA-2021-D-0980) for risk-informed, context-of-use framing, NASA-STD-7009A for credibility reporting. Numerical-method references: Roache (grid convergence index), Oberkampf and Roy (verification text), Salari and Knupp (manufactured solutions), Shampine and Thompson (event location), Dieci and Lopez (discontinuous ODEs). Standards confirmed by web lookup 2026-11-03; the last four cited from standard knowledge, bibliographic records to be checked before manuscript use. No regulatory compliance or certification is claimed.

Evidence categories kept separate: A mathematical specification verification; B code verification; C solution verification; D numerical uncertainty quantification; E physiological validation (outside this methodology; never inferred from A to D).

## Deliverable A. Formal model inventory (confirmed against source)

States: six total compartment volumes in mL, order `(lv, sa, sv, rv, pa, pv)` (`cardiovascular.py:10`); optional six auxiliary cumulative edge flows in mL.

Parameters (dataclass `cardiovascular.py:14-40`, all exploratory): heart rate 75 per min; LV elastance 0.06 to 2.5 mmHg/mL; RV elastance 0.03 to 0.8 mmHg/mL; systolic fraction 0.4; compliances 1.5, 100, 5, 20 mL/mmHg (sa, sv, pa, pv); resistances 0.01, 1.0, 0.01, 0.01, 0.1, 0.01 mmHg·s/mL (aortic, systemic, tricuspid, pulmonary valve, pulmonary, mitral); unstressed volumes (10, 700, 2500, 10, 100, 400) mL; initial volumes (140, 850, 3200, 140, 180, 490) mL, total 5000 mL. Admissibility enforced: finite positive scalars, 0 < s < 1, Emax >= Emin, six finite volumes, initial positive, unstressed nonnegative.

### Equation-to-code traceability matrix

| ID | Equation as implemented | Location | Interpretation and constraints |
|---|---|---|---|
| E1 | T = 60 / HR | `cardiovascular.py:58-61` | Cycle length, s |
| E2 | phi = (t mod T)/T; a(phi) = (1 − cos(2π phi/s))/2 for phi < s, else 0 | `cardiovascular.py:63-73` | a in [0,1]; a and a' vanish at phi = 0 and phi = s; a'' jumps (C1, not C2) |
| E3 | E_v(t) = Emin_v + (Emax_v − Emin_v)·a, v in {lv, rv} | `cardiovascular.py:70-73` | Synchronous LV and RV activation |
| E4 | P_i = k_i(t)(V_i − V0_i); k = E_v for ventricles, 1/C_i for vessels | `cardiovascular.py:76-83` | Gauge relative to an implicit external pressure of exactly 0; no parameter; negative pressure admissible when V < V0 |
| E5 | q_k = (P_k − P_{k+1 mod 6})/R_k, k = 0..5 | `cardiovascular.py:98` | Directed ring lv→sa→sv→rv→pa→pv→lv |
| E6 | q_k := max(q_k, 0) for k in {0, 2, 3, 5} | `cardiovascular.py:99` | Ideal diodes (aortic, tricuspid, pulmonary, mitral); beds signed |
| E7 | dV_i/dt = q_{i−1 mod 6} − q_i | `cardiovascular.py:103-106` | Mass balance; symbolic sum identically 0 |
| E8 | Regime RHS: q_k unclipped if valve k "open", 0 if "closed" | `_hybrid.py:82-87` | What is actually integrated; equals E5+E6 only at exactly located roots |
| E9 | Event g_k = P_k − P_{k+1}, terminal; direction −1 when open, +1 when closed; g == 0 replaced by ±eps sentinel | `_hybrid.py:89-102` | Roots: brentq, xtol = rtol = 4·eps |
| E10 | Tie disambiguation by forward-Euler probe of length min(√eps·T, half remaining interval) | `_hybrid.py:17-43` | Chooses right-hand regime; never advances state |
| E11 | Integration restarts at sT/2, sT and T each beat | `_hybrid.py:71-74` | Checkpoints for C1 boundaries and pulse peak |
| E12 | dC_k/dt = q_k per regime; offsets accumulated | `_hybrid.py:87,119,123` | Auxiliary integrals; same atol as volumes |
| E13 | Outputs: V from dense output at sample times; P = E4(V); Q = E5+E6(P) | `simulation/__init__.py:158-160` | Reported flows clipped even where E8 integrated an unclipped value |
| E14 | SV = trapezoid of Q_aortic over last beat; CO = SV/duration; EDV, ESV sampled extrema; mean pressures by trapezoid; beat difference = max over six volumes, last vs previous beat | `simulation/__init__.py:35-63` | Post-processing with its own quadrature and sampling error |
| E15 | Local balance residual V − V(0) − (C_in − C_out) | `simulation/__init__.py:69-83` | Linear invariant of the augmented ODE; wiring and roundoff only |
| E16 | Runtime audit: finite, increasing time, V > 0, no reverse valve flow, total drift <= 1e-6 mL | `validation/__init__.py:5-24` | Observational gate, no projection |

Solver configuration. API default: DOP853, rtol 1e-7, atol 1e-8 mL, max step T/100 (`simulation/__init__.py:116-119,157`). Canonical: rtol 1e-9, atol 1e-10, max step T/200, 60 beats, 400 samples per beat (`runner.py:22-23`, `experiments/phase1.json`). Error norm RMS over all states, so auxiliary integrals dilute volume error control when enabled. Dense output used for sampling and event roots. Guard raises after eight consecutive zero-length events.

### Specification ambiguities to resolve in a frozen specification (not inferred from code)

1. Which system is "the model": the continuous clipped ODE (E5 to E7, Lipschitz RHS, unique classical solution) or the hybrid regime system (E8 to E11). Recommendation: declare the clipped ODE as the mathematical model and the hybrid scheme as a numerical method whose convergence must be demonstrated.
2. Behaviour on g_k = 0 over an interval (zero-flow equilibria): both branches give zero flow; the sentinel (E9) and probe (E10) are numerical devices needing a stated rule.
3. Reported versus integrated flow (E13 vs E8): difference at a located root bounded by |g_k'(t*)|·δt/R_k with δt about 4·eps·t; must be stated and tested.
4. Floating-point modulo in E2 near beat boundaries: phase may evaluate to T − ulp instead of 0; activation is 0 either way; write it down.
5. Initial regime decided by strict inequality (`_hybrid.py:63`); a zero initial gap is "closed".
6. Implicit zero external pressure in E4 is a convention with no parameter.
7. The beat-difference in E14 is a numerical settling diagnostic, not a limit-cycle criterion.

## Deliverable B. Mathematical verification matrix

| Equation | Verification method | Independent oracle | Constraint | Existing evidence (status) | Gap |
|---|---|---|---|---|---|
| E1 to E3 | Point and property checks: extrema, period, zero value and slope at phi = 0 and s, jump of a'', algebraic equivalence with sin² form | Hand-derived values; sin²(π phi/s) identity | 0 <= a <= 1, periodic, C1 | Extrema and period point-checked; sin² and cos² equivalences used (PARTIALLY_VERIFIED) | Slope continuity at boundaries, modulo edge NOT_TESTED |
| E4 | Zero pressure at V0, dP/dV = k; unit covariance | Hand arithmetic; Pint-scaled parameters | Negative pressure admissible, not clipped | One-state point check; unit covariance with negative control (VERIFIED, Level 1) | None material |
| E5, E6 | Per-edge gradient sweep incl. tiny and zero; q·ΔP >= 0 | Explicit edge list and resistances | Diodes nonnegative; beds signed | Five gradients (VERIFIED, Level 1) | No parameter-extreme sweep |
| E7 | Assembly vs explicit incidence matrix; mutation controls | Explicit `INCIDENCE` in `docs/evidence/c_verify_run.py` | Column sums zero; endpoint identity | 80 seeded states, mutations rejected (VERIFIED, Level 1) | Shared parameter interpretation; cannot detect a common unit misreading |
| E8 to E11 | Convergence of hybrid scheme to clipped ODE; event-time convergence; regime-vs-clipped consistency; tie handling | Single-solve `solve_ivp` on clipped RHS at fine tolerance; fixed-step reference with bisection events (Level 3); expm reference for the all-open regime | Order reduction at kinks bounded and reported | Public API vs single-solve fine agreement recorded (PARTIALLY_VERIFIED, same RHS); symmetry and chatter tests pass | Event times NOT_TESTED; observed order across an event NOT_TESTED; tie logic beyond symmetric case NOT_TESTED |
| E12, E15 | Invariant residual; refinement of integrals; monotonicity | Explicit incidence; refinement ladder | Residual at eps·|C|; monotone valve integrals at fine tolerance | Residual <= 1e-6 mL, refinement 1e-5 mL, monotone at fine settings (PARTIALLY_VERIFIED; thresholds from measured behaviour) | No order estimate; dense-output undershoot not bounded analytically |
| E13 | Sampled values equal dense output; sampling independence | Exact equality across densities | Sampling cannot alter trajectory | Exact (VERIFIED) | Clipped-vs-regime flow difference at roots NOT_TESTED |
| E14 | Synthetic arrays with hand-computed metrics; quadrature refinement | Hand arithmetic; cumulative states | Trapezoid error h² away from kinks | Synthetic test (VERIFIED for definitions); 400 vs 1600 samples differ about 0.06 percent | Event-defined EDV and ESV absent; no uncertainty attached to reported digits |
| E16 | Fault injection on synthetic arrays | Hand-built faults | Audit rejects, never repairs | VERIFIED (utility) | None |
| Conservation (sum of E7) | Identity preserved by any RK method | Derivation | Drift at roundoff floor | About 1e-11 mL (VERIFIED as identity; weak as code evidence) | Cannot detect wrong topology; not code verification |

## Deliverable C. Numerical verification protocol

**N1 Solver convergence.** Ladder A: rtol 1e-5 to 1e-13 in decades, atol = rtol/10 mL, fixed max step T/400. Ladder B: max step T/25 to T/1600 at fixed rtol 1e-12. Ladder C: forced fixed steps (large rtol so every step is accepted; accepted steps verified from the returned grid) to obtain an observed order. Quantities of interest with their own error metrics: six volume trajectories (max norm per compartment), pressures, flows (away from roots and within one step of roots), six cumulative integrals, eight valve event times per beat, E14 metrics. Uncertainty: observed order p from three levels where differences shrink monotonically (asymptotic-range check), Richardson estimate with safety factor 1.25 (three levels) or 3 (two levels), following grid-convergence-index practice; where the asymptotic check fails, report the raw difference to the finest level and mark INCONCLUSIVE.

**N2 Independent solver comparison.** Within the production RHS: DOP853, Radau, LSODA at matched tolerances, labelled solver agreement only. Genuine independence only from the Level-3 implementation (different solver family, no shared code).

**N3 Analytical reference problems derived from the model.** (a) Zero-flow equilibrium (exists). (b) Two passive reservoirs, exponential rate (1/C_sa + 1/C_sv)/R_sys (exists at loose RK23 tolerances; rerun across a step ladder with observed order). (c) New, strongest: all-valves-open linear regime with constant elastances, dV/dt = A V + b, exact by matrix exponential; initial state with every gap strictly positive; exact first event time from the exponential solution; compare production trajectory up to that time; reference uncertainty cond(A)·eps. (d) Time-varying elastance with closed valves: volume constant, pressure follows E3; tests E11 checkpoints. (e) Single ventricle ejecting through a diode into one reservoir with piecewise-constant elastance: exact piecewise exponential with analytic closing time; the one analytic case with a real valve event.

**N4 Manufactured solutions.** Appropriate within a smooth regime only. Separate harness importing the constitutive functions and the regime RHS, adding g(t) = dV_m/dt − f(t, V_m) for a smooth V_m keeping every gap strictly signed; measure observed order. The production `rhs` and `integrate` have no source hook, so the harness is separate code; it verifies integrator and assembly. Across a valve switch MMS is not appropriate; event-time verification (N5) replaces it. No MMS result verifies physiology.

**N5 Discontinuities and events.** The clipped RHS is continuous with kinks on g_k = 0; one-step methods crossing a kink without event location lose local order. Tests: observed order of the hybrid scheme across one isolated event vs the same problem without events; event-time convergence under N1; root-residual bound (ambiguity 3); event count per beat in steady state (expected 8) and zero-length events; max-step sweep on the pulse-peak checkpoint case; tie cases with g_k = 0 exactly at a checkpoint.

**N6 Periodic versus transient.** Beat-to-beat map V(kT) → V((k+1)T) as a Poincaré map; report d_k (max-norm distance between successive beats) and contraction ratio r_k = d_{k+1}/d_k. Criterion derived, not chosen: periodic to numerical precision when d_k falls below the refinement-derived trajectory uncertainty for the number of beats implied by r_k, with r_k < 1. Existing evidence shows residuals at canonical tolerances are dominated by integration error and non-monotone, so assess only at tolerance levels whose uncertainty floor is below the target. Basin probe: perturbed initial distributions at fixed total volume. If r_k does not stay below one, report nonconvergence.

**N7 Stability and perturbation.** Fastest time constant about R_valve/Emax_lv ≈ 4 ms, comparable to the canonical step cap of 4 ms; report the stiffness ratio across the parameter box. Central finite-difference sensitivities of each quantity to each parameter at two tolerance levels; accept a sensitivity only when stable between levels beyond the N1 noise floor. Numerical instability (growth under refinement) vs dynamical response (stable under refinement) distinguished by that comparison.

## Deliverable D. Independent verification architecture

- Level 1, analytical checks: explicit incidence oracle, gradient sweeps, unit covariance with negative control, activation identities. Largely in place; shares the parameter interpretation.
- Level 2, reference numerical problems: N3 (a) to (e), N4 harness. (a) and (b) exist; (c), (d), (e) and N4 do not.
- Level 3, independent implementation: **BLOCKED**. No frozen specification exists (`physiology.md` mixes description, history and code references). The generator imports and calls the production RHS and `simulate`. To unblock: frozen specification (E1 to E7, E13, E14, parameter manifest, admissible domain) with hash; implementer who has not seen `src/physiosim`, given only that document; different solver family, preferably different language; provenance statement of access. Two AI agents given the same code are not independent; an agent given only the frozen specification can be, if the access restriction is recorded and enforced.
- Level 4, cross-implementation agreement: |A − B| <= U_A + U_B per quantity, with each side's N1 uncertainty.
- Level 5, independent technical review: a human numerical analyst reviewing specification, protocol and evidence package; prior agent reviews count as development review.

Supportable today: Level 1 "algebraic assembly matches an explicit specification at sampled states"; Level 2 "the integrator reproduces two trivial reductions". Nothing at Levels 3 to 5.

## Deliverable E. Existing evidence audit (117 tests; prior independent-review records preserved)

| Test family (count) | Mathematical claim | Oracle | Independent expected output? | Could pass with a wrong governing equation? | Classification |
|---|---|---|---|---|---|
| Constitutive point checks, `test_cardiovascular` (2) | E1 to E6 at a few points | Hand arithmetic | Yes | Yes, away from sampled points | PARTIALLY_VERIFIED |
| Mass balance via `roll` (1) | E7 | Production flows re-rolled in the test | No (circular) | Yes | INCONCLUSIVE |
| Incidence oracle with mutations, `test_independent_verification` (1) | E7 assembly | Explicit matrix, 80 seeded states | Yes | No for topology; yes for shared unit misreading | VERIFIED (Level 1) |
| Valve gradient and dissipation (5) | E5, E6 | Explicit edge list | Yes | No at those gradients | VERIFIED (Level 1) |
| Unit covariance (1) | E4 to E7 covariance | Pint scaling, negative control | Yes | No | VERIFIED (Level 1) |
| Conserved stable 40-beat trajectory (1) | Identity plus 0.1 mL settle | Production run | No | Yes (identity) | INCONCLUSIVE as code verification; regression |
| Metrics on synthetic arrays (1) | E14 definitions | Hand arithmetic | Yes | n/a | VERIFIED (post-processing) |
| Input validation, parameters and solver controls (16) | Admissible domain | Specification | Yes | n/a | VERIFIED (not mathematical) |
| Reduced-contractility response, 0.2 percent anchors (2) | Direction, regression | Production run | No | Yes | INCONCLUSIVE as verification; regression only |
| DOP853 vs Radau, 4 beats, 0.002 mL (1) | Solution agreement | Same RHS, second solver | No | Yes (same RHS) | PARTIALLY_VERIFIED (solver agreement); threshold origin undocumented |
| Single-beat NaN, package exports (2) | API behaviour | Specification | Yes | n/a | VERIFIED (not mathematical) |
| Dot-reduction and cos² equivalence, `test_hybrid` (5) | Common-mode robustness of E2, E7 | Algebraically equivalent formulations | Yes | Partly | VERIFIED for the properties tested |
| Zero-flow chatter, symmetric circuits, sampling independence (3) | E9 to E11, E13 | Symmetry, exact equality | Yes | No for those properties | VERIFIED (property based) |
| Large-step opening (6) | E11 checkpoint | Same code at finer step | No | Yes (common-mode) | PARTIALLY_VERIFIED |
| Cumulative flows (13) | E12, E15, refinement 1e-5 mL, monotone, better than quadrature | Linear invariant; same code refined | Partly | Residual yes; refinement partly | PARTIALLY_VERIFIED; thresholds from measured behaviour (regression, not verification) |
| Periodicity report on synthetic signals (23) | E14 beat-difference arithmetic | Analytic residuals | Yes | n/a | VERIFIED (post-processing) |
| Periodicity on real model (1) | Two functions agree | Each other | No | Yes | INCONCLUSIVE |
| Runtime audit faults (7) | E16 | Hand-built faults | Yes | n/a | VERIFIED (utility) |
| Passive equilibrium and reservoir refinement (2) | N3 (a), (b) | Analytic | Yes | No for those reductions | VERIFIED (Level 2); reservoir lacks order estimate |
| Determinism and saved-evidence gates (2) | Same-host repeatability; artefact thresholds | Replay; stored JSON | Replay yes; file is stored | File test cannot fail on live drift unless regenerated | Repeatability VERIFIED (same host); saved-evidence INCONCLUSIVE as live evidence |
| Interventions (8), experiments and CLI (2), ontology (8), semantic binding (4) | Not model-mathematics claims | Various | Various | n/a | Out of scope |

Common-mode weaknesses: most oracles call `pressures`, `flows` or `simulate`; parameter-unit interpretation shared by every oracle; event times NOT_TESTED; observed order of the production integrator NOT_TESTED; clipped-vs-regime flow difference NOT_TESTED; tie-breaking probe tested only via symmetric and equilibrium cases; 60-beat error growth characterised only by the 0.3153 mL default-vs-tight two-point comparison. Prior independent-review findings (strict periodicity MIXED, quadrature residuals, 0.3153 mL discrepancy, completeness bugs later fixed) remain valid and map to N1, N6 and E14.

## Deliverable F. Acceptance criteria

Each test record carries: claim, equation, oracle, procedure, measured quantity, error metric, uncertainty estimate, acceptance criterion, failure criterion, reproducibility evidence. Threshold derivation rules fixed before results:

- Identities (conservation, invariants, sampling independence): bound c·N·eps·scale with declared c, N operations or steps, scale of the summed quantity; exceeding is FAIL.
- Point checks vs hand arithmetic: relative error <= 16·eps; else FAIL.
- Analytic references: |numerical − exact| <= reference uncertainty + Richardson solver uncertainty, both reported. Observed order within one of theoretical order in the asymptotic range: PASS; monotone decrease without asymptotic range: INCONCLUSIVE; non-decreasing error: FAIL.
- Solution verification per quantity: PASS when the asymptotic-range check holds and estimated uncertainty is below the declared context-of-use requirement (set in the frozen specification, for an exploratory model relative to the quantity's beat-to-beat variation); INCONCLUSIVE when asymptotic range not reached; FAIL when refinement increases error.
- Event times: observed order at least one; PASS if Richardson uncertainty below the output sampling interval; else INCONCLUSIVE.
- Cross-implementation: |A − B| <= U_A + U_B PASS; beyond: FAIL with defect investigation on both sides; BLOCKED while Level 3 absent.
- Periodicity: PASS only as "periodic to within numerical uncertainty U at tolerance level L" with r_k < 1 recorded; else "not demonstrated".

Gates: specification completeness (ambiguities 1 to 7 resolved, hashed, reviewer sign-off); code verification (Level 1 complete; N3 (c), (e) and N4 PASS; event-time tests exist); solution verification (N1 and N5 for every quantity, no FAIL, INCONCLUSIVE listed); numerical uncertainty characterisation (every reported digit carries an uncertainty; N7 noise floor recorded); independent reproducibility (Level 3 built, Level 4 PASS, two-machine replay). No gate implies physiological validation.

## Deliverable G. Minimal high-information experiment suite (ranked)

1. Frozen specification resolving ambiguities 1 to 7, reviewed. Zero compute.
2. All-valves-open matrix-exponential reference, N3 (c).
3. Observed-order study across a single valve event with and without event location, N5 (fixed-step ladder); first event-time convergence data.
4. Single-ventricle piecewise-exponential case with analytic closing time, N3 (e).
5. Clean-room Level-3 implementation from the frozen specification, four beats, Level-4 comparison.
6. Poincaré contraction study at the tolerance ladder, N6.
7. Manufactured-solution harness on a smooth time-varying-elastance regime, N4.
8. Parameter-perturbation noise-floor study, N7.

Items 2 to 4 need minutes of compute and no production change (a harness importing the public API). Item 3 needs event times, recoverable post hoc from sign changes of the pressure gaps on the dense output, with the recovery method verified against the fixed-step reference.

## Deliverable H. Verification roadmap

| Stage | Content | Prerequisite | Resources | Reviewer | Stopping condition |
|---|---|---|---|---|---|
| 0 | Frozen specification and traceability matrix; this document reviewed | Approval of this methodology | 1 to 2 days, no compute | Human with ODE background, not the model author | Any unresolved ambiguity blocks Stage 1 |
| 1 | Level 1 completion and Level 2 references (G2, G4, N4 harness) | Stage 0 | 2 to 3 days, laptop compute | Same reviewer checks derivations | FAIL at Level 2 halts; defect to owner |
| 2 | Solution verification N1, N5, N6, N7 | Stage 1 PASS | 3 to 5 days; hours of compute; second machine for replay | Numerical reviewer | INCONCLUSIVE listed; FAIL halts |
| 3 | Level 3 clean-room implementation and Level 4 comparison | Stage 0 specification; implementer without code access | 3 to 5 days of an independent implementer | Independence provenance checked | Disagreement beyond combined uncertainty halts both sides |
| 4 | Evidence package and Level 5 external review | Stages 1 to 3 | 1 to 2 days plus reviewer time | External numerical analyst | Incomplete package blocks any claim |

Proposed structure (not yet created): `docs/verification/00_specification_frozen.md` plus `specification.json`; `01_traceability_matrix.md`; `02_numerical_protocol.md`; `03_independent_architecture.md`; `04_existing_evidence_audit.md`; `05_acceptance_criteria.md`; `06_evidence_package/` with `manifest.json` (commit, file hashes, configuration hashes, dependency versions, machine information), `logs/`, `results/` (all positive and negative outcomes with uncertainty calculations), `REPRODUCE.md`; `07_claim_boundary.md`. The Level-3 implementation lives outside `src/`, preferably in a separate repository with its own manifest. Pinned commit and hashes keep results auditable after the implementation changes.

Missing information and how to obtain it: a frozen specification (Stage 0); valve event times (post hoc recovery or an approved instrumentation change); the origin of the 0.002 mL Radau bound and the 1e-7 mL conservation bound (ask the authors or re-derive under Deliverable F); an independent implementer (person or agent sandbox with no repository access); a second machine for replay (the [redacted: cloud host] server used for the SHACL reproduction is a candidate).

## Deliverable I. Scientific claim boundary

Completing all five gates would establish: the code solves the clipped six-compartment ODE in the frozen specification; the numerical error of each reported quantity is characterised with an uncertainty; the hybrid event scheme converges to that ODE's solution; an independent implementation reproduces the results within combined uncertainty.

It would not establish that the equations describe cardiovascular physiology, that any parameter value is physiological, that the elevated-pressure baseline or the contractility scenarios correspond to any clinical state, that the model reproduces Smith 2004 or any published model, or that anything is scientifically novel. Correct implementation, numerical accuracy, reproduction of a published model, physiological validity and novelty are five separate claims; this methodology addresses the first two only.
