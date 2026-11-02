# Ontology-grounded synthetic experiment agent

A researcher supplies a model hypothesis. The agent inspects local parameter and
ontology contracts, executes this repository's real closed-loop engine for a
baseline and intervention, and emits JSON checked against retained tool receipts.
This is synthetic exploratory research tooling. Parameters and outputs are not
clinically validated, patient predictions, physiological targets or medical advice.

The implementation adds no dependencies and changes no engine or ontology code.
No provider was contacted during development or tests. Offline evaluation measures
infrastructure correctness; it does not establish LLM mapping accuracy or API
compatibility with any live service.

## Architecture and entry points

`physiosim.agent.loop.run_agent(hypothesis, provider=..., provider_name='meta',
model=None, extra=None, max_steps=8, commit=None, wall_clock_s=180,
max_experiments=6, no_classifier=False)` returns:

```text
{report, verification, trace, provenance, usage, classifier}
```

The loop runs the deterministic guard before creating a live provider. An allowed
request then receives a separate no-tool scope classifier call using that same
provider. Either layer can refuse. After both checks pass, it sends the repository-specific research system prompt and JSON Schema tools to
an OpenAI-compatible Chat Completions provider. Successful experiment receipts
are retained by the session independently of the bounded UI store. Final JSON is
verified, failures are fed back once for a report-only repair, and remaining
failures make the report `unverified`. There are at most eight ordinary model
calls by default plus one classifier and one repair call; a message may call at
most sixteen tools. Each session allows at most six `run_experiment` attempts and
180 seconds including provider retries, classification, solvers and repair. The
portable cooperative deadline uses `time.monotonic()` before every model/tool
call and after each returns, except final assistant replies: those proceed to local
verification even if the deadline expires during their call. Expiry before a classifier
decision returns a refusal with `Scope classifier unavailable.` Every HTTP attempt, including retries and classifier
format fallback, gets `min(configured_timeout, remaining_seconds)`; retry backoff
also fits the remaining budget. No signals or process timers are imported or
changed, so sessions work in threads, ASGI workers and Pyodide. A synchronous
solver or custom provider finishes its current call before the next deadline
check; this is not a hard interrupt. Solver cycles remain capped at 80. Python
callers may use `wall_clock_s=None` to disable the session deadline; configured
HTTP timeouts still apply. Expiry returns `stopped_budget` with the completed
receipts and code-generated verified values retained. Further experiment calls
beyond `max_experiments` return `{"error":"budget_exhausted"}` as tool results,
allowing the model to finish from existing receipts.
CLI overrides are `--wall-clock-s`, `--max-experiments` and `--max-steps`.
Exhaustion and provider failures produce an explicit unsuccessful result, never
invented findings. Only one model is supported within a final report.

Modules:

| Module | Purpose |
| --- | --- |
| `catalog.py` | Dataclass-derived scalar ports, conservative ranges, existing anatomical contexts |
| `tools.py` | Paired simulation, ontology/evidence lookup, metrics and bounded UI traces |
| `guard.py` | Normalized English/Korean table-driven screen, classifier policy and fixed refusal |
| `verify.py` | Closed-schema checks against trusted session receipts |
| `narrative.py` | Receipt-only labels, units, diagnostics and narrative |
| `budget.py` | Cooperative monotonic session deadline |
| `llm.py` | urllib client, presets, redaction, retries, scripted FakeProvider |
| `tool_protocol.py` | Shared tool schemas and strict JSON/argument validation |
| `loop.py` | Session receipts, one repair and usage/trace |
| `provenance.py` | Local-context PROV-O JSON-LD with runtime source hashes |
| `__main__.py` | CLI and output artifacts |

`tools`/`catalog` import only stdlib, NumPy, SciPy and the lightweight engine
modules. They never import `physiosim.ontology`, rdflib, pint or matplotlib.
`knowledge.json` bundles exact anatomy/source records and a small index of real
repository evidence lines with original file digests. Package data is included in
the wheel; a checkout or documentation tree is not needed for tool execution.
Evidence paths remain repository-relative source locators when installed.

