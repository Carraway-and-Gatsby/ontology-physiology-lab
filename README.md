# Ontology-Guided Physiological Simulation Engine

Experimental Phase 1 research software. **Not for diagnosis, treatment selection, or patient-specific prediction.** No patient data are used. Numerical simulation is deterministic and requires no LLM or network connection after installation.

## What works

- A closed-loop six-compartment cardiovascular ODE model: LV, systemic arteries/veins, RV, pulmonary arteries/veins; four ideal diode valves; linear vascular compliances and resistances; prescribed time-varying ventricular elastance.
- Three reproducible scenarios: computational baseline, reduced LV contractility, and illustrative partial contractility restoration. These are separate runs from identical initial volumes; they are **not** a timed clinical treatment sequence.
- Headless plots, full sampled CSV trajectories, a local HTML result viewer, strict JSON summaries, parameter-change records, and checksummed execution manifests.
- 34 annotated variables with verified external concept labels, explicit local extensions, named-graph RDF/TriG export, and checked producer-to-consumer unit conversions.
- Numerical, dimensional, semantic, independent verification, regression, failure-path and reproducibility tests.

**All physiological numeric defaults are exploratory, not fitted literature parameters. The baseline is elevated-pressure and must not be described as a healthy adult reference.** Structural equations were informed by inspected sources, but this simplified model does not replicate a published reference trajectory.

## Install and run

Prerequisites: Python 3.11+ and `uv`, or an equivalent Python virtual-environment/pip workflow. Commands below were exercised using Python 3.11.15 on macOS ARM64. Run from this directory:

```sh
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements.lock -e .
.venv/bin/python -m physiosim --config experiments/phase1.json --output results/phase1
.venv/bin/python -m pytest -q --junitxml=results/tests.xml
```

Once installed, `physiosim --config experiments/phase1.json --output results/phase1` is the equivalent console command when the virtual environment is activated. Dependencies are pinned in `requirements.lock`; automatic downloads are only needed during installation.

Open `results/phase1/index.html` locally in a browser. No web server is needed. On macOS:

```sh
open results/phase1/index.html
```

Output files:

- `comparison.png`: last three beats of pressure, flow, ventricular volume and an LV pressure-volume loop.
- `transients.png`: full-run pulmonary venous pressure and cycle-integrated cardiac output.
- `{baseline,reduced_contractility,partial_contractility_restoration}.csv`: time in seconds; six volumes in mL; six pressures in mmHg; six directed flows in mL/s. Samples include the initialization transient. These are uniformly sampled solver outputs, not native adaptive solver steps.
- `summary.json`: exact parameters, perturbations, solver settings, final-beat metrics and audits.
- `variables.json`, `annotations.trig`: machine-readable variable metadata and RDF named graphs.
- `semantic_benchmark.json`: every synthetic connection fixture, decisions and confusion counts, including a known false acceptance.
- `manifest.json`: dependency/platform information, configuration hash, implementation hashes and output checksums.

Exit status 0 means all scenarios passed the runtime conservation/positivity/valve audit and the declared sampled periodicity gate. Status 2 preserves output but marks at least one scenario as transient/nonperiodic. Status 1 indicates an execution/configuration error. Passing these checks is not biological validation.

The canonical experiment uses 60 cycles, 400 samples/cycle, DOP853, rtol=1e-9, atol=1e-10 mL and maximum step T/200. Its periodicity gate is a maximum six-volume last/prior-beat waveform difference of 0.1 mL. This is a modest software milestone gate, not the stricter prospective multi-beat convergence protocol in `docs/verification_protocol.md`.

## Verify a clean wheel installation and repeatability

```sh
uv build --wheel
uv venv --python 3.11 .clean-venv
uv pip install --python .clean-venv/bin/python -r requirements.lock dist/ontology_physiosim-0.1.0-py3-none-any.whl
.clean-venv/bin/python scripts/verify_reproducibility.py
.clean-venv/bin/python scripts/verify_independent.py
.clean-venv/bin/python -I -m pytest -q --junitxml=results/tests.xml
.clean-venv/bin/python scripts/generate_report.py
```

