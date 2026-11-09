# CI checks and their limits

`research-ci.yml` runs on pull requests, pushes to `main` and
`hackathon/experiment-agent`, and manual dispatch. The existing two-Python
`verify` job, including its 25-minute timeout, is unchanged. Its results concern
the tests and synthetic numerical checks actually run in that checkout.

`smith-shacl` installs every pin in
`docs/evidence_review/shacl/requirements-shacl.txt` and runs the documented
command, `python -I docs/evidence_review/shacl/run_shacl.py`. That runner checks
dependencies and anatomical identifiers and compares all three fixture result
sets with `expected_results.json`; a mismatch fails the job. Non-conformance of
the translated Smith workspace is a recorded finding, as documented by the
runner, and does not itself fail the fixture controls.

## Conditional ontology gates

The detector checks for both `tools/generate_ontology_contracts.py` and
`docs/evidence_review/shacl/project/run_project_shacl.py`. When both are absent,
it writes **ontology gates not applicable: files absent** to the workflow
summary; ontology jobs are skipped. This is not an ontology pass. If exactly one
file exists, detection fails. When both exist, the workflow requires:

1. `tools/generate_ontology_contracts.py --check`.
2. `tools/generate_closed_shapes.py --check`.
3. The standalone `docs/evidence_review/shacl/project/run_project_shacl.py`.
4. All tests in `tests` and `tools/ontology_graph_view/tests`, with
   `ONTO_REQUIRE_SHACL=1`, across 24 matrix shards.
5. A successful `shard-coverage` audit after every shard and generator/control
   job succeeds.

These jobs install `requirements.lock` and the pinned SHACL requirements and
use Python 3.12.3. Ontology generators and tests validate the checkout's `src`
via `PYTHONPATH=src`, not an installed wheel; the standalone project runner also
inserts checkout `src` itself. The unused ontology wheel build/install is removed.
The reviewed validators require the checkout's trust anchors. Node must be
available for viewer layout tests; its absence fails the job. There is no
optional SHACL fallback. Independent generator/control checks
continue after an earlier check fails if installation succeeded. Shards run
whenever full collection succeeds, even after a generator/control failure;
the final audit still requires all those gates to have succeeded. Matrix
fail-fast is disabled so other shards can finish.

`scripts/ci_shard.py` collects through pytest hooks, sorts the complete relative
node ids, and assigns shard `i` the slice `nodeids[i::24]`. Each shard independently
recollects the suite and requires an exact match with the reference collection.
It records actual call reports and all collection/setup/call/teardown skips,
and adds a `ci_nodeid` property to every JUnit testcase. The final audit requires
every shard's successful execution output and JUnit, checks each partition and
its execution identities, and compares their multiset union with the full
collection. Missing/duplicate tests, collection drift, skips (including xfails),
failures, errors, and missing artifacts fail. No test count is hard-coded as a
passing assertion; collection determines the expected count for each checkout.

The receipts-based `tools/report_lung_adversarial.py --check` is **not run** by
this workflow, and there is no passing claim for that report. The individual
adversarial tests still run in the required suite. Likewise,
`tools/select_lung_evidence.py --check` is **not run in CI**: it needs an external
upstream root unavailable to CI. Tests of retained inputs do not establish a
fresh comparison with that upstream root.

## Timing evidence and projection

Original CI-N6 measurements were made on the integrator Mac on 2026-11-09, using
Python 3.11.15 and the existing pinned SHACL environment, with wheels built from
scratch copies. The private candidate was the supplied `8ceb573` plain copy;
its original directory was not modified. The scientific environment uses
`MPLBACKEND=Agg`, `PYTHONHASHSEED=0`, and one OpenBLAS/OMP thread, matching CI.
Dependency installation is excluded from test timings.

The public suite really ran: **523 passed**, no failures/errors/skips, pytest
111.95 seconds (112.157 seconds including interpreter startup). Supplied public
CI timings were 170.5 and 231.8 seconds. Dividing those pytest times by 111.95
gives a runner/local duration ratio of **1.5230–2.0706**; projection uses the
slower ratio. Collection and Smith smoke checks overlapped part of the local
baseline, so this is an approximate calibration.

