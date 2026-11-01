# four_chamber_m1 1.0.0 — passive atria

SYNTHETIC/EXPLORATORY research software; not clinically validated. No patient
information, physiological calibration or published four-chamber reproduction.
Legacy six-compartment equations, identities and experiments remain independent.

## Numerical acceptance criteria (declared before implementation/test execution)

| Check | Absolute bound | Rationale |
| --- | --- | --- |
| Total volume drift | 1e-7 mL | Linear invariant, roundoff at ~5000 mL and short runs |
| Local balance residual | 1e-6 mL | Augmented linear invariant; wiring/roundoff only, not quadrature accuracy |
| Passive analytic subproblem | 1e-6 mL | expm solution, rtol/atol 1e-10; short 0.5 s interval |
| DOP853 tolerance refinement | 1e-5 mL | Compare volumes and integrals, 1e-9/1e-10 T/200 vs 1e-11/1e-12 T/400, 3 beats |
| Radau vs DOP853 | 1e-4 mL | Independent integration methods, 1e-10/1e-10, 2 beats |
| Large-step pulse | 1e-4 mL volumes; 1e-5 mL integrals | Resolving peak must prevent missing an entire opening |
| Simultaneous symmetric circuits | 1e-7 mL volumes; 1e-6 mL integrals | Symmetry with roundoff-scale event ordering differences |
| Sampling independence, replay, equilibrium, output diode law | Exact | Sampling cannot change adaptive integration; law recomputed without approximations |

These software bounds are fixed before observing results; no clinical target is
used. Failures must be diagnosed, not hidden by relaxed thresholds.

## Equations and contract

`MODEL_ID="four_chamber_m1"`, version `1.0.0`. State order is
`(lv, sa, sv, ra, rv, pa, pv, la)`. Every state is a total blood volume (mL),
not a stressed volume. Caller-supplied `V0` is the unstressed-volume parameter.
The sum of the eight initial volumes declares the total; it is never normalized.
There is no legacy volume-splitting/migration helper or anatomical identity claim.

| Edge (column order) | Source | Target | Law |
| --- | --- | --- | --- |
| aortic | lv | sa | ideal diode |
| systemic | sa | sv | signed resistor |
| venous_return | sv | ra | signed resistor |
| tricuspid | ra | rv | ideal diode |
| pulmonary_valve | rv | pa | ideal diode |
| pulmonary | pa | pv | signed resistor |
| pulmonary_venous | pv | la | signed resistor |
| mitral | la | lv | ideal diode |

For each edge `e`, `B[source,e]=-1`, `B[target,e]=+1`, and every other
entry is zero. Thus `dV/dt = B q`, `1^T B=0`, and `d(sum V)/dt=0`.
The versioned endpoint table is validated independently of conservation: swapping
an edge can conserve mass and still violate M1's topology.

```text
                  ao sys vr tc pv pul pvr mt
B (lv row)       = -1  0  0  0  0  0   0   1
  (sa)          =  1 -1  0  0  0  0   0   0
  (sv)          =  0  1 -1  0  0  0   0   0
  (ra)          =  0  0  1 -1  0  0   0   0
  (rv)          =  0  0  0  1 -1  0   0   0
  (pa)          =  0  0  0  0  1 -1   0   0
  (pv)          =  0  0  0  0  0  1  -1   0
  (la)          =  0  0  0  0  0  0   1  -1
```

With `T=60/HR` s and `phi=(t mod T)/T`, let `s=systolic_fraction`:

```text
a(phi) = (1-cos(2*pi*phi/s))/2, if phi < s; 0 otherwise
E_v(t) = Emin_v + (Emax_v-Emin_v)*a(phi), v in {lv,rv}
P_v = E_v(t)*(V_v-V0_v), v in {lv,rv}
P_a = E_a*(V_a-V0_a), a in {la,ra}, constant positive E_a
P_i = (V_i-V0_i)/C_i, i in {sa,sv,pa,pv}
dp_e = P_source(e)-P_target(e)
q_e = max(dp_e/R_e,0), for the four ideal diodes
q_e = dp_e/R_e, for the four signed resistors
Cumulative_e(t) = integral from 0 to t of q_e(u) du
```

The ventricular activation calls the existing `cardiovascular.elastance` function;
legacy code and behavior are unchanged. M1 has **eight volume states** plus eight
auxiliary flow integrals. There is no flow/inertance state.

Pressure reference (exact machine contract): "model gauge pressure relative to one
common fixed external pressure of 0 mmHg; no intrathoracic/pericardial pressure".
This is a declared mathematical gauge, with no assertion about atmospheric or
absolute pressure. All chambers/compartments share it; negative gauge pressures
are allowed. No pressure/volume clipping or conservation projection is applied.

