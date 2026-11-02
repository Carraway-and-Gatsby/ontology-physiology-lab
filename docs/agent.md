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
model=None, extra=None, max_steps=8, commit=None)` returns:

```text
{report, verification, trace, provenance, usage}
```

The loop runs the deterministic guard before creating a live provider. Otherwise,
it sends the repository-specific research system prompt and JSON Schema tools to
an OpenAI-compatible Chat Completions provider. Successful experiment receipts
are retained by the session independently of the bounded UI store. Final JSON is
verified, failures are fed back once for a report-only repair, and remaining
failures make the report `unverified`. There are at most eight ordinary model
calls by default plus one repair call; a message may call at most sixteen tools.
Exhaustion and provider failures produce an explicit unsuccessful result, never
invented findings. Only one model is supported within a final report.

Modules:

| Module | Purpose |
| --- | --- |
| `catalog.py` | Dataclass-derived scalar ports, conservative ranges, existing anatomical contexts |
| `tools.py` | Paired simulation, ontology/evidence lookup, metrics and bounded UI traces |
| `guard.py` | English/Korean scope prefilter and fixed refusal |
| `verify.py` | Closed-schema checks against trusted session receipts |
| `llm.py` | urllib client, presets, redaction, retries, scripted FakeProvider |
| `loop.py` | Tool protocol, session receipts, one repair and usage/trace |
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
| `get_timeseries` | `run_id`, optional `names` | Baseline/intervention time and selected downsampled named arrays |

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

The UI store retains at most sixteen run pairs. Each series contains at most 601
uniformly indexed samples from up to the final three beats. Names are `time_s`,
`pressure.lv`, `volume.la`, `flow.mitral`, etc. Data returned to callers is copied.
Eviction produces `unknown_run`. Numeric verification uses full session receipts,
not the downsampled store. Run IDs hash model, full baseline/intervention values,
solver settings and observed engine source hashes. Timing changes do not alter IDs.

## Final report schema and verification

The machine schema is `src/physiosim/agent/report.schema.json`; runtime validation
is implemented without a JSON Schema dependency. A successful report has exactly
these keys (example placeholders are illustrative, not experimental findings):

```json
{
  "schema_version": "1.0",
  "status": "completed",
  "hypothesis": "exact original user prompt",
  "model": "m1",
  "summary": "The paired synthetic experiment completed; inspect the cited metrics.",
  "parameter_changes": [
    {"run_id": "actual-run-id", "parameter": "resistance_mitral", "baseline": 0.01, "intervention": 0.03}
  ],
  "ontology_ids": ["UBERON:0002135"],
  "evidence": [
    {"path": "actual repository path", "line": 1, "anchor": "L1", "excerpt": "exact source line", "scope": "exact receipt scope"}
  ],
  "findings": [
    {"id": "finding-a", "label": "Mean left atrial pressure", "run_id": "actual-run-id",
     "metric_path": "intervention.metrics.la_pressure_mean_mmhg", "value": 0.0, "decimals": 6, "direction": null}
  ],
  "limitations": ["copy all canonical LIMITATIONS strings verbatim"]
}
```

Every finding must resolve against a successful tool output from **this session**
and equal `round(actual_tool_value, decimals)` exactly. Precision is an integer
from zero through twelve; there is no loose relative-error tolerance. Metric paths
are limited to `baseline.metrics.KEY`, `intervention.metrics.KEY`, `delta.abs.KEY`
and `delta.rel.KEY`. Null metrics cannot become numeric findings. Direction is
null or `increase`/`decrease`/`unchanged`, checked against the unrounded absolute
delta for that metric, even when a rounded value becomes zero.

All explicit parameter change receipts from every successful run must be copied,
including scaled values resolved against baseline overrides. Every ID must exist
in offline repository data; a changed bound parameter must cite at least one of
its existing anatomical context IDs. Evidence must exactly match actual
`get_evidence` receipts. Hypothesis must echo user input, not become a container
for new model claims. Summary prose permits model identifiers (`Phase 1`, `M1`,
`four-chamber`), catalogue parameter names (`resistance_mitral`,
`initial_volumes.lv`), known ontology IDs listed in the report, session run IDs,
and section/ordinal references. An introduction such as "One paired synthetic M1
run" is also allowed. Quantitative values, percentages, units, multipliers such
as `3x`, and metric direction/magnitude claims (including "rose", "fell" and
"unchanged") belong in cited findings. The narrow exception is `triple`/`tripled`
directly attached to a named parameter, such as "resistance_mitral was tripled"
or "tripled the mitral resistance": every session change for that parameter must
be a tripling and must be copied exactly into `parameter_changes`. Tripling a
metric or a parameter without matching receipts fails. Finding labels continue
to prohibit digits and quantity/direction words. Clinical output text is
also scope-checked. Unknown fields, fabricated paths, mismatched numbers/changes,
missing limitations and uncited runs fail. Run metadata and source-locator numbers
are machine-matched metadata, rather than numeric experimental findings.

The verifier does **not** decide whether the selected parameter accurately
represents the natural-language hypothesis or whether its physiology is valid.
It can detect a report misdescribing the actual chosen intervention. A fully
consistent but conceptually mistaken LLM mapping remains possible and needs
researcher review. High fake-provider scores make no claim about that risk.

For example, "One paired synthetic M1 run compared the default mitral flow-path
resistance with a modified setting and reported mean left atrial pressure and
left ventricular stroke volume. All quantitative results and their directions
are in the findings. The periodicity check was satisfied, but that does not
establish physiological validity." passes the summary rule. "Mean LA pressure
rose to 8.1 mmHg in M1" fails it. The summary check is lexical, not a general
natural-language claim verifier.

The loop gives verifier failures back once, quoting each exact failing rule and
including an allowed summary and, when available, a receipt-backed finding example.
Repair may only return a final report;
new tool calls are rejected. Remaining failures make status `unverified` and mark
failed findings `UNVERIFIED`; individually matching values in a structurally failed
report are `VERIFIED_VALUE_ONLY`. The verification result lists all failures.
Guarded requests have a separate minimal `refused` envelope and no numeric claims;
provider/step failures have explicit `error`/`unverified` envelopes. These failure
envelopes are intentionally outside the successful-report schema.

## Scope guard

English/Korean regular expressions reject personal/patient requests, diagnosis,
treatment, dosing, medications, symptoms, emergencies and "should I" wording,
including prompts that also mention a model. The fixed refusal explains that this
is a synthetic unvalidated research model and asks for a synthetic experiment
rephrasing. The system prompt enforces the same scope independently. Model-only
requests such as "increase systemic resistance by 50%" pass.

This lexical guard is conservative, not a multilingual intent classifier or a
proof against all adversarial paraphrases. It can over-refuse clinical terms used
in abstract research and can miss unfamiliar wording. This system is only offered
as synthetic research tooling and must not be used for clinical decisions.

## Provenance and traces

Each session has an LLM `prov:SoftwareAgent`, a software `prov:SoftwareAgent`, a
session `prov:Activity`, and a `prov:Activity` per tool call. Each call uses a
configuration `prov:Entity` and generates a result `prov:Entity`; associations,
attribution and timestamps use PROV-O predicates. JSON literals preserve exact
arguments, baseline/intervention parameters, solver settings and output receipts.
Activities record engine commit (passed or local `git rev-parse HEAD` if available),
package version, provider and model. Runtime engine SHA-256 hashes capture observed
source bytes; a checkout commit alone cannot identify uncommitted edits. Result
entities hash deterministic JSON serialization of the actual receipt, including
observational timing fields. Identical fixed inputs/timestamps serialize identically;
fresh wall-clock timestamps/timings make fresh session documents different.

The JSON-LD context is local and needs no network or rdflib at runtime. Trace
entries contain model message/intent, tool name/arguments, full receipt and concise
result summary, timing and timestamps. Tokens from provider usage are aggregated;
fake-provider token counts are zero, not a token estimate. Authorization/known
credentials are redacted and are never printed or put in provenance. HTTP errors
include the status and at most 600 characters of the response body, preferring
JSON `error.message` when present. The body passes through `redact()` with the
API key before truncation; request/response headers, URL and HTTP reason are not
included. Redirects are refused to avoid
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
extensions can also override standard payload keys, so select them deliberately.
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

`agent_eval/hypotheses.json` contains ten in-scope cases across both models and four
clinical refusals including Korean. Each scientific case has expected parameter
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