Prior local JUnit output for 1,581 tests was used only to choose representative
shards and estimate imbalance. It matched all freshly collected node ids.
Its SHA-256 is
`b1471dfb2d83ff6e35e457e655ec7a1045747759781739b3ca1516bd867683c2`.
Sorted round-robin with 32 shards would group two long tests into a 4,045.980
second shard. With 24 shards, the largest prior-duration sum is 2,833.584
seconds on shard 22. Large determinism tests launch complete subprocess suites;
dividing a six-hour total by the shard count would underestimate the maximum.
The eight-seed fixture is shared in a serial run but is paid separately by
shards 10 and 13. Adding its prior 746.848 seconds to shard 13 gives 1,323.828
seconds, still below shard 22. Other fixture/setup costs and runner differences
remain reasons to treat the eventual timing calculation as a projection.

Fresh measurements include shard 22 (slowest expected), 10 (subprocess-heavy),
and 0 (ordinary workload). They ran concurrently in independent scratch copies,
alongside other local CI validation, so the measured times include possible host
contention. JUnit and execution identities matched each assigned partition.

| Shard (zero-based) | Tests passed | Skips | JUnit seconds | Wall seconds | Prior duration sum, seconds |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0 | 66 | 0 | 433.895 | 434.969 | 549.762 |
| 10 | 66 | 0 | 1,027.540 | 1,027.918 | 1,334.246 |
| 22 | 65 | 0 | 2,571.691 | 2,572.031 | 2,833.584 |

These are **197 distinct representative tests passed**, not a fresh full
1,581-test pass. The slowest measured shard includes the determinism test's
complete subprocess module run; no subprocess workload was omitted.

The planning local maximum is the larger of the fresh maximum (2,572.031 s)
and the largest prior duration sum (2,833.584 s). Apply the slower runner/local
ratio, a 10% workload margin, and a five-minute installation/startup allowance:

```text
max(2572.031, 2833.584) × (231.8 / 111.95) × 1.10 + 300
  = 6753.839 seconds = 112.564 minutes
```

Each shard has a **240-minute timeout**. The projected slowest shard uses
**46.902%** of that timeout, below the required 50%, and is well below GitHub's
six-hour job limit. Numeric-suite calibration may differ from SHACL and
subprocess performance; this calculation is a projection, not a runtime bound.

Other timeouts are 25 minutes for `verify`, 10 for `smith-shacl`, 5 for detection,
180 for `ontology-gates` (generators/project controls/collection), and 10 for
coverage. The public CI measurements do not justify raising `verify`'s timeout.
Independent review measured the standalone project SHACL runner at **1,304.4
seconds**, exit 0, under host contention. FIX1 measured standalone contracts
and closed-shape checks at **1.579** and **0.229 seconds**, and ontology collection
at **0.692 seconds**, all exit 0, using checkout `src` without an installed
ontology wheel. Installation was not timed. For a conservative
`ontology-gates` projection, retain the larger prior project-control test time
(1,978.167 seconds) and apply the same slower ratio, 10% margin and five-minute
installation/startup allowance as the shards:

```text
(max(1304.4, 1978.167) + 1.579 + 0.229 + 0.692) × (231.8 / 111.95) × 1.10 + 300
  = 4811.215 seconds = 80.187 minutes
```

This **projection** uses **44.548%** of the 180-minute `ontology-gates` timeout,
below 50%. It is not a measured GitHub job duration.

**Projection, not a GitHub ontology-tree result:** the first actual CI run of
the ontology tree must confirm the timing model. Local representative runs do
not establish that all 24 shards passed.

## Local validation and reproduction

YAML is loaded with Python/PyYAML. Structural checks require read-only contents
permission, immutable action SHAs, disabled persisted checkout credentials, the
complete shard matrix, and an unchanged `verify` job. The detector was exercised
against absent, present, and incomplete file sets. `actionlint` was unavailable
and was not run.

