# Exploratory six-compartment cardiovascular model

**Scope:** executable closed-loop teaching/research prototype, not a clinical model,
not a patient-specific prediction, and **not a replication of Smith et al. (2004)**.
All numeric physiological defaults below are author-selected exploratory choices.
No parameter was fitted to a patient or borrowed as a verified published value.
The default run is a computational baseline, **not a healthy/normotensive reference**.

## Source review before implementation

The accessible Physiome CellML encoding was downloaded as XML data and inspected
before model implementation. Its own metadata attributes the translation to
Matlab code supplied by the original authors.[1]
The accompanying reference is Smith BW, Chase JG, Nokes RI, Shaw GM, Wake G,
*Minimal haemodynamic system model including ventricular interaction and valve
dynamics*, Medical Engineering & Physics 26 (2004), 131–139, PMID 15036180.[2]

The inspected CellML `vena_cava` and `aorta` components use a linear pressure–volume
law, `P = E_es * (V - V_d)`; its `flow` component defines the systemic and pulmonary
vascular flows by pressure difference divided by resistance.[1]
The ventricular components mix an activated end-systolic pressure with a passive
end-diastolic pressure, while additional components describe septal and pericardial
interaction.[1]
The original model includes an “open on pressure close on flow” valve law with
inertia; our simpler pressure-driven ideal diodes deliberately do **not** reproduce
that law.[2]

**Our explicit modifications/design assumptions:**

- Six compartments retained: LV, systemic arteries, systemic veins, RV,
  pulmonary arteries, pulmonary veins. Atria are not separate states.
- Linear passive ventricular pressure replaces the source's nonlinear passive
  ventricular law. Septum, pericardium, thoracic pressure and valve inertia omitted.
- A synchronous cosine pulse replaces the source's Gaussian activation.
- Four algebraic, unidirectional resistive valves replace dynamic valve states.
- Systemic/pulmonary vascular beds remain signed resistors, not diodes.
- No reflex regulation, respiratory modulation, coronary circulation, spatial
  anatomy, oxygen transport, renal/volume regulation or disease calibration.
- Internal units are **s, mL, mmHg**, rather than the source encoding's kPa.
  Since no numeric parameters were transplanted, there is no hidden pressure-unit
  conversion of source parameters.

Raw evidence is in `evidence/a_smith_2004.cellml` and
`evidence/a_smith_overview.html`; the former was parsed but **never executed**.
Source identities and verbatim evidence are in `physiology_sources.json`.
No source-model implementation was incorporated into the simulator.

**Source identity and license (reviewed 2026-10-31).** The parsed capture[1] is a
SemSim-annotated copy from PMR workspace 267 (`semantic-annotation`), not the
file behind the Smith exposure. The exposure's own source is a separate
workspace at changeset `f7b732c9`[3][4], retained as
`evidence/a_smith_2004_canonical.cellml`. A static comparison
(`evidence/a_smith_2004_compare.py`, output `a_smith_2004_compare.json`) finds
the same 14 components, 32 equations and 94 variable connections in both, but
the workspace-267 capture has **no `initial_value` attributes**: 43 parameters
and 10 state initial conditions are absent, so it is underdetermined and cannot
be simulated as captured. Any reference simulation must use the canonical file.
That file's own status note says the beat is cycled by piecewise conditions, so
only 14 beats (10.5 s at the 0.75 s period) are encoded.[3]

PMR states that all publicly accessible repository content is licensed under
CC BY 3.0 Unported.[4] Both captures are publicly accessible, so both fall under
that statement; only the canonical file also has an exposure-specific license
page.[4] Redistribution requires attribution to the CellML author (Geoffrey
Nunns, Auckland Bioengineering Institute), the original paper (PMID 15036180),
the source URL and download time, and the PMR citation (Lloyd et al.,
*Bioinformatics* 2008;24(18):2122–2123). The license covers the CellML
encodings, not the journal article's text or figures. This is technical due
diligence, not legal advice.

## Implemented equations

State order `COMPARTMENTS = (lv, sa, sv, rv, pa, pv)`.
The circulation is a directed ring:

```text
LV --aortic--> SA --systemic--> SV --tricuspid--> RV
RV --pulmonary_valve--> PA --pulmonary--> PV --mitral--> LV
```

All six state variables are **total compartment volumes**, not just stressed
volumes. `V0` is the unstressed-volume parameter; pressure uses `V - V0`.
These are implementation definitions, not a claim of source-model equivalence:

```text
T = 60 / heart_rate                     [s; HR in beats/min]
phi = (t modulo T) / T                  [dimensionless]
a(phi) = (1 - cos(2*pi*phi/s))/2         if 0 <= phi < s
       = 0                             otherwise
E_lv(t) = emin_lv + (emax_lv - emin_lv)*a(phi)
E_rv(t) = emin_rv + (emax_rv - emin_rv)*a(phi)
P_lv = E_lv(t)*(V_lv - V0_lv)
P_rv = E_rv(t)*(V_rv - V0_rv)
P_i = (V_i - V0_i)/C_i                  for i = sa, sv, pa, pv
Q_valve = max((P_upstream-P_downstream)/R_valve, 0)
Q_bed = (P_upstream-P_downstream)/R_bed
```

The pulse has value zero at the start/end of systole and peaks at `s*T/2`.
Both ventricular activations share a phase. `emax_lv` directly controls the LV
maximum elastance; this is a proxy intervention, not a calibrated drug effect.

With flows ordered `(aortic, systemic, tricuspid, pulmonary_valve, pulmonary,
mitral)`, the ODEs are:

```text
dV_lv/dt = Q_mitral - Q_aortic
dV_sa/dt = Q_aortic - Q_systemic
dV_sv/dt = Q_systemic - Q_tricuspid
dV_rv/dt = Q_tricuspid - Q_pulmonary_valve
dV_pa/dt = Q_pulmonary_valve - Q_pulmonary
dV_pv/dt = Q_pulmonary - Q_mitral
```

Each flow appears once with each sign, so the symbolic sum of all six derivatives
is exactly zero. Numerical conservation is tested separately; volumes are never
renormalized to force a passing result. No pressure or volume clipping is used.
Valves clip **flow only** according to their constitutive law.

## Complete default parameter provenance

Every entry is **exploratory, author-selected, unfitted, not clinically validated**.
The numerical values below have **no claimed literature measurement source**.
The physiological source citations support equation structure, not these values.
Machine-readable entries for every dataclass field are in
`evidence/a_parameter_provenance.json`.

| Dataclass field | Default | Unit | Design role |
|---|---:|---|---|
| `heart_rate` | 75 | beat/min | Imposed pacing, no baroreflex |
| `emin_lv` | 0.06 | mmHg/mL | Linear passive LV stiffness |
| `emax_lv` | 2.5 | mmHg/mL | Peak LV stiffness |
| `emin_rv` | 0.03 | mmHg/mL | Linear passive RV stiffness |
| `emax_rv` | 0.8 | mmHg/mL | Peak RV stiffness |
| `systolic_fraction` | 0.4 | 1 | Width of activation pulse / cycle |
| `compliance_sa` | 1.5 | mL/mmHg | Systemic arterial reservoir |
| `compliance_sv` | 100 | mL/mmHg | Systemic venous reservoir |
| `compliance_pa` | 5 | mL/mmHg | Pulmonary arterial reservoir |
| `compliance_pv` | 20 | mL/mmHg | Pulmonary venous reservoir |
| `resistance_aortic` | 0.01 | mmHg s/mL | Aortic valve |
| `resistance_systemic` | 1 | mmHg s/mL | Systemic vascular bed |
| `resistance_tricuspid` | 0.01 | mmHg s/mL | Tricuspid valve |
| `resistance_pulmonary_valve` | 0.01 | mmHg s/mL | Pulmonary valve |
| `resistance_pulmonary` | 0.1 | mmHg s/mL | Pulmonary vascular bed |
| `resistance_mitral` | 0.01 | mmHg s/mL | Mitral valve |
| `unstressed_volumes` | (10, 700, 2500, 10, 100, 400) | mL | Order lv, sa, sv, rv, pa, pv |
| `initial_volumes` | (140, 850, 3200, 140, 180, 490) | mL | Same order; sums to 5000 mL |

The initial distribution is an exploratory starting condition, not a periodic
solution. The default baseline pressures are elevated; no claim is made that this
parameter set is “normal.” Initial conditions and parameter validity checks do
not guarantee physical validity for arbitrary user-specified interventions.

## Public Python API

```python
from dataclasses import replace
from physiosim.models import Parameters, COMPARTMENTS, FLOW_NAMES
from physiosim.simulation import simulate, SimulationResult

p = Parameters()
baseline = simulate(parameters=p, cycles=40, samples_per_cycle=400,
                    rtol=1e-7, atol=1e-8, max_step=None, method="DOP853")
reduced = simulate(parameters=replace(p, emax_lv=0.5 * p.emax_lv))
print(baseline.metrics())
last = baseline.final_beat
lv_volume_ml = baseline.volumes[last, COMPARTMENTS.index("lv")]
```