M1 has no engine defaults. The agent explicitly chooses the existing demo's
`synthetic_fixture()` values, reproduced in a lightweight helper and tested for
exact equality to that function. These are synthetic test-design inputs.

## Tools

All functions accept JSON-compatible arguments and return JSON-compatible values.
`dispatch(name, arguments)` converts unknown names/arguments into structured
errors. No tool performs network access. Timings are observational; numerical
results, configurations and content-derived run identities are deterministic for
a fixed implementation/runtime, not guaranteed bit-identical across platforms.

| Tool | Arguments | Result |
| --- | --- | --- |
| `list_parameters` | `model: phase1\|m1` | Ports with name, model, unit, default, `[min,max]`, description, binding or null |
| `lookup_ontology` | `query: string` | Matching local entities, original IDs/labels, synonyms if recorded, parameters and directed source relations |
| `run_experiment` | `model`, `intervention`, optional `baseline_overrides`, `cycles` | Run ID, common settings, both parameter/metric receipts, periodicity, deltas, warnings and timings |
| `get_evidence` | `entity_or_param: string` | Real repository path, one-based line, anchor, exact line excerpt and scope; unknown queries return `[]` |
| `get_timeseries` | `run_id`, optional `names` | UI: selected arrays; LLM: min/max/mean and at most 60 points per series |

Interventions use absolute numeric values or `{"scale": factor}` relative to the
actual baseline after overrides. Baseline overrides accept absolute numbers only.
Volume tuples become scalar ports such as `initial_volumes.lv` and
`unstressed_volumes.la`; original compartment order is retained on reconstruction.
There are 28 Phase 1 ports and 36 M1 ports. Forty-four model-specific entries have
an anatomical binding (13 Phase 1, 31 M1).

Ranges are default ×0.1 through ×5, intersected with positive finite engine
requirements, systolic fraction capped at 0.95, and individual Emax/Emin bounds.
Both endpoints and joint changes are passed through engine validators. These are
exploration limits, not claims of biological plausibility. Unknown parameters,
booleans, nonfinite numbers, invalid scales, cycles outside integer 1–80 and joint
Emax < Emin produce `{"error":{"code":"invalid_request","message":"..."}}`.
Integration/trajectory failures use `engine_failure`; no tolerances are silently
relaxed. Scalar ranges do not guarantee solvability of every joint configuration.

Binding IDs and labels come from the existing anatomical v2/source records.
Ventricular elastance follows the legacy organ context; M1 atrial elastance uses
a cavity context without selecting a wall/myocardium mechanical bearer. Existing
Phase 1 peripheral compartments remain project-local, so their bindings are null.
M1 vascular lumen context is not identity with an entire lumped vascular bed;
FMA-primary nodes retain Uberon as a related structure. An FMA IRI is returned
only where recorded by the source, otherwise its existing CURIE suffices. There
is no dedicated anatomical path binding for systemic, pulmonary or venous inflow
resistances, nor one for systolic fraction. No ID is minted to fill a gap.

Source `part_of`/`located_in` relations retain contextual template endpoints,
review decisions and the statement that source claims are not engine axioms.
Shared blood IDs do not collapse their separate LA/LV templates. No new external
ontology validation, identity assertion, numerical binding or calibration occurs.

## Solver and metric semantics

The default is 12 cycles, explicitly shorter than the documented Phase 1 40-cycle
and M1 30-cycle demos. Both conditions use 400 samples/cycle and DOP853. Phase 1
uses rtol 1e-7, atol 1e-8 mL; M1 uses rtol 1e-9, atol 1e-10 mL. The explicit
maximum step in seconds is **identical for the pair**:
`min(baseline_period, intervention_period)/100` for Phase 1 and `/200` for M1.
This equals the documented demo step for unchanged rate and uses the smaller step
for both conditions when rate changes. Each run starts independently from its
own declared initial volumes. A rate intervention keeps cycle count identical,
so elapsed durations differ and are reported. Solver settings cannot be changed
through parameter intervention ports.