| Quantity | Unit |
| --- | --- |
| Time / maximum step | s |
| Volume, initial/unstressed volume, cumulative flow, SV, solver atol | mL |
| Pressure | mmHg |
| Instantaneous flow / mean CO | mL/s (CO also explicitly converted to L/min) |
| Elastance | mmHg/mL |
| Compliance | mL/mmHg |
| Resistance | mmHg s/mL |
| HR | beats/min |
| Activation, systolic fraction, EF, solver rtol | dimensionless |

Parameters have no defaults. All scalar physiology inputs must be real, finite,
positive, with `0<s<1` and `Emax>=Emin`. Initial volumes are eight positive finite
values, unstressed volumes eight nonnegative finite values. Caller lists become
immutable tuples. Invalid shapes, booleans, non-real scalars and nonfinite values
are rejected. Numerical controls live in the separate `SolverSettings` class.

## Integration and reported quantities

The solver integrates fixed smooth valve regimes to terminal pressure-gap events,
using a short forward probe to choose the right-hand mode at roundoff-scale ties.
A signed epsilon sentinel prevents repeated events at identically zero gaps.
Each beat splits at activation start, peak, end of systole and beat end. Only the
portion of each dense interpolant preceding its first event is retained. Eight
integrals restart at zero per regime and accumulate through offsets; solver rtol
and atol apply unchanged to physical volumes and local integral increments.

Terminal zero-volume events and checks on accepted nodes/sampled dense output
raise explicit failures. Solver failure, uncovered samples, nonfinite state and
repeated failure to advance also raise. There is no silent repair or tolerance
change. Extremely large/ill-conditioned explicit inputs may fail numerically;
these are not guaranteed admissible physiological configurations.

`FourChamberM1Result` contains named columns for time, volumes, pressures, flows
and cumulative flows. Outputs recompute the exact algebraic flow law from the
reported pressure, rather than storing a regime-dependent approximate diode law.
`volume(name)`, `pressure(name)` and `flow(name)` expose columns.

The final-beat metrics use cumulative aortic/pulmonary-valve differences for
LV/RV forward SV (mL) and divide by beat duration for CO (mL/s and L/min).
EDV/ESV are sampled maximum/minimum volumes, with EF their fractional excursion;
they are not event-defined or a guarantee of integrated ejection fraction.
During inflow/outflow overlap or transients, the volume excursion need not equal
forward SV. Atrial pressure/volume min/max and time means are included, as are
SA/PA min/max/mean pressure. Means use sampled trapezoidal quadrature and extrema
can depend on sample density. Solver-integrated SV and the integrated trajectory
are independent of sample density, as tested at matching sample times.

`conservation()` reports total initial volume, maximum total drift and local
`max|V(t)-V(0)-B*Cumulative(t)|`, all in mL. The local residual checks wiring
and roundoff; it cannot independently establish integral accuracy. Refinement
and different-method tests address that. `periodicity()` reports per-compartment
and maximum final/prior-beat waveform differences in mL, or null for one beat.
It imposes no healthy target or automatic convergence gate: a fixed beat count
never proves steady state.

## Evidence, interpretation and unresolved conflicts

- **Verbatim evidence:** not republished or newly validated in this stage. The
  stable corpus is commit `6626e5b8c50f2c068218d6caa43b1ab8df9feb9b`, specifically
  `src/physiosim/models/cardiovascular.py::elastance` and
  `src/physiosim/simulation/_hybrid.py::_right_hand_modes,integrate`.
- **Extracted project facts:** `docs/evidence_review/anatomy_nodes_v2.json`
  JSON pointers `/nodes/2` through `/nodes/9` cover LV/RV/LA/RA cavities and the
  four valves. Vascular contexts are found by stable keys
  `systemic_arterial_lumen`, `systemic_venous_lumen`,
  `pulmonary_arterial_lumen`, `pulmonary_venous_lumen`; the generated manifest
  records their exact JSON pointers and source SHA256. The source declares
  Uberon 2026-10-01 and FMA 5.1.0 (2026-05-15). No external revalidation occurred.
- **Model interpretation:** chamber blood is `blood_contained_in` the corresponding
  cavity; vascular reservoirs have `lumped_compartment_context`, not identity with
  entire anatomical beds. Valve flows have `flow_location`. Relationship direction,
  primary IDs, both ontology IDs, source/version and provenance are explicit.
  For vessel contexts, the Uberon system/vessel ID is a related structure, not a
  lumen-equivalent mapping; the FMA lumen ID remains primary.
- **Unresolved source/model difference:** v2 `/nodes/4` and `/nodes/5` describe
  LA/RA as lumped Smith venous blood. M1 separates them by explicit design without
  asserting that legacy SV/PV volumes contain atria or editing the old identities.
  v2 also records no FMA cross-reference for UBERON:0013127; it remains a related
  pulmonary venous structure and FMA:52455 is the lumen context.
