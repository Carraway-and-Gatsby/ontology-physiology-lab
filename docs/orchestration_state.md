# Orchestration state (multi-model engineering log)

Lightweight coordination record. Status vocabulary is strict: PROPOSED <
IMPLEMENTED < TESTED < SCIENTIFICALLY VALIDATED. Nothing in this project is
scientifically validated against external physiological data.

## Current milestone

Phase 1 cardiovascular core: numerical-verification hardening before any
reference-model reproduction or renal coupling (see decisions.md).

## Verified tool / model configuration (2026-10-31)

| CLI | Version | Auth / account | Model probes |
|---|---|---|---|
| Claude Code | 2.1.314 | [redacted: account/billing detail] | claude-haiku-5-5 OK, claude-sonnet-5-5 OK, claude-opus-5-5 OK |
| Codex | 0.153.4 | [redacted: account/billing detail] | gpt-6-astra OK, gpt-5.6-sol OK, gpt-5.6-terra OK; gpt-6.1-sol, gpt-6-sol, gpt-6-luna, gpt-6.1-terra rejected (`model_not_found` for [redacted: account/billing detail]); gpt-5.6-luna HTTP 429 (unverified) |

Effective tiers: Claude LIGHT/STANDARD/DEEP = haiku/sonnet/opus-5-5. Codex
LIGHT = gpt-5.6-terra, STANDARD = gpt-5.6-sol (substitute for unavailable
gpt-6.1-sol), DEEP = gpt-6-astra. Note: `~/.codex/config.toml` defaults to
gpt-6.1-sol, which fails for this account, so always pass `-m`.
Each Codex exec loads ~26-30k tokens of user skills/config context even for a
trivial prompt.

Isolation: this directory is not a git repository. Workers ran in
git-baselined scratch copies with their own venvs; the integrator applied
reviewed diffs here. Pre-integration snapshot:
`~/.hermes/cache/scratch/physiosim-orch/main-snapshot-pre-orch.tgz`.

## Task and routing history

| ID | Task | Risk / complexity | Routed to | Outcome |
|---|---|---|---|---|
| T1 | Opt-in solver-integrated cumulative edge-flow states (`simulate(cumulative_flows=True)`, `local_balance_residual_ml`, `cumulative_metrics`) | MEDIUM / MEDIUM | Codex gpt-5.6-sol, workspace-write sandbox, 1 attempt, 293 s, [redacted: usage] | IMPLEMENTED, TESTED (13 tests) |
| T2 | Strict multi-beat `periodicity_report` | LOW / LOW | Claude haiku-5-5, acceptEdits + pytest-only Bash, 16 turns, 197 s | IMPLEMENTED, TESTED (24 tests) |
| R1 | Independent cross-family review of T1 | Tier 4 | Claude opus-5-5, read-only (no edit tools), 18 turns, 374 s | ACCEPT WITH CHANGES: 3 MAJOR (two tolerances 87x/8000x too loose; undocumented dense-output undershoot; looser volume error control) |
| T1-fix | Apply R1 changes | LOW | Integrator (Hermes) after re-executing all R1 numbers | Tolerances tightened to ~4x/~8x measured; limitations documented |
| T2-rev | Review of T2 | LOW | Integrator diff review + cross-check against the previously documented independent residuals (exact reproduction) | Accepted unchanged |

No escalation was needed. No task was retried.

## Test evidence (integrated tree)

- Full suite: 101 passed (64 pre-existing + 13 + 24), 5 RDFLib-internal
  deprecation warnings.
- Default `simulate()` path unchanged: canonical experiment CSVs regenerated
  from the integrated code are byte-identical to `results/phase1/*.csv`.

## Findings

- Strict 3-beat 1e-4 mL periodicity verdicts at canonical tolerances depend
  on solver error control (see physiology.md table); at rtol 1e-11/atol
  1e-12/T/400 all three scenarios pass (<= 6.1e-7 mL).
- Solver-integrated SV converges to 1.3e-6 mL under refinement; 400-sample
  trapezoid SV is biased by ~0.056% (sign scenario-dependent).

## Pending / next (PROPOSED)

1. Decide whether the runner should report `periodicity_report` and
   cumulative-flow SV in `summary.json` (changes canonical outputs; needs
   approval and regenerated results/manifests).
2. Rebuild wheel, reinstall `.clean-venv`, rerun reproducibility scripts
   (not done; `dist/` wheel and `results/` predate these changes).
3. Local parameter sensitivity analysis of final-beat metrics (STANDARD, Codex).
4. Licensed reference-model reproduction (DEEP research). Smith 2004 license
   resolved 2026-10-31: CC BY 3.0 with attribution (physiology.md). Use only
   the canonical CellML (`evidence/a_smith_2004_canonical.cellml`); the
   workspace-267 capture has no parameter/initial values.
5. Renal coupling remains deferred per decisions.md.

## OpenCOR reference run (Hermes, [redacted: cloud host] `[redacted: host]`)

