# Smith 2004 completed-run provenance
W3C PROV-O Recommendation 2013; local metadata uses urn:smith2004:prov:.
Revised in local review before commit: route events downgraded to routed records; binary prov:wasAssociatedWith added (see e:revisionNote).
Evidence, extracted facts, interpretations and conflicts have separate predicates and source pointers.
Readback usage covers logged invocation plus settings inspection; it is not a causal configuration input.
C times are wrapper boundaries only; A/B and CVODE start/end, C script start, comparison boundaries and ZIP creation time are UNKNOWN.
CVODE solver attribution, Hermes version/execution evidence and model call outcomes are UNKNOWN; model steps are recorded as routed (e:routedModel), not as prov associations; logged launcher hashes identify pythonshell, not wrappers.
Plans quote pinned docs/decisions.md; the later tolerance supersedes the old entry.
This record establishes traceability, not numerical or physiological validation.
Check: <server path>/repo/.venv/bin/python docs/evidence_review/prov/check_prov.py; optional --ttl PATH runs synthetic checker-only regressions, and missing evidence files are reported as skipped.
