# Research strategy records (index)

Status: working documents added to the working tree on 2026-11-03. **Not committed, not reviewed, not part of any evidence gate.** They record read-only audits and designs; no code, test, model, dataset or published material was changed to produce them. Baseline audited: `main@7b9e2e82715ce4a2322e15520e7e670ef233ed8a` (clean tree).

Status vocabulary used throughout: `NOT_STARTED`, `IN_PROGRESS`, `VERIFIED`, `BLOCKED`, `REFUTED` for research hypotheses; `VERIFIED`, `PARTIALLY_VERIFIED`, `INCONCLUSIVE`, `FAILED`, `NOT_TESTED`, `BLOCKED` for verification evidence. A passing software test never by itself makes a claim `VERIFIED`.

| File | Content | Date |
|---|---|---|
| [dual_track_audit_2026-11-03.md](dual_track_audit_2026-11-03.md) | First report: research baseline, Track A and Track B evidence registers, novelty, shared dependencies, gaps, roadmap, readiness, next actions | 2026-11-03 |
| [track_a_methodological_register.md](track_a_methodological_register.md) | Track A (methodological, Nature Computational Science aspiration) evidence register | 2026-11-03 |
| [track_b_discovery_register.md](track_b_discovery_register.md) | Track B (physiological discovery, Nature Communications aspiration) register | 2026-11-03 |
| [novelty_and_prior_work.md](novelty_and_prior_work.md) | Literature and novelty review with citations and reading depth | 2026-11-03 |
| [research_gate_1.md](research_gate_1.md) | Research Gate 1: Track A benchmark and baseline protocol, Track B model feasibility matrix, blockers, highest-information experiments, PASS/BLOCKED/INSUFFICIENT_EVIDENCE criteria; appendix with model and tooling facts | 2026-11-03 |
| [../verification/model_verification_methodology_v1.md](../verification/model_verification_methodology_v1.md) | Model Verification Methodology v1 for the implemented six-compartment model (deliverables A to I) | 2026-11-03 |

## Order of work decided so far

1. **Model verification first** (`docs/verification/`): does the implemented code solve the equations it claims, within demonstrable numerical uncertainty? Nothing physiological is inferred from this.
2. **Research Gate 1** before any Track A implementation or Track B integration: independent benchmark design, reference-model feasibility, explicit gate criteria.
3. Track A is the primary research direction; Track B is exploratory and independently gated.
4. Journal targets are aspirations, not statements of suitability. Neither track is publication-ready.

## Standing rules recorded in these documents

- Acceptance criteria must be derived (machine precision, observed convergence, reference-solution uncertainty, sourced context of use) and fixed before results are seen; no threshold chosen to make the implementation pass.
- The current six-compartment model is **not** a reproduction of Smith 2004 and must not be described as one.
- Unreviewed branches (PR #5 four-chamber M1 and sidecar, hackathon experiment agent, ontology-completion rounds, public site) are outside both evidence bases until reviewed and merged.
- Different AI agents are not automatically independent reviewers or independent implementers; independence is a matter of recorded access, not vendor.