All summary metrics analyse the **last complete beat, including both endpoints**.
The returned `analysis_window_s` identifies that interval for each condition.
Engine `result.metrics()` values are preserved exactly under their original names.

| Metric | Definition |
| --- | --- |
| Phase 1 `stroke_volume_ml` | Engine trapezoidal integral of sampled forward aortic flow over final beat |
| M1 `lv_stroke_volume_ml`, `rv_stroke_volume_ml` | Engine differences of solver-integrated cumulative aortic/pulmonary-valve flow states over final beat |
| `cardiac_output_l_min` | Engine LV forward SV / final-beat duration ×60/1000; M1 alias of `lv_cardiac_output_l_min` |
| `lv_ejection_fraction` | Engine `(sampled LV maximum volume - minimum volume)/maximum`; M1 alias of its sampled EF |
| `<compartment>_pressure_{mean,min,max}_mmhg` | Sampled trapezoidal time integral/duration, or sampled extrema, for every compartment |
| `<compartment>_volume_{mean,min,max}_ml` | Same summaries for every compartment volume |
| `<edge>_forward_volume_ml` | Trapezoidal integral of `max(Q,0)` over final beat |
| `<edge>_backward_volume_ml` | Positive magnitude: trapezoidal integral of `max(-Q,0)`; ideal diodes return zero |
| `<edge>_mean_flow_ml_s` | Trapezoidal integral of signed Q divided by beat duration |
| `delta.abs.KEY` | Intervention metric minus baseline metric |
| `delta.rel.KEY` | Absolute delta divided by absolute baseline value; null for zero baseline or unavailable value, never Infinity |

Edge forward/backward integrals are sampled quadrature, and therefore need not
exactly equal M1 solver-integrated SV. EF is volume excursion and need not equal
integrated ejected throughput during filling/ejection overlap or transients.
Pressure is the engine's common gauge with fixed zero external pressure, not a
clinical or absolute pressure measurement. Means/extrema and sampled Phase 1 SV
can depend on sample density. Engine diagnostics such as whole-run volume drift
remain in the metrics under their original documented meanings. Nonfinite
unavailable engine diagnostics are converted to JSON null, never zero.

The periodicity diagnostic compares up to the last three successive beat pairs
at identical phases. For each pair and compartment it takes the maximum absolute
volume waveform difference divided by `max(max(abs(prior compartment waveform)),
1 mL)`. The maximum across pairs/compartments must be **strictly below 1e-3**.
With one beat it is unavailable and does not pass. With two/three beats it uses
one/two comparisons and reports their count. Each nonpassing condition gets a
warning; every shortened run gets a duration warning. This modest relative
settling diagnostic is not the repository's stricter multi-beat absolute-volume
validation criterion, a convergence proof, or evidence of biological validity.

The process-local LRU store has a **64 MiB total byte cap** (`MAX_STORE_BYTES`)
and an additional sixteen-run cap. Access refreshes LRU order. Retained values
include the receipt, owned NumPy float64 arrays for at most the final three
complete beats (1,201 points), a cached UI view with at most 601 points per
series, cached min/max/arithmetic means and source hashes. Byte accounting
includes array buffers and Python metadata; oversize runs are evicted. A real
80-cycle M1 regression checks that one stored run stays below 8 MiB. Temporary
solver trajectories are released after the run and are not held by array views.

`get_timeseries(..., full=True)` returns the retained final three beats, not the
entire solve. The default uses the cached 601-point UI view. The model receives
cached statistics over those final three beats and at most 60 uniformly selected
points. Statistics and source hashes are computed once during the run, without
repeated full-trajectory copying or JSON serialization. Full arrays never enter
model messages or provenance. Names include `time_s`, `pressure.lv`, `volume.la`
and `flow.mitral`. Returned JSON arrays are copies; eviction returns `unknown_run`.
Numeric verification retains full session metric receipts independently of the
trajectory store. Run IDs hash model, full baseline/intervention values, settings
and engine source hashes; timings do not alter IDs.