`Parameters` is a frozen dataclass. Its `period` property is in seconds.
All scalar physiological parameters must be finite/positive; maximum elastance
cannot be below minimum; `0 < systolic_fraction < 1`. Each volume tuple must have
six finite entries (initial volumes positive, unstressed volumes nonnegative).

`simulate(parameters=None, cycles=40, samples_per_cycle=400, rtol=1e-7,
atol=1e-8, max_step=None, method="DOP853") -> SimulationResult` uses
`scipy.integrate.solve_ivp`. It exposes solver selection directly; `Radau` was
independently exercised in the tests. Integration failure raises `RuntimeError`.
`cycles` must be an integer >=1, and `samples_per_cycle` an integer >=4.
Tolerances must be positive finite scalars; `atol` is in mL.
Explicit `max_step` must be positive finite seconds. Its default is `T/100`.
These solver/sampling defaults are **numerical design choices**, not physiological
parameters. No solver termination criterion claims a steady state.

`SimulationResult` contains:

- `time`: shape `(cycles*samples_per_cycle+1,)`, seconds, including both endpoints.
- `volumes`, `pressures`, `flows`: shape `(N,6)`, units mL, mmHg, mL/s respectively.
- `parameters`, `samples_per_cycle`, `compartment_names`, `flow_names`.
- `final_beat`: slice of the last `samples_per_cycle+1` rows, endpoints included.
- `metrics()`: a dictionary of Python numeric values with unit-explicit keys.

`heart_rate_bpm` is the imposed pacing rate, not an estimate from peak detection.
`stroke_volume_ml` is trapezoidal integration of forward aortic flow over the
last beat; `cardiac_output_l_min` is that volume divided by beat duration,
converted to L/min. `cardiac_output_m3_s` supplies the same output in SI units
(1 mL = 1e-6 m³, 1 L = 1000 mL, 1 min = 60 s; unit definitions).
`lv_edv_ml`/`lv_esv_ml` are sampled LV extrema, not independently detected valve
event values, and `lv_ejection_fraction = (EDV-ESV)/EDV` is dimensionless.
Thus the flow-based SV and sampled `EDV-ESV` can differ slightly.

Pressure keys are `systemic_systolic_pressure_mmhg`,
`systemic_diastolic_pressure_mmhg`, `systemic_mean_pressure_mmhg`,
`pulmonary_mean_pressure_mmhg`, `pulmonary_venous_mean_pressure_mmhg`.
Means are time-weighted integrals, not unweighted sample averages.
`volume_drift_ml` is the maximum absolute change in total volume across **all**
samples. `final_beat_max_volume_difference_ml` compares all six last-beat volume
waveforms with the prior beat at matched phases; it is NaN for a one-beat run.
Consumers writing strict JSON must handle this NaN rather than calling it zero.
Sampling resolution affects extrema/quadrature independently of ODE tolerances.

## Executed numerical evidence

Run `python docs/evidence/a_verify_core.py` in the project environment to regenerate
`evidence/a_core_results.json`; exact results and library versions are recorded
there. A 40-cycle, 400-sample/beat default run produced:

| Computed quantity | Baseline | Half LV peak elastance |
|---|---:|---:|
| HR (beats/min) | 75 | 75 |
| Forward SV (mL) | 102.6564 | 89.3244 |
| CO (L/min) | 7.69923 | 6.69933 |
| LV EDV (mL) | 177.734 | 214.082 |
| LV ESV (mL) | 75.1345 | 124.705 |
| LV EF (fraction) | 0.57726 | 0.41749 |
| Systemic systolic/diastolic pressure (mmHg) | 163.009 / 104.702 | 142.829 / 91.424 |
| Systemic mean pressure (mmHg) | 133.498 | 116.434 |
| Pulmonary arterial mean pressure (mmHg) | 23.7631 | 24.1710 |
| Pulmonary venous mean pressure (mmHg) | 10.9381 | 12.9989 |
| Maximum total-volume drift (mL) | 2.01e-11 or less | 1.37e-11 or less |
| Last vs prior beat max volume difference (mL) | 0.00666 | 0.03982 |

