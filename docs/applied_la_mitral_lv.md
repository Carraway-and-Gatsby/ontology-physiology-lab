# LA–mitral–LV descriptive sidecar v1

This is a thin metadata sidecar for `four_chamber_m1@1.0.0`, restricted to LA,
mitral transport and LV. It reads the closed M1 manifest and leaves equations,
parameters, units, outputs and the legacy registry untouched. It does not create a
new physiological model or an anatomical ontology equivalence. All source
roles are generic knowledge templates. No patient, CT, mask, overlay, measurement
or observation material is received, including public or deidentified material.

The baseline snapshot `456abc8c77134cd8909d603a1d96ed1384bad41f` is **UNREVIEWED**.
Inherited M1 batch-TDD history remains unresolved. This sidecar does not approve it.
There is no clinical, anatomical or physiological validation, body-wide
application, right-heart change or M2/M3 change.

## Pinned evidence and internal-use notice

Source: `[private repository]` revision
`70784bcdb9c14fba5271ee73f3c62b5f94ccbcfb`. (The source repository name was replaced by `[private repository]` for public
release on 2026-11-02; the snapshot `source_repo` field and the pinned document digest were updated accordingly.
The full-file SHA256 values of the original source files are unchanged.) The retained knowledge-only snapshot
was read locally; no source scripts, instructions, inference environment, network
or full TriG were used. Source material and prior model results remain untrusted
reference evidence. `applied_la_mitral_lv_source_v1.json` retains original JSON
records in `record`, with original file, JSON pointer and full-file SHA256 in
`provenance`. Only selected literature-source metadata is retained.

The Python module independently pins the complete canonical JSON document,
section digests and original full-file digests. Rewriting both the receipt and its
records cannot change these code pins. Canonical JSON is UTF-8, sorted keys,
ASCII escaping, compact separators and no nonfinite numbers. Hashes describe
integrity and provenance, not scientific validity or numerical permission. The
complete-document digest includes the subset-digest receipt but never itself.
The loader requires the pinned revision, unique template/profile keys and claim
IDs, closed context references, and knowledge-only flags. The two null contexts
are explicitly `heart/organ` and `heart/mitral_orifice`. No missing context is
filled by inference. All four chamber/wall/myocardium claims questioned in the
plan exist in this slice; `absent_claims` is empty.

Source `THIRD_PARTY_NOTICES.md:3–14` reports no separate own-code open-source
license. This copy is owner-authorized internal research use only; no source
relicensing or redistribution right is asserted. Uberon is CC BY 3.0, FMA CC BY
4.0 and RO CC0 as recorded by the source notice. Other referenced works retain
separate access/license conditions in `sources`. Source scripts are not copied.
Term release versions are not invented; the source revision is the version pin.

## Exact source locations and roles

Paths below are relative to `experiments/medmlx_anatomy_mapping/` in that revision.
Catalog pointers are array positions in `results/contents_catalog.json`.

| Source key | Concept ID | Catalog pointer | Descriptive role |
| --- | --- | --- | --- |
| heart/organ | UBERON:0000948 | #/0 | heart structure context only |
| heart/lv | UBERON:0002084 | #/1 | chamber structure, distinct from blood |
| heart/lv_cavity | UBERON:0016514 | #/2 | spatial context |
| heart/lv_wall | UBERON:0036285 | #/3 | unselected mechanical context candidate |
| heart/lv_blood | UBERON:0000178 | #/4 | proposed V_lv/P_lv bearer/context correspondence |
| heart/la | UBERON:0002079 | #/9 | chamber structure, distinct from blood |
| heart/la_cavity | UBERON:0016513 | #/10 | spatial context |
| heart/la_blood | UBERON:0000178 | #/11 | proposed V_la/P_la bearer/context correspondence |
| heart/lv_myocardium | UBERON:0006566 | #/18 | unselected mechanical context candidate |
| heart/mitral_valve | UBERON:0002135 | #/26 | flow-location context |
| heart/la_wall | FMA:9531 | #/41 | unselected mechanical context candidate |
| heart/mitral_orifice | FMA:9335 | #/47 | anatomical opening; boundary REVIEW |
| heart/la_myocardium | UBERON:0003380 | #/51 | unselected mechanical context candidate |
| heart/mitral_annulus | UBERON:0005995 | #/65 | anatomical attachment; relation REVIEW, definition REVISE |

Every catalog record retains `KNOWLEDGE_TEMPLATE_REVIEW` and `observed_in_CT=false`.
The identical blood concept ID does not merge the LA/LV contextual templates.