## Final report schema v2 and verification

`src/physiosim/agent/report.schema.json` uses `oneOf` for all v2 report envelopes:
`completed`/`completed_with_warnings`, `unverified`, `refused`, `error`, and
`stopped_budget`. Each has closed properties and `schema_version: "2.0"`.
Successful reports have `status`, `hypothesis`, `model`, `verified_summary`, `runs`,
`parameter_changes`, `ontology_ids`, `evidence`, `findings` and fixed `limitations`.
Runtime checks have no JSON Schema dependency. Tests validate every FakeProvider
eval report, CLI dry-run output and a synthetic example of every envelope, using
jsonschema if installed or the in-repository test validator for this subset.

Code owns every verified display field. `narrative.py` derives labels and units
from metric paths and its metric/compartment tables; model labels are dropped.
`verified_summary` is a deterministic receipt template that reports:

- Every baseline override, including its catalogue default and unit, and every intervention.
- Each selected metric's baseline, intervention, absolute delta, percentage and direction.
- Cycles, periodic flags, maximum relative beat-to-beat changes and all warnings.

For example, a sentence's form is `Mean left atrial pressure
(la_pressure_mean_mmhg): <before> → <after> mmHg (<delta>, <percent>); <direction>.`
Only real receipt values fill those placeholders. Per-run `runs` records contain
`run_id`, `baseline_overrides` and a `diagnostics` block with `cycles`, complete
`baseline`/`intervention` periodicity records and `warnings`. The verifier checks
these fields and the generated narrative exactly against every session receipt.
Run-specific warnings or a non-periodic condition yield
`completed_with_warnings`; otherwise the status is `completed`. Always-present
synthetic-model and sampled-quadrature caveats are separate receipt `caveats`,
not `warnings`. No verified summary is emitted without a successful run.

A finding has `id`, `label`, `unit`, `run_id`, `metric_path`, `value`, `decimals`
and `direction`. Paths resolve only in `baseline.metrics`, `intervention.metrics`,
`delta.abs` or `delta.rel`; null/nonfinite metrics cannot be numeric findings.
Values must equal exact Python rounding with at least three significant figures,
or use `decimals: null` and the exact receipt value. Code fills low-precision model
values directly from receipts. Nonzero metrics never display as zero. Directions
use a declared noise tolerance `10 * (solver_atol + solver_rtol * metric_scale)`,
where scale is the larger absolute baseline/intervention value. Inside that
threshold the structured direction is `unchanged` and prose says **no meaningful
change**. This is a numerical display convention, not a physiological threshold.

The model's final message is parsed only for structured fields. Free model
prose, legacy summaries, commentary and unknown top-level fields are discarded;
there is no commentary UI, screen, flag or CLI output. Labels, units, finding IDs,
limitations and the verified narrative are generated by code. Other strings in a
successful report must exactly match the user hypothesis or trusted structured
receipts (parameter names, ontology IDs, evidence records and metric paths).
Fabricated structured values still fail verification.

Parameter changes must exactly match all session receipts, and each successful
run must be cited. IDs must come from this session's `lookup_ontology` results or
catalogue bindings of changed/overridden parameters. Each bound parameter needs
its context ID. Evidence must match an actual `get_evidence` call for a changed
parameter, override or related entity; unrelated calls do not qualify. Unknown
top-level and finding keys are discarded before verification; finding
IDs, labels, units and directions are code-generated. Fabricated values, altered
diagnostics and missing required structured fields fail.
The fixed hypothesis is echoed exactly. Semantic hypothesis-to-parameter mapping
and biological validity still require researcher review.

A failed check receives one report-only repair with exact failure paths and a
receipt-backed example. Further failure yields the minimal `unverified` envelope:
a fixed note, canonical limitations, and a `response_hash` receipt containing
`sha256`, `chars` and `stored: false` when a final message was received. It never
contains raw responses or rejected findings. Completed engine receipts remain in
the trace. An unavailable repair also retains this unverified outcome. Refusals
contain a fixed refusal and optional fixed guard note; errors contain a fixed
failure label. `stopped_budget` includes completed run diagnostics, exact parameter
changes and code-generated findings, plus a verified receipt narrative when any
run succeeded. Budget findings use valid metrics from the last model findings, or
recognized metric names/labels in the hypothesis (including LA pressure, stroke
volume and cardiac output). If no requested metric is known, the documented
default is `stroke_volume_ml`. Values always come from completed run receipts.
Its overall verification remains false because the session stopped.

## Scope guard

Before any tool use, two independent layers can veto a prompt:

1. `guard.py` applies NFKC normalization, removes Unicode format/zero-width
   characters, maps common English homoglyphs and case-folds. Auditable `TERMS`
   and `RULES` tables cover person plus condition/measurements, relatives in
   English/Korean, drugs/medications, dosing in context, diagnosis/treatment,
   personal health questions and symptoms/emergencies. It also covers third-person
   condition requests, clinician recommendations, surgery/valvotomy, drug classes
   (beta blocker, calcium channel blocker, nitrate, ACE inhibitor, diuretic,
   anticoagulant, rate control) and Korean
   counterparts, plus spaced/hyphenated/underscore patient and dosing obfuscations.
   Korean 약 is anchored to drug contexts, allowing 약간 and 요약. Solver phrases
   `safe for convergence` and `numerically safe` remain allowed; clinical risk
   words such as harmful/concerning still trigger the health-context rule. `should we expect`, model
   parameter `dose-response`, `treat X as the intervention`, `emergence` and
   explicit Korean non-diagnostic disclaimers are accepted.
2. One same-provider LLM call, without tools, must return exactly
   `{"in_scope": bool, "reason": str}` under a short scope policy and strict JSON
   schema. The hypothesis is JSON-encoded inside explicit untrusted delimiters;
   the policy forbids following embedded instructions. Requests cap the classifier
   at 200 tokens and ask for a reason of at most
   12 words. OpenAI uses `max_completion_tokens`; other presets use `max_tokens`.
   An HTTP 400 naming either token field permits one retry with the other field.
   An unsupported `response_format` HTTP error separately retries once without that
   field; strict duplicate-key/type/extra-key local JSON checks still apply.
   Malformed replies, tool calls and provider errors fail closed. `--no-classifier`
   explicitly disables this layer while retaining the deterministic veto.

`FakeProvider` has independent
scripted `classifier_answers`, including errors, without consuming tool scripts.
The guard is still not a proof against every language or adversarial paraphrase.
The application is synthetic research tooling only.

## Provenance and traces

Each session has an LLM `prov:SoftwareAgent`, a software `prov:SoftwareAgent`, a
session `prov:Activity`, and separate activities for tools, classifier and model calls. Each call uses a
configuration `prov:Entity` and generates a result `prov:Entity`; associations,
attribution and timestamps use PROV-O predicates. JSON literals preserve validated
numeric configuration, baseline/intervention parameters, solver settings and output
receipts; free string arguments and echoed queries/errors use text digests.
Every tool, classifier, model and repair activity links to the session and
preceding activity with `prov:wasInformedBy`. Assistant result entities are
attributed to the LLM agent, which records provider and model; only tool receipts
are attributed to the software agent. The final report
is a `prov:Entity`, generated by the session and derived from cited run result
entities. Labels use `rdfs:label`; the local context declares JSON-LD `@version: 1.1`.
Timeseries provenance contains hashes rather than arrays. Activities record engine commit (passed or local `git rev-parse HEAD` if available),
package version, provider and model. Runtime engine SHA-256 hashes capture observed
source bytes; a checkout commit alone cannot identify uncommitted edits. Result
entities hash deterministic JSON serialization of the actual receipt, including
observational timing fields. Identical fixed inputs/timestamps serialize identically;
fresh wall-clock timestamps/timings make fresh session documents different.

The JSON-LD context is local and needs no network or rdflib at runtime. Trace
entries contain assistant tool calls (function name and arguments), tool receipts
(compact statistics/points for timeseries), summaries, timing and timestamps.
Every assistant free-text content, including valid final JSON, classifier and
repair messages, is replaced in both trace and provenance by only
`{"sha256": "...", "chars": N, "stored": false}`. No free model prose or raw
assistant JSON is persisted. Tool names persist only when registered; unknown names become `unknown_tool`.
Arguments persist only after strict JSON-object and tool-schema validation;
invalid arguments and free string argument values persist as text digests.
Echoed ontology queries and tool error messages are also hashed in stored receipts.
Trusted engine receipts remain structured data. Classifier reasons are replaced by fixed code-generated labels. Tokens from provider usage are aggregated;
fake-provider token counts are zero, not a token estimate. Authorization/known
credentials are redacted and are never printed or put in provenance. HTTP errors
include the status and at most 600 characters of the response body, preferring
JSON `error.message` when present. The body passes through `redact()` with the
API key before truncation; request/response headers, URL and HTTP reason are not
included. Classifier/model call failures retain a redacted cause of at most
200 characters in the trace; invalid classifier JSON receives a fixed cause.
Redirects are refused to avoid
forwarding credentials. Retry backoff covers 429/5xx and transport failures with
bounded attempts and per-request timeout.

## Running

The shared development venv currently points to an older checkout. Prefix commands
with `PYTHONPATH=src` so this worktree is imported; do not reinstall over the owner's
shared environment. From this repository, use its supplied venv interpreter or a
Python environment with the existing engine dependencies installed.

```sh
export PYTHONPATH=src
# Offline, fixed scripted M1 triple-mitral mapping; still runs the actual engine.
python -m physiosim.agent --dry-run --out agent_eval/my-dry-run