These are simulated outcomes, not external observations. Reduced LV contractility
here causes lower output and higher pulmonary venous pressure; the intervention
is a new run from the same initial volumes, not a mid-run switch or a clinical
heart-failure diagnosis. The baseline meets the deliberately modest test target
of less than 0.1 mL last-versus-prior-beat volume difference; this is not a proof
of asymptotic stability for all parameter sets.

Tightening to `rtol=1e-9`, `atol=1e-10`, `max_step=T/200` gives baseline CO
7.69931 L/min and beat difference 0.000222 mL or less. Maximum volume difference
between the full default and tight trajectories was **0.3153 mL**, including the
transient; it must not be described as machine-precision trajectory agreement.
The four-cycle DOP853-versus-Radau test, with tighter tolerances, requires each
volume sample to agree within 0.002 mL absolute tolerance (plus pytest's default
relative allowance) and SV within relative tolerance 1e-4.

## Tests and development evidence

`tests/test_cardiovascular.py` contains constitutive-law, four-diode, six-state
mass-balance, conservation, final-beat, metric-quadrature, invalid-input,
contractility-response, cross-solver and public-import checks.
Eight incremental red→green feature slices were run; logs are stored as
`evidence/a_tdd_01_red.txt` through `a_tdd_08_green.txt`.
Later response and solver comparisons are acceptance/regression tests against
already implemented behavior, not evidence of clinical validation.
The implemented feature suite last returned **25 passed**.

## Limitations and next validation work

No reference trajectory was reproduced, no original model code was executed,
and no patient or experimental data was used. The pressure baseline is elevated;
parameter tuning to a prespecified physiological dataset would be separate work,
not a reason to relabel the present simulation as validated. Valve switching is
nonsmooth, so tolerances and output sampling need convergence checks. Neither
sampling nor default solver settings guarantee accurate valve-opening times.
The fixed linear pressure law admits unphysical negative pressures for some
parameter/initial-state combinations; these are not hidden by clipping. Users
must inspect positivity, conservation, beat convergence and intervention ranges.

## Sources

[1] https://models.physiomeproject.org/workspace/267/rawfile/6ae217019bf59fc1e22e2dc5235751c6fcf6be24/Smith_2004.cellml — Smith 2004 CellML encoding
[2] https://models.physiomeproject.org/exposure/9d046663ba5cac5c8a61ac146183614b/view — Physiome Smith 2004 overview
[3] https://models.physiomeproject.org/workspace/smith_chase_nokes_shaw_wake_2004/rawfile/f7b732c9707abdba5a55d471c49baf7dee92b036/smith_chase_nokes_shaw_wake_2004.cellml — Smith 2004 canonical CellML encoding
[4] https://models.physiomeproject.org/exposure/9d046663ba5cac5c8a61ac146183614b/smith_chase_nokes_shaw_wake_2004.cellml/license_citation — PMR license and citation page

## Solver-integrated cumulative flows (opt-in)

With `simulate(..., cumulative_flows=True)`, the solver augments the six volume
states with six directed-edge states