Directed claims are verbatim in `results/relation_literature_review.json` at
`#/claims/20,22,23,26,27,32,33,34,39,41,42,45` (the machine receipt is authoritative
for each pointer). Each retains its claim ID, exact IRI, direction, evidence
locator, reviewer, scope, original relation status, formalization decision and
expert-review status. No absent field is invented: the derived status view marks
an absent anatomical-evidence status `NOT_RECORDED` while retaining the verbatim
record. All selected claims are `NOT_INDEPENDENTLY_EXPERT_REVIEWED`.

Special reviews preserve `mitral_orifice_boundary_equivalence=REVIEW` and
`mitral_annulus_complete_fibrous_ring_interpretation=REVISE`. Boundary definitions
are `ontology/boundary_definitions.json#/proposals/5` (attachment) and `#/proposals/6`
(transfer interface), version `0.1.0`, `DRAFT_MODEL_CONVENTION`, `NOT_MEASURED`.
The symbolic oriented spanning interface is separate from the anatomical valve,
orifice, annulus, open gap and effective orifice area. EOA is `NOT_REPRESENTED`.

## Relations and independent gates

Source blood→cavity `RO_0001025` (located_in), source cavity→chamber
`RO_0002572` (IRI preserved without a new interpretation), target C5 `part_of`
(`docs/decisions.md:27`, runtime adaptation deferred), and M1
`blood_contained_in` (`four_chamber_m1_manifest.py:54–61`) remain separate.
The C5 entry is explicitly unapplied. No sameAs, equivalentClass, verified bearer
or value equivalence is produced. V2 anatomy pointers are recorded beside source
IDs only; matching spelling does not establish equivalence. V2 LA's Smith role
and separate M1 LA state remain an unresolved interpretation difference.

Three independent axes are retained: source decisions/original relation status/
expert reviews; target crosswalk `PROPOSED`; external numeric permission `NONE`.
ACCEPT only supports descriptive context. REVIEW, REVISE and DRAFT remain visible.
They never imply owner review or numerical authorization.

- G1: pinned representation and exact model contract checks.
- G2: synthetic execution allowed; public `gate_report` reports `executed=false`
  until the demo actually executes and verifies its two runs.
- G3: external numeric binding **CLOSED**. `request_numeric_binding` always raises
  `PermissionError`, including requests carrying ACCEPT or a purported approval.

The validator is deliberately a closed model-specific contract. It rejects extra
or changed fields, model versions, contexts, units, references, temporal meaning,
direction, identity/bearer substitutions, aorta→systemic-bed mappings, boundary/EOA
equivalences, status promotion and changed receipts. No actual binder or
`connect_value` use is added; no resistance, area or elastance is inferred.

## Symbols, parameters and law references

`variables` and `parameters` are exact copies of their selected M1 contracts;
sidecar role annotations live separately and never extend the canonical manifest.

| Symbols | Sidecar kind | Unit | Time / aggregation |
| --- | --- | --- | --- |
| V_la, V_lv | blood volume state | mL | instantaneous total volume |
| P_la, P_lv | algebraic observable | mmHg | instantaneous, common model gauge |
| Q_mitral | edge flow | mL/s | instantaneous, nonnegative LA→LV |
| Q_cum_mitral | auxiliary integral | mL | run-integrated LA→LV transport |
| lv_edv_sample_ml, lv_esv_sample_ml | metric | mL | beat_sample_extremum |
| lv_ejection_fraction_sample | metric | dimensionless | beat_sample_extremum |
| la_pressure_mean_mmhg | metric | mmHg | beat_mean |
| mitral_flow_port | port metadata referencing Q_mitral | via referenced flow | no duplicate physical state |

Pressure reference is exactly: "model gauge pressure relative to one common fixed
external pressure of 0 mmHg; no intrathoracic/pericardial pressure". Signed negative
gauge pressure is permitted. Nonpressure references remain `not applicable`.

Required parameter references: `elastance_la`, `emin_lv`, `emax_lv` (mmHg/mL),
`resistance_mitral` (mmHg*s/mL), `heart_rate` (1/min), `systolic_fraction`
(dimensionless), `unstressed_volumes` and `initial_volumes` (mL). The volume arrays
retain the complete M1 order in their exact parameter contracts; slice references
select LA index 7 and LV index 0. Initial volumes are initial-state inputs; V0
references select unstressed-volume parameters. No values are obtained from anatomy.
SV_lv/CO_lv belong to the aortic edge and are intentionally rejected here.