# Meta final target; credentials are supplied in the environment, never arguments.
# MODEL_API_KEY must be set. Default model: muse-spark-1.3.
python -m physiosim.agent "Triple mitral resistance in M1 and compare LA pressure and stroke volume" --provider meta --out agent_eval/meta-run

# OPENAI_API_KEY must be set; use --model or LAB_LLM_MODEL.
python -m physiosim.agent "Halve emax_lv in phase1 and compare cardiac output" --provider openai --model YOUR_MODEL --out agent_eval/openai-run

# Optional request extensions: preset < environment < --extra-json (shallow merge).
export LAB_LLM_EXTRA_JSON='{"temperature":0.4}'
python -m physiosim.agent "Triple mitral resistance in M1" --provider openai --model YOUR_MODEL --extra-json '{"temperature":0.2,"reasoning_effort":"none"}' --out agent_eval/openai-extra-run

# ANTHROPIC_API_KEY must be set; OpenAI-compatible Chat Completions endpoint.
python -m physiosim.agent "Increase systemic resistance by 50% in M1" --provider anthropic --model YOUR_MODEL --out agent_eval/anthropic-run

# Local OpenAI-compatible endpoint, for example an installed open-weight model.
export LAB_LLM_BASE_URL=http://localhost:11434/v1
export LAB_LLM_MODEL=YOUR_LOCALLY_INSTALLED_MODEL
# LAB_LLM_API_KEY is optional for unauthenticated loopback services.
python -m physiosim.agent "Halve emax_lv in phase1" --provider custom --out agent_eval/local-run