- **Physiological evidence gap:** no source here calibrates atrial elastance,
  venous-inflow resistance or atrial unstressed volumes. All are mandatory caller
  inputs. The fixture resolves software exercise needs, not that evidence gap.

The new `four_chamber_m1_manifest` validator checks the full model-specific
contract against the offline node specification. It rejects reversed topology,
wrong/mismatched IDs or valve locations, missing variables, pressure references,
properties, units or temporal contexts, and lumen identity assertions. It parses
units with pint but requires the exact exported units (no implicit conversion).
Cumulative flow is **run-integrated volume**, SV **beat-integrated volume**, CO
**beat-mean flow**, and P/V/Q **instantaneous**. Machine-readable parameter units
and state order accompany the contract. Existing registry/bindings are untouched.
In an installation without repository docs, an explicit v2 file path is required
for the loader; it never downloads missing resources.

## Synthetic fixture and execution

`synthetic_fixture()` copies legacy exploratory ventricular/vascular scalar
values without mutating them. All values are test design choices, not fitted,
literature-derived or normal physiology. New `E_la=.15`, `E_ra=.10` mmHg/mL,
`R_venous_return=.05`, `R_pulmonary_venous=.05` mmHg s/mL are explicit fixture
choices. In state order, `V0=(10,700,2500,20,10,100,400,20)` mL and
`V_initial=(140,850,3200,60,140,180,490,60)` mL. This caller declares **5120 mL**.
This is no conservative split of the legacy state and no volume is created during
integration. The engine does not prescribe any total-volume default.

From the repository with existing dependencies (no install/network required):

```sh
.venv/bin/python scripts/run_four_chamber_m1.py --output <server path>/artifacts/m1-passive-atria-v1/demo
.venv/bin/python -m pytest tests/test_four_chamber_m1_model.py tests/test_four_chamber_m1_simulation.py tests/test_four_chamber_m1_semantics.py tests/test_four_chamber_m1_demo.py -q
```

The default synthetic demonstration uses 30 beats, 400 samples/beat, DOP853,
rtol=1e-9, atol=1e-10 mL and max_step=T/200. `--cycles`, `--samples-per-cycle`
can override duration/density. `--config FILE` accepts a synthetic JSON object
with required complete `parameters` and optional `simulation` (`cycles`,
`samples_per_cycle`) and `solver` (`method`, `rtol`, `atol`, `max_step`) objects.
No patient data are supported or authorized. Omitted config solver controls use
`SolverSettings` defaults (max_step=None means T/100), recorded as effective values.

Public Python entry points:

```python
from physiosim.experiments.four_chamber_m1_demo import synthetic_fixture
from physiosim.simulation.four_chamber_m1 import SolverSettings, simulate_m1
p = synthetic_fixture()  # explicitly choose a synthetic fixture
r = simulate_m1(p, cycles=2, samples_per_cycle=80,
                settings=SolverSettings(max_step=p.period/200))
print(r.pressure('la'), r.metrics(), r.conservation(), r.periodicity())
```

The required `--output` names a private new/empty caller directory. Existing files
are never overwritten. `trajectories.csv` has time and all eight V/P/Q/cumulative
columns, at requested sample times rather than native adaptive nodes. CSV Qcum
columns correspond to the manifest's `Q_cum_*` variables. `summary.json` contains
all parameters, effective numerical settings and metrics; `manifest.json` contains
the checked semantic contract, full config, source/config/output hashes and
Python/dependency versions. Manifest output hashes omit the manifest itself.
`figure.png` and local `index.html` display the synthetic label and limitations.
There are no timestamps; byte replay is tested in the same environment, without
claiming bit identity across platforms. Files are mode 600 and output directory
mode 700, including transient plotting cache files; failures never reuse old data.

## Scope limits and verification handoff

No active atrial contraction, AV delay, inertance, closure regurgitation, FSI,
renal/drug/reflex model or clinical validation. Four ideal algebraic diodes cannot
claim dynamic valve behavior. This is no Smith/four-chamber reference reproduction.
No unconditional R->0 equivalence to the six-compartment model is claimed or used
as a gate; that singular limit requires compatible compliance and initial pressures.

TDD RED/GREEN command logs are private files in the task artifacts `tdd/` folder;
thresholds above were written before the first RED run. Tests cover literal
incidence/endpoints and deliberate mutations, parameter shapes/domains, passive
laws, a closed-valve constant-elastance matrix-exponential analytic problem,
named outputs, pulse detection, equilibrium/chatter, symmetric simultaneous
events, positivity/conservation, method/tolerance refinement, sampling/replay,
error paths, semantic negatives and demo serialization. These are software/math
checks, not physiological validation. The router runs the full legacy suite and
fresh cross-provider review separately; this implementation stage does not claim
those unrun checks passed.