`E_lv(t)` is a separate constitutive-law node, never a manifest variable. Its
activation inputs are heart_rate and systolic_fraction; the implementation refers
to `physiosim.models.cardiovascular.elastance`. Verbatim target equation anchors
and declared line/section references remain traceable to
`docs/physiology_four_chamber_m1.md:62–70`:
activation, E_v(t), P_v, P_a, ideal-diode q_e and cumulative integral. These are
references to existing model equations, not adopted anatomical axioms.
Constitutive, definition and signed conservation-contribution dependencies are
separate from value equivalence; the slice does not replace the other M1 edges.

M1's ideal diode is a restricted no-reverse-flow approximation relative to the
source interface allowing signed/regurgitant transport. It does not model
regurgitation, effective area, patient geometry or valve mechanics.

## Public API and private demo

From `physiosim.ontology.applied_la_mitral_lv`:
`load_source_slice(path=None)`, `validate_source_slice(document)`,
`build_applied_sidecar()`, `validate_applied_sidecar(sidecar)`,
`gate_report(sidecar)`, `request_numeric_binding(*args, **kwargs)`.
Validation returns None on success and raises ValueError for contract defects.
Missing local resources fail locally; no network fallback exists. Expected source
hashes are code pins. The M1-specific law/version contract checks the model ID,
version, common pressure reference, LA/LV state order, mitral LA → LV diode and
required parameter fields. This declaration does not prove arbitrary numerical
implementation integrity. Runtime file hashes are separate observed provenance;
checkout tests check the law anchors against documentation. The existing M1
manifest remains closed.

From `physiosim.experiments.applied_la_mitral_lv_demo`:
`result_fingerprint(result)`, `run_applied_demo(output)`, `main(argv=None)`.
The demo runs the existing `synthetic_fixture()` with `cycles=2`,
`samples_per_cycle=50`, and `SolverSettings(max_step=period/200)` twice, before
and after building/validating the sidecar. Full time/volume/pressure/flow/cumulative
arrays, dtype/shape and configuration hashes must match exactly. The manifest
must also remain identical. These short runs are numerical invariance checks,
not steady-state or physiological validation.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src" \
.venv/bin/python \
scripts/run_applied_la_mitral_lv.py --output results/applied-demo
```

`--output` is required. Existing nonempty directories and final-component symlinks are
rejected; symlinked ancestors (such as macOS `/tmp`) are accepted. umask 077 is restored afterward; the output directory is mode 0700 and
all six files are mode 0600 with exclusive, no-follow writes. Files:
`applied_sidecar.json`, `gate_report.json`, `source_receipt.json`,
`trace_la_mitral_lv.csv`, `index.html`, `run_receipt.json`.
CSV values come from actual computed M1 arrays, with units in column names.
The local HTML uses inline SVG, synthetic labels and source statuses; no external
assets or scripts. Output checksums explicitly exclude `run_receipt.json` itself.
No output paths or timestamps enter deterministic file contents.

## Execution evidence and review boundary

For the PR #5 portability repair, chronological focused commands, actual exit
codes and RED/GREEN logs are retained in the private task artifacts under
`pr5-wheel-portability-v1/tdd/index.jsonl`. The initial wheel evidence reproduced
two failures; it is not evidence for all 30 reported CI failures. The router runs
both complete source and freshly installed wheel suites separately. These
software checks do not approve mappings or physiological validity. Inherited M1
batch-TDD history remains UNREVIEWED.

Run focused source tests from this checkout with:

```sh
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH="$PWD/src" \
.venv/bin/python -m pytest \
tests/test_applied_la_mitral_lv.py -q -p no:cacheprovider -o addopts= \
-o pythonpath="$PWD/src" --basetemp=.pytest_tmp/focused
```

`test_physiosim_package_matches_checkout_source` compares complete imported
package file hashes against this checkout, accepting an identical installed wheel
and rejecting changed submodules, missing files and extra files. Wheel tests use
`python -I -m pytest` without source-path redirection. A byte-exact check compares
the bundled runtime anatomy JSON with `docs/evidence_review/anatomy_nodes_v2.json`
in both modes, so a later documentation-source change requires an explicit
resource update. This preserves source provenance without requiring repository
docs at runtime.

Law and port metadata explicitly retain unit, temporal meaning, sign, reference and
aggregation. `time_contract` fixes seconds elapsed from run start and the periodic
activation phase. `parameter_roles` distinguishes caller parameters from state;
`target_anatomy_source` preserves the existing v2 version/provenance contract.