python agent_eval/run_eval.py --provider fake --out agent_eval/my-fake-eval
python -m pytest -q -p no:cacheprovider
python -m pytest -q -p no:cacheprovider tests/test_agent_catalog_tools.py::test_pyodide_import_and_real_run_with_heavy_modules_blocked
```

Presets use `https://api.meta.ai/v1`, `https://api.openai.com/v1`, and
`https://api.anthropic.com/v1`; the client appends `/chat/completions`. Meta defaults
to `muse-spark-1.3`; `--model` overrides it. OpenAI, Anthropic and custom require
`--model` or `LAB_LLM_MODEL`. Custom uses `LAB_LLM_BASE_URL`/`LAB_LLM_API_KEY`;
plain HTTP is restricted to loopback hosts. Provider contracts/model availability
must be confirmed in a later authorized live integration run; none were tested
here. A real provider requires compatible tool calling and access to the chosen
model. The CLI dry run always demonstrates its fixed M1 mapping, even if a
positional prompt says otherwise; it is labelled as scripted and cannot establish
arbitrary prompt understanding. Python callers can supply a specific
`FakeProvider.for_experiment(model, intervention, metric=..., cycles=...)` instead.

`ProviderConfig.extra` is a dictionary merged into the Chat Completions payload
after the standard fields. `provider_config(..., extra={...})` and
`run_agent(..., extra={...})` supply the last override layer, used by CLI
`--extra-json`. Both `LAB_LLM_EXTRA_JSON` and `--extra-json` require a JSON object
with finite values. Merging is shallow and later keys replace earlier values;
model/messages/tool protocol fields and the classifier response schema remain
controlled by the client; request extensions cannot replace them.
The OpenAI preset defaults to `{"reasoning_effort":"none"}`: OpenAI requires this
setting for GPT-6.x function-tool use on Chat Completions. Users can override it
for other compatible model configurations. Meta, Anthropic and custom presets
have no extra fields by default. An explicitly supplied provider instance uses
its own configuration; dry runs remain scripted and never contact providers.