The reproducibility script invokes the installed wheel twice in isolated Python mode, checks numerical CSV byte identity and summary equality, and writes `results/reproducibility.json`. It also verifies that the import came from `site-packages`, not an editable source checkout. This demonstrates same-host/same-dependency replay, not cross-platform bitwise identity. RDF serialization ordering is not used as a numerical reproducibility criterion.

## Python API

```python
from dataclasses import replace
from physiosim.models import Parameters
from physiosim.simulation import simulate
from physiosim.ontology import cardiovascular_registry, UnitConversion
from physiosim.ontology.bindings import connect_value

p = Parameters()
result = simulate(replace(p, emax_lv=p.emax_lv * 0.5),
                  cycles=60, rtol=1e-9, atol=1e-10,
                  max_step=p.period / 200)
print(result.metrics())

registry = cardiovascular_registry()
target = replace(registry['CO'], name='consumer_CO', unit='L/min')
co = connect_value(result, 'CO', target,
                   conversion=UnitConversion('mL/s', 'L/min'))
```

`validate_connection` checks direct variable equivalence, not causal adjacency. A pressure port cannot be directly equated to a flow port; the component's mathematical resistance law must implement that relationship. `connect_value` actually applies the checked conversion. The topology is still statically implemented; this is not an automatic multi-model ODE composer.

`ParameterChange.apply` makes an immutable dataclass replacement and an audit record. Its `time_s` is recorded metadata, not a scheduler. The canonical runs apply changes at time zero. No drug-dose or PK/PD model is included.

## Source and validation documentation

- `docs/physiology.md`: adopted/modified equations, every parameter, assumptions, units, source evidence and core API.
- `docs/ontology.md`: exact concept URIs, provenance, local concepts, connection rules and limitations.
- `docs/ecosystem.md`: inspected existing repository and Physiome/CellML, OpenCOR, SemSim/SemGen, CircAdapt and Pulse access/license findings. No external simulation code was executed or incorporated into the numerical engine.
- `docs/verification_protocol.md`: broader prospective scientific verification plan; not every proposed gate is implemented.
- `docs/independent_verification.md`: independent executed checks and remaining gaps.
- `docs/research_report.md`: generated current results, failures, claim boundaries and next steps.
- `docs/decisions.md`: concise architecture/scientific decision record.
- `docs/evidence/`: retained retrieval evidence, citation ledgers, parameter provenance and verification records.
- `docs/evidence_review/`: 2026-11-01 literature evidence review for the Smith 2004 semantic layer: evidence cards with quotations, a 76-variable/32-equation dictionary of the canonical CellML, candidate concepts, unresolved conflicts (including the kPa/mmHg label question) and rejected connection cases. Review only; no OWL, model or registry change. Earlier development outputs are historical; `results/phase1/` is the canonical current experiment.

## Scientific limits and next step

The model omits separate atria, septal/pericardial interactions, valve inertia, nonlinear passive ventricular mechanics, reflexes, renal regulation, respiration, oxygen transport and pharmacology. Positive parameter values are only a mathematical-domain check, not validated physiological ranges. Pulmonary venous pressure is a lumped reservoir pressure, not a measured atrial pressure or evidence of pulmonary edema.

The semantic benchmark is a small hand-designed synthetic fault-injection experiment. Its unassisted condition accepts submitted mappings without checking; no human productivity study was conducted. Correct-looking metadata attached to the wrong numerical data remain a deliberately demonstrated failure. Ontology-guided reliable model composition remains a research hypothesis.

Before cardiorenal coupling, prioritize a licensed reference-model reproduction with parameter-level provenance, better pressure/flow waveform calibration, stronger periodicity and sampling checks, and uncertainty/sensitivity analysis. A subsequent renal research spike should define an explicit renal perfusion-flow port and an external fluid-balance source/sink contract, then test conservation with those sources/sinks. GFR, sodium balance, RAAS and drug predictions remain unimplemented. No Streamlit service, deployment, remote push or clinical model has been created.

Passive atrial extension: [four_chamber_m1](docs/physiology_four_chamber_m1.md) provides a separate eight-volume explicit-parameter engine and a synthetic demo; the six-compartment API remains available.