- 2026-10-31 attempt stopped before download: `curl: (6) Could not resolve
  host: github.com` inside the worker CLI sandbox. The host itself resolves
  github.com, so the block was the sandbox's network policy, not the server.
- Official OpenCOR v0.8.3 `OpenCOR-0-8-3-Linux.tar.gz` (322,810,313 bytes,
  GitHub asset SHA-256 `513ad729…60ee`) is staged at
  `/opt/opencor/OpenCOR-0-8-3-Linux` (root-owned, read-only to others).
  Hermes runs as `medical-ontology` ([redacted: uid]), so the first staging under
  `<server path>` was invisible to it (ENOENT); after the move, the archive
  hash, `pythonshell` and `bin/OpenCOR` were checked as [redacted: uid]. Static
  `ldd` with the bundled `lib/` and `plugins/`: core simulation/Python
  plugins resolve; only GUI, web-view and PMR plugins miss system
  libraries. Startup not yet tried.
- Reference input switched to the canonical CellML (SHA-256 `8cca17e8…3e60`);
  the integrator downloaded and hash-verified it outside the sandbox
  (2026-10-31 14:25:29 UTC). Simulation status: PROPOSED.
- 2026-11-01 default run (CVODE + KINSOL) loaded the model but
  `simulation.run()` failed: `std::runtime_error: the maximum number of
  iterations was reached before convergence`. That wording matches KINSOL
  (septum algebraic equation), not CVODE. Cause not established; a scipy
  re-implementation (not the reference) points at the discontinuous valve
  law at Q=0 but that is a hypothesis only.
- 2026-11-01 user-approved solver deviation: OpenCOR's built-in fixed-step
  fourth-order Runge-Kutta replaces CVODE only. KINSOL, the model, parameters
  and units are unchanged. Two step sizes (1e-5 s and 5e-6 s) are run for a
  step-halving comparison. Outputs are labelled "OpenCOR RK4", never as the
  OpenCOR default-solver result. This does not show why CVODE failed.
- Result of the approved runs: A and B both completed 1.5 s and wrote CSVs;
  no KINSOL convergence error. The existing comparator rejects the pair
  because output times differ at floating-point level, so the aggregate
  status is still failed (comparator condition, not a failed calculation).
- Decision approved by the user (2026-11-01): time stamps count as
  equal when |dt| <= 1e-9 s, applied to the time axis only. Raw CSVs stay
  unmodified (no rounding or interpolation). Fixed before looking at value
  differences. Superseded the same day (user-approved, see decisions.md):
  1e-9 s was the assistant's own choice and is replaced by the derived bound
  |dt| <= N_steps * eps * t_max.
- 2026-11-01 value-comparison basis (PubMed, text read unless noted):
  Pathmanathan & Gray 2013 (doi 10.3389/fphys.2013.00358), Pathmanathan &
  Gray 2014 (10.1002/cnm.2615; abstract plus Wiley passages), Erdemir 2020
  (10.1186/s12967-020-02540-4), Mulugeta 2018 (10.3389/fninf.2018.00018),
  Santiago 2022 (10.1371/journal.pcbi.1010141). Abstract only: Smith 2004
  (10.1016/j.medengphy.2003.10.001), Hicks 2015 (10.1115/1.4029304). Not read
  (outside PubMed): Celik 2008, Roache, ASME V&V 20/40, FDA 2023 guidance.
  User decision: report-only, no pass/fail line.
- User-approved (2026-11-01), run C not yet requested or run: add a third step
  size, 2.5e-6 s (run C), so an observed order of convergence can be computed
  (two sizes cannot);
  expect it below the RK4 order of 4 near valve switches. Quantities of
  interest fixed beforehand: P_lv, P_ao, Q_av, stroke volume, valve
  open/close times. The independent scipy re-implementation stays blind
  until the procedure is fixed. Run C must be requested from Hermes.
- 2026-11-01 Hermes check before run C: A used RK4 step 1e-5 s and B 5e-6 s
  (settings read back before and after); both CSVs have 0.001 s output
  spacing and 1,501 rows. The earlier "every 4th C row = A grid" instruction
  was the assistant's error and was withdrawn. Run C: step 2.5e-6 s, same
  0.001 s output, compared by output index; scalar definitions and the
  decision not to add the negative-flow integral are in decisions.md. Hermes
  confirmed it will run C once with these rules and add no pass/fail wording.
  A and B files unchanged.