Both trees were freshly collected and their partitions checked for a complete,
disjoint union: 523 public tests using path `tests` (shards of 21–22, matching
`verify`'s testpaths) and 1,581 candidate tests using `tests` and
`tools/ontology_graph_view/tests` (shards of 65–66). These are collection counts,
not ontology pass counts. The public viewer directory has 19 tests: it runs only
in the ontology shards, so those tests do not run on the current public tree.
Collecting both workflow paths on the public tree yields 542 tests. The
Smith runner passed its three exact fixture comparisons locally; both ontology
generator checks also passed locally. The standalone project SHACL runner
passed all 61 controls (one expected conforming, 60 expected non-conforming).
Temporary pytest suites exercised the
helper's complete audit and rejection of missing shards, duplicate executions,
JUnit skips, missing JUnit identities, collection drift, runtime skips,
collection skips, and test failures.

All 24 public-tree shards also ran locally and the real coverage audit passed:
path `tests` only, 523 collected = 523 executed exactly once, zero skips. This
separate functional validation took 203.499 seconds overall while ontology
measurements were active; it is not the baseline used for runner calibration.

FIX1 repeated YAML loading, both tree partitions, the public absent-files path
and Smith SHACL locally. Candidate shard 23 then passed with the workflow's
exact command and out-of-checkout basetemp: **65 passed, zero skips**, 413.665
seconds wall time; JUnit and executed node ids matched its assigned partition.
Both targeted W25.a variants also passed (2 tests, 23.054 seconds wall time).
These runs used checkout `src` without an installed ontology wheel. The other
23 ontology shards were not rerun in FIX1; this is not a full ontology pass.

To reproduce the source-checkout ontology collection, one shard, and the final
audit, after installing both requirements files:

```sh
export ONTO_REQUIRE_SHACL=1 PYTHONPATH=src MPLBACKEND=Agg PYTHONHASHSEED=0
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
# Locally, create RUNNER_TEMP outside every checkout; GitHub provides it in CI.
export RUNNER_TEMP="$(mktemp -d "${TMPDIR:-/tmp}/ontology-ci.XXXXXX")"
python scripts/ci_shard.py collect --shards 24 --basetemp "$RUNNER_TEMP/ontology-pytest" --collection .ci-artifacts/collection.json tests tools/ontology_graph_view/tests
python scripts/ci_shard.py run --shards 24 --shard 22 --basetemp "$RUNNER_TEMP/ontology-pytest" --collection .ci-artifacts/collection.json --results .ci-artifacts/shards tests tools/ontology_graph_view/tests
# Run every other index 0..23 before auditing.
python -I scripts/ci_shard.py coverage --shards 24 --collection .ci-artifacts/collection.json --results .ci-artifacts/shards
```

## Security and integration limits

Workflow permissions are `contents: read`; every checkout disables persisted
credentials and every action uses a pinned commit. The new jobs use no secrets.
Uploaded ontology evidence consists only of the relative test collection,
execution output, and per-shard JUnit, retained for seven days. No Mac paths or
hostnames are embedded in the helper or workflow. The README badge reflects the
whole workflow. It shows passing when `verify` and `smith-shacl` succeed and the
ontology gates are not applicable (files absent); in that state no ontology
check ran. After the ontology files are published, passing additionally requires
`ontology-gates`, all 24 shards and `shard-coverage` to succeed.

The existing `verify` job's isolated installed-wheel invocation is incompatible
with the supplied ontology candidate's checkout-only trust anchors. A targeted
local probe reproduced a failure in `test_canonical_source_and_projection`
before SHACL execution. The job is preserved as requested; this future-tree
compatibility issue needs integrator resolution before an ontology publication
can have a fully passing workflow. Public-tree `verify` is unaffected.

A second publication blocker is W25.a (`isolated_site_packages`) in
`tests/test_ontology_round3g.py`: the candidate's `--basetemp=.pytest_tmp` puts its
fake site-packages path inside the checkout, where `trust_root()` walks up to
real trust anchors. Independent review reproduced 64 passes and one failure on
shard 23, plus the same failure in the W25.a SHACL test. Both pass with an
out-of-checkout basetemp. The ontology collection and shard commands now pass
`--basetemp "$RUNNER_TEMP/ontology-pytest"`; local reproduction must do the same.
This fixes the CI temporary-directory placement, but the test itself still
needs an owner-approved fix before ontology publication so its isolation does
not depend on invocation. The ontology candidate has not been changed.

Independent CI-N6 review requested these corrections. No ontology GitHub run,
commit, or push was performed here.
