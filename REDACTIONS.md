# Public redactions

This repository is a history-preserving public copy of a private repository. Rewriting was done with `git-filter-repo` 2.47.0 (`--replace-text` for file contents and `--replace-message` for commit messages, same rule file: `replacements.txt`).

## What is preserved and what changed

- The original commit topology and dates are retained. The mailmap normalizes selected owner identities to the public GitHub noreply identity. Public rights documentation is included directly in the rewritten commits, without adding commits.
- Every commit hash changed because content and some messages changed. The old-to-new mapping is in `commit-map.txt`. Abbreviated hashes inside commit messages were rewritten by git-filter-repo automatically; hashes quoted inside file contents (e.g. `baf499e` in docs) were not and still refer to the original commits.
- Published branches: `main`, `codex/applied-validation-fix`, `codex/ontology-graph-view`, `hackathon/experiment-agent`. No tags, other branches, or remotes.

## SHA-256 records

SHA-256 values recorded in docs for the files listed below refer to the pre-redaction bytes. The following records no longer match the redacted bytes:

- `tools/ontology_graph_view/input-sha256.json` records `ed3f4a73...1581` for `inputs/applied_sidecar.json`; the redacted file hashes to `0e2c2a14...51ce`.
- `src/physiosim/ontology/applied_la_mitral_lv.py` pins `PINNED_DOCUMENT = fe512725...5f` (canonical-JSON digest of `applied_la_mitral_lv_source_v1.json`); the redacted document digests to `5223a5d9...1db8`. The five per-subset digests are unaffected. Earlier snapshots broke 16 tests on the two `codex/*` branches; the current codex/* tips contain the repaired pins. The experimental branch still has an old pin and a bundled receipt affected by the privacy rewrite.
- Evidence files that were redacted (`docs/evidence/c_*`, `a_tdd_*`, `results/*`, ...) may be cited by hash in prose in `docs/`; the scan found no full or prefix hash of them in the published tree, but the original bytes are the reference.

The current codex/* source tips already contain the public-compatible source document pin. The earlier hash observations above remain as provenance of the privacy-only audit.

## Rules (`replacements.txt`)

The historical counts below describe the earlier three-branch privacy-only audit, computed over every blob reachable before filtering (distinct blobs / total matches / commit messages touched). Note git-filter-repo applies `literal:` rules before `regex:` rules.

| # | Rule | Blobs | Matches | Messages | Paths |
|---|---|---|---|---|---|
| 1 | `regex:/Users/[A-Za-z0-9._-]+/Desktop/Development/medical-ontology==><repo>` | 9 | 26 | 0 | 9 |
| 2 | `regex:/Users/[A-Za-z0-9._-]+(?:/[^\s"'\\<>()\[\]:;,`]*)?==><local path>` | 2 | 2 | 0 | 2 |
| 3 | `literal:<server path>==><server path>` | 4 | 42 | 0 | 4 |
| 4 | `regex:/home/(?:ubuntu\|[a-z][a-z0-9_-]+)\b==><server path>` | 13 | 13 | 1 | 1 |
| 5 | `literal:[redacted: host]==>[redacted: host]` | 16 | 19 | 3 | 2 |
| 6 | `literal:[redacted: cloud host]==>[redacted: cloud host]` | 14 | 14 | 0 | 1 |
| 7 | `regex:(?i)[redacted: cloud host]==>[redacted: cloud host]` | 0 | 0 | 1 | 0 |
| 8 | `literal:[private repository]==>[private repository]` | 5 | 5 | 0 | 3 |
| 9 | `literal:[private repository]==>[private repository]` | 0 | 0 | 0 | 0 |
| 10 | `regex:\bMED-[A-Z0-9][A-Z0-9-]*==>[redacted: request id]` | 7 | 16 | 4 | 3 |
| 11 | `regex:[redacted: account/billing detail](?: \([^)]*\))?==>[redacted: account/billing detail]` | 15 | 15 | 0 | 1 |
| 12 | `regex:[redacted: account/billing detail](?: \([^)]*\))?==>[redacted: account/billing detail]` | 15 | 15 | 0 | 1 |
| 13 | `literal:[redacted: account/billing detail]==>[redacted: account/billing detail]` | 15 | 15 | 0 | 1 |
| 14 | `literal:Auth / account==>Auth / account` | 15 | 15 | 0 | 1 |
| 15 | `regex:\b\d[\d,]{3,} tokens\b==>[redacted: usage]` | 15 | 15 | 0 | 1 |
| 16 | `regex:"platform":\s*"(?:macOS\|Darwin)[^"]*"==>"platform": "[redacted: OS version]"` | 3 | 3 | 0 | 3 |
| 17 | `regex:\(main, [A-Z][a-z]{2} +\d+ \d{4}, [\d:]+\) \[Clang [\d.]+ \]==>[build details redacted]` | 4 | 4 | 0 | 4 |
| 18 | `regex:\[Clang [\d.]+ \]==>[build details redacted]` | 0 | 0 | 0 | 0 |

Total distinct blobs changed: 41; distinct paths: 23. Commit messages that differ from the original: 9 (redactions plus abbreviated-hash remapping).

## Affected paths per rule

### Rule 1: `regex:/Users/[A-Za-z0-9._-]+/Desktop/Development/medical-ontology==><repo>`
- `docs/evidence/a_tdd_02_red.txt`
- `docs/evidence/a_tdd_03_red.txt`
- `docs/evidence/a_tdd_07_red.txt`
- `docs/evidence/c_verify_execution.txt`
- `docs/evidence/c_verify_full_suite_initial.txt`
- `docs/evidence/c_verify_pytest.txt`
- `docs/evidence/c_verify_red.txt`
- `results/build.log`
- `results/reproducibility.json`

### Rule 2: `regex:/Users/[A-Za-z0-9._-]+(?:/[^\s"'\\<>()\[\]:;,`]*)?==><local path>`
- `docs/evidence/c_finish_evidence.py`
- `docs/evidence/c_retrieve.py`

### Rule 3: `literal:<server path>==><server path>`
- `docs/applied_la_mitral_lv.md`
- `docs/evidence_review/prov/README.md`
- `docs/evidence_review/prov/smith2004_opencor_runs.ttl`
- `docs/physiology_four_chamber_m1.md`

### Rule 4: `regex:/home/(?:ubuntu\|[a-z][a-z0-9_-]+)\b==><server path>`
- `docs/orchestration_state.md`

### Rule 5: `literal:[redacted: host]==>[redacted: host]`
- `docs/orchestration_state.md`
- `tools/ontology_graph_view/README.ko.md`

### Rule 6: `literal:[redacted: cloud host]==>[redacted: cloud host]`
- `docs/orchestration_state.md`

### Rule 8: `literal:[private repository]==>[private repository]`
- `docs/applied_la_mitral_lv.md`
- `src/physiosim/ontology/applied_la_mitral_lv_source_v1.json`
- `tools/ontology_graph_view/inputs/applied_sidecar.json`

### Rule 10: `regex:\bMED-[A-Z0-9][A-Z0-9-]*==>[redacted: request id]`
- `docs/evidence_review/evidence_review.md`
- `docs/evidence_review/prov/smith2004_opencor_runs.ttl`
- `docs/orchestration_state.md`

### Rule 11: `regex:[redacted: account/billing detail](?: \([^)]*\))?==>[redacted: account/billing detail]`
- `docs/orchestration_state.md`

### Rule 12: `regex:[redacted: account/billing detail](?: \([^)]*\))?==>[redacted: account/billing detail]`
- `docs/orchestration_state.md`

### Rule 13: `literal:[redacted: account/billing detail]==>[redacted: account/billing detail]`
- `docs/orchestration_state.md`

### Rule 14: `literal:Auth / account==>Auth / account`
- `docs/orchestration_state.md`

### Rule 15: `regex:\b\d[\d,]{3,} tokens\b==>[redacted: usage]`
- `docs/orchestration_state.md`

### Rule 16: `regex:"platform":\s*"(?:macOS\|Darwin)[^"]*"==>"platform": "[redacted: OS version]"`
- `docs/evidence/c_verify_results.json`
- `results/independent/c_verify_results.json`
- `results/phase1/manifest.json`

### Rule 17: `regex:\(main, [A-Z][a-z]{2} +\d+ \d{4}, [\d:]+\) \[Clang [\d.]+ \]==>[build details redacted]`
- `docs/evidence/c_verify_results.json`
- `results/independent/c_verify_results.json`
- `results/phase1/manifest.json`
- `results/reproducibility.json`

## Not redacted (deliberately)

- Public third-party e-mail addresses inside fetched evidence pages, IP-like version numbers, 32-hex hashes, the organisation name `Carraway-and-Gatsby`, the public repo `Carraway-and-Gatsby/cardiac-simulator`, model names, generic OS and Python/NumPy versions.
- The earlier GitHub feature-flag captures have now been replaced entirely by rights stubs.
- The agent name `Hermes` and the `.hermes/skills` relative path are retained; numeric UID strings are redacted by the effective rule file.
- Other commit author identities are retained. Selected owner aliases are normalized by the mailmap.

## Verification

- Re-scan of all three branches and all commit messages: zero hits for local paths, user/host names, private repository name, request IDs, machine fingerprints, secrets, token counts. The `account_billing` pattern still matches the redaction placeholder text itself and the third-party flag names above.
- The earlier privacy-only audit parsed all 21 changed `.json`/`.ttl` files. The rights verifier additionally parses every historical version of each protected JSON path.

## Third-party content

The reproducible pipeline also transforms all historical versions of the paths
listed in `RIGHTS.md`, after the privacy replacements. Whole-file REMOVE items
and the integrator-selected UNSURE captures become provenance stubs at the same
paths; JSON paths contain valid JSON stub objects. Each stub records the source,
retrieval date, SHA-256 and size of that version's original bytes.

Only the two complete publisher abstracts in `docs/c_sources.json` and
`docs/evidence/c_quotes.json`, the non-open-access abstracts in
`docs/evidence/d_epmc_bibliographic_core.json`, and the PMC3098554 CC BY-NC
abstract in `docs/evidence/d_epmc_search_chase_desaive_oa.json` are replaced
inside otherwise retained JSON. The marker is
`[abstract omitted: publisher copyright; see DOI/PMID]`.

`docs/evidence/b_opb_excerpt.json` retains identifier/label XML and provenance;
definitions, comments and restrictions are removed. The two Smith CellML
encodings remain unchanged under the binding PMR CC BY 3.0 decision; their
embedded abstract is an explicit exception to the phrase scan. Attribution is
in `NOTICE.md`. All ledger SHA-256 values continue to refer to original bytes.

The four published local branches are `main`, `codex/applied-validation-fix`,
`codex/ontology-graph-view`, and `hackathon/experiment-agent`. Statements above
about the earlier three-branch snapshot describe that earlier privacy-only run.
The pipeline includes public documentation within each rewritten commit. Each
historical rights record lists only versions in that commit’s ancestry, so source
growth does not backfill future hashes into older commits. No network service or push is involved.