\[
C_k(t)=\int_0^t Q_k(t')\,dt', \qquad \dot C_k=Q_k,
\]

where flow is in mL/s and cumulative flow is in mL. Edge `i` is the outflow of
compartment `i`, and edge `i-1` (modulo six) is its inflow. The scalar absolute
tolerance, in mL, applies to all 12 states. The default remains the original
six-state integration and returns no cumulative-flow array.

At `rtol=1e-9`, `atol=1e-10`, and `max_step=T/200`, a four-cycle augmented run
differed from the six-state volume trajectory by at most 2.28515e-5 mL. In a
20-cycle run, the maximum independent incidence-matrix balance residual was
9.77707e-12 mL; swapping two incidence columns produced 189.025 mL. This small
correctly wired residual is **not** evidence that the cumulative-flow quadrature
is accurate: Runge-Kutta (and linear multistep) methods preserve the linear
invariant `V_i - V_i(0) - (C_in - C_out)`. Here dV/dt and dC/dt are built from
the same evaluated flow vector and DOP853 dense output is linear in the stage
values, so the invariant also holds at interpolated `t_eval` samples, up to a
roundoff floor of order eps*|C|. The residual was ~1e-11 mL at rtol 1e-3, 1e-7
and 1e-9 alike (independent review R1), confirming that it checks
incidence/sign wiring and roundoff only. Cumulative-flow accuracy must be
demonstrated separately by tolerance refinement.

For a 40-cycle baseline, cumulative aortic stroke volume was 102.599935089 mL
at those tight settings and 102.599933804 mL at `rtol=1e-11`, `atol=1e-12`, and
`max_step=T/400`, an absolute difference of 1.28573e-6 mL. Tight-setting sampled
trapezoidal values were 102.657489315 mL at 400 samples/beat and 102.598919777 mL
at 1600 samples/beat; their absolute differences from the integrated value were
0.0575542 mL (0.0560958%) and 0.00101531 mL (0.000989583%), respectively. The
six final-beat edge throughputs spanned 1.14729e-5 mL, within the 2.39901e-5 mL
bound derived from the observed compartment-wise final-beat volume changes;
this follows from the same linear invariant and is a consistency check, not
independent accuracy evidence.

Known limitations of the augmented mode (measured; reviewer R1 numbers
re-executed by the integrator, 40-cycle baseline, fine reference rtol 1e-11,
atol 1e-12, T/400):

- Dense-output undershoot. Values at accepted solver steps are non-decreasing
  for valve edges, but DOP853 interpolation at `t_eval` samples near the
  ideal-diode `max(., 0)` kink can make sampled valve cumulative flows
  decrease: minimum per-sample increment -4.93e-3 mL at the API defaults
  (rtol 1e-7, atol 1e-8, T/100), -3.82e-6 mL at rtol 1e-9/atol 1e-10/T/200,
  and 0 at the fine settings. Monotonicity is therefore only tested at the
  fine settings.
- Accuracy is not uniform. Final-beat SV error versus the fine reference is
  -2.75e-4 mL at the API defaults and 1.29e-6 mL at the tight settings, but
  whole-run `|C - C_fine|` is larger (9.04e-3 and 1.73e-3 mL respectively).
  Per-beat SV accuracy must not be assumed for run-long cumulative
  throughput.
- Looser volume control. At matched tight settings the augmented run's volume
  error versus the fine reference was 2.34e-5 mL (plain six-state: 6.2e-6 mL)
  after 4 cycles and 1.69e-3 mL (plain: 1.02e-3 mL) after 40 cycles. The likely
  mechanism (reasoned, not isolated experimentally) is that the large
  cumulative states dilute scipy's RMS error norm, allowing longer steps.
  Use the six-state default for volume trajectories and the augmented mode
  for throughput, or tighten tolerances.

## Strict multi-beat periodicity report

`physiosim.validation.periodicity_report(volumes, samples_per_cycle, beats=3,
tolerance_ml=1e-4)` compares each of the last `beats` beats with its
predecessor at identical phase samples (both beat endpoints included) and
returns per-beat residuals in mL, oldest first. The residual for the last beat
equals `metrics()['final_beat_max_volume_difference_ml']` exactly. With fewer
than `beats + 1` complete beats it returns `available=False` and never passes.
Passing is a numerical settling check, not biological validation, and not
proof of a unique limit cycle. It is not yet wired into the runner's exit
status; the declared 0.1 mL last/prior-beat milestone gate is unchanged.

Measured on the three canonical scenarios (60 cycles, 400 samples/beat,
DOP853), three successive beats, 1e-4 mL:

| Scenario | six-state, rtol 1e-9/atol 1e-10/T/200 | augmented (cumulative_flows), same | augmented, rtol 1e-11/atol 1e-12/T/400 |
|---|---|---|---|
| baseline | 2.33e-4, 7.37e-5, 2.29e-5 — FAIL | 1.40e-5, 2.40e-5, 1.08e-5 — pass | 3.3e-7, 1.5e-7, 1.3e-7 — pass |
| reduced contractility | 9.42e-6, 7.39e-6, 9.57e-6 — pass | 1.83e-5, 2.09e-5, 2.42e-5 — pass | 7.2e-8, 1.4e-7, 1.5e-7 — pass |
| partial restoration | 2.22e-5, 1.94e-5, 9.26e-6 — pass | 4.29e-4, 8.89e-4, 4.86e-4 — FAIL | 3.8e-7, 1.8e-7, 6.1e-7 — pass |

The six-state baseline values reproduce those previously reported by the
independent reviewer. At the canonical tolerances the strict verdict changes
when only the error-control state set changes, and residuals are not
monotone, so residuals of 1e-5 to 1e-3 mL there are dominated by integration
error rather than physiological settling. At the fine settings all three
scenarios pass with residuals <= 6.1e-7 mL. Strict-periodicity claims should
use the fine settings (or a demonstrated refinement sequence), not the
canonical tolerances.