CLI output is `report.json` (envelope containing `report`, `verification`, `usage`),
`trace.json` (trace list) and `provenance.jsonld`. Existing output files are refused.
The printed summary reports synthetic scope, status, verification and cited values.
Use a new output directory per run. CLI returns nonzero on verification failure.

## Evaluation and observed evidence

`agent_eval/hypotheses.json` contains thirteen in-scope cases across both models
and fourteen clinical refusals including Korean. Each scientific case has expected parameter
ports, metric sign and freshly engine-derived baseline/intervention values.
`agent_eval/reference_runs.json` retains full paired receipts at the documented
demo durations. Cases cover mitral resistance, LV peak elastance, rate, systemic
and pulmonary resistance, arterial compliance and initial volume. Expectations
were obtained by executing this engine, not by importing textbook signs.

`run_eval.py` records parameter/model mapping, real engine tool use, verifier pass,
guard behavior, expected-sign claim agreement, model steps, tokens and latency.
It writes full JSON results and a Markdown table, and can be run with each live
provider after credentials are authorized. FakeProvider receives each expected
mapping explicitly: **fake evaluation verifies orchestration, not LLM intelligence**.
All tests block network connections or mock the urllib transport. The lightweight
subprocess test blocks rdflib/pint/matplotlib via `sys.modules[...] = None` and runs
both actual engines. This tests the import boundary, not a new real-browser
Pyodide execution/parity run. Existing browser parity evidence lives in the
separate browser runner's `VERIFY.md`.

Remaining scientific limits include no calibration/reference-trajectory
validation, ideal no-reverse-flow valves, synchronous ventricles, passive M1 atria,
no reflex/drug/renal/FSI/pericardial/septal coupling, no clinical targets and no
patient data. Periodicity is a numerical diagnostic with a declared threshold;
source evidence supports context and model structure, not these numerical values.

### Evaluation updates for v2

`agent_eval/run_eval.py --provider fake` now covers the original cases, ten review
clinical counter-examples, and three formerly refused experiment phrasings. The
classifier has a separate correctness column/score; deterministic refusals get an
independent classifier-only evaluation. Fake classification is scripted and does
not measure a real provider's safety or interpretation. For sign scoring, alias
groups are derived programmatically by comparing every available metric across
all baseline/intervention reference runs for each model (`rel_tol=1e-12`, no
absolute tolerance). No alias pairs are hard-coded; groups and scores are saved
in evaluation results. Real provider runs remain the integrator's responsibility.
