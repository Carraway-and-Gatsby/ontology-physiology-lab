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
  GitHub asset SHA-256 `513ad729…60ee`) was staged and hash-checked on the
  host at `~/opencor/OpenCOR-0-8-3-Linux`. Static `ldd` with the bundled
  `lib/` and `plugins/`: core simulation/Python plugins resolve; only GUI,
  web-view and PMR plugins miss system libraries. Startup not yet tried.
- Reference input switched to the canonical CellML (SHA-256 `8cca17e8…3e60`),
  to be downloaded by the integrator outside the sandbox. Status: PROPOSED.

## Open questions

- Whether to exclude cumulative states from error control (not supported by
  scipy's solve_ivp directly) or accept documented looser volume control.
- gpt-5.6-luna availability (429 only; retry later before routing to it).