- 2026-11-01 run C result (Hermes report, report-only; recomputed from the
  reported numbers, raw CSVs not seen here): C ran 05:48:23-05:48:27 UTC,
  exit codes 0/0, empty stderr, no NaN/Inf, 1,501 rows, CSV SHA-256
  `8d0943e5…b427`; report ZIP SHA-256 `b4ec9e79…2166`. Max time difference
  at the same output index about 7e-18 s (bounds 5.0e-11 to 2.0e-10 s).
  Max abs difference A-B / B-C: P_lv 0.00712 / 0.00365, P_ao 0.00495 /
  0.00254 (labelled kPa), Q_av 1.928 / 0.964 mL/s. Observed order p (max
  norm) 0.964, 0.960, 1.000; RMS norm gives the same picture. RK4's formal
  order is 4; the cause of the lower order is not established. Stroke volume
  per beat (A/B/C, mL): 65.8474 / 65.8479 / 65.8481 (p 2.29, GCI_fine
  5.4e-7) and 65.7768 / 65.7769 / 65.7770 (p 1.00, GCI_fine 1.2e-6); this
  GCI excludes the 1 ms sampling quadrature error, which is common to A, B
  and C. Aortic valve sample times identical in A, B, C: open 0.247 / 0.997
  s, close 0.384 / 1.134 s; p undefined (0/0). The requested check
  GCI_AB / (2^p x GCI_BC) equals f_C / f_B by construction when p comes from
  the same three values, so it carries no evidence; asking for it was the
  assistant's error.
- Blind comparison with the assistant's scipy re-implementation (not a
  reference, not independent of the assistant), report-only: stroke volume
  65.8 mL vs 65.848 mL (beat 1); aortic valve opening 0.247 s vs first
  positive sample 0.247 s. From the raw C CSV: P_lv -3.2 to 119.0 vs
  -3.23 to 119.00; P_ao 79.0 to 116.4 vs 78.96 to 116.38; Q_av peak 1110 vs
  1110.05. All agree to the precision the scipy values were recorded at.
- 2026-11-01 review of the Hermes report ZIP (SHA-256 matches `b4ec9e79…
  2166`; read, not executed). A/B/C `signals.csv` hashes match the report;
  B's `rawsignals.csv` is byte-identical to its `signals.csv`. Solver
  readbacks: KINSOL settings identical in A, B, C; only the RK4 Step differs
  (1e-5, 5e-6, 2.5e-6); output interval 0.001 s. Comparator
  (`compare_abc.py`, `report_math.py`) implements the approved definitions;
  undefined orders are labelled, not adjusted. Runner changes limit
  execution to the single run C and re-hash A/B before and after; the old
  1e-9 s grid assertion and the embedded PATH injection were removed. No
  defect found. An independent recomputation from the raw CSVs (own code,
  not Hermes's) reproduces every reported number.
- Observation, not an established cause: negative Q_av holds one constant
  value per closed-valve span, and in the first span it halves exactly with
  each step halving (-3.856, -1.928, -0.964 mL/s over 0.001-0.246 s); later
  spans are smaller (A/B/C -0.0095/-0.0049/-0.0003 and -0.0097/-0.0051/
  -0.0005) and do not halve cleanly. Flow that scales with the integration
  step points to a numerical artifact of the fixed-step solution at the
  valve law's Q=0 switch rather than physiology; Smith 2004 (abstract only
  read) describes solving with a phase-dependent number of states. This
  offset dominates the Q_av order (largest B-C difference at t=0.001 s);
  the largest P_lv/P_ao B-C differences sit at 0.255-0.26 s, just after
  aortic valve opening. Hermes notes OpenCOR's Step unit (seconds) is
  owner intent, not confirmed from API documentation.
- Still open: unit labels (kPa labels on values that behave as mmHg) and
  agreement with the published waveform; both need the Smith 2004 paper.
- Not yet verified: negative Q_av, original-unit plausibility (pressures
  labelled kPa behave numerically as mmHg), agreement with the published
  waveform.
- 2026-11-01 update from the Smith 2004 author manuscript (card S6P in
  docs/evidence_review/evidence_cards.md; quotations only, file not
  retained): the paper uses mmHg, ml and s throughout and never kPa, but
  has no parameter table (C1). Its valve law removes Q from the state
  vector when Q turns negative, whereas the CellML holds dQ/dt = 0, so a
  negative Q reached in one step is frozen; this is consistent with the run
  C negative-Q_av observation being an artefact of the CellML encoding
  (C11). The six CellML initial volumes sum to the paper's 1500 mL stressed
  volume, and the 0.75 s period matches its 80 beats/min. Agreement with the
  published waveform (Figure 7) is still not checked.
- 2026-11-01 user decision (decisions.md, "C1 units and the R13 numeric
  block"): the CellML numerals are read as mmHg-based and existing OpenCOR
  outputs labelled kPa are read as mmHg, with no conversion factor; no file
  is edited. Numeric comparison with the CellML is no longer blocked and
  stays report-only.
- 2026-11-01 C11 check (Hermes [redacted: request id], read-only on the A/B/C
  CSVs; results in evidence_review.md C11): three Q_av < 0 spans per run,
  each exactly constant, with P_lv - P_ao < 0 throughout. B/C ratios of the
  frozen values are 2.0000, 16.27 and 10.50, so only the first span halves
  with the step; the earlier "halves with the step" wording applies to the
  first span only. Independent review of the result is not done.

## Open questions

- Whether to exclude cumulative states from error control (not supported by
  scipy's solve_ivp directly) or accept documented looser volume control.
- gpt-5.6-luna availability (429 only; retry later before routing to it).
