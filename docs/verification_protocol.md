# Independent verification protocol

## Status, provenance and claim boundary

**Prospective protocol, not a test report.** No implementation or tests are modified by this assignment, and no third-party simulation was run. All thresholds below are proposed engineering acceptance criteria selected for this small research prototype, not thresholds extracted from clinical studies or evidence that tests have passed. Freeze them before inspecting final experimental outcomes; explain and version any later change rather than silently relaxing a failing gate.

The scientific basis is the published 0D hydraulic-circuit/time-varying-elastance modeling tradition.[25]
CellML's normative unit and variable-equivalence rules inform the interface checks, while SemGen's annotation protocol and published composition limitations inform semantic negative controls.[16][17][18]
The equations and mathematical checks below are independently derived for the **proposed** six-state topology; they are not asserted to reproduce a particular published parameterization or the eight-state CardioLab implementation.[12]

Verification asks whether code solves its declared equations. Biological validation asks whether those equations and parameters predict appropriate observations. This protocol supports the former and a limited mechanistic plausibility experiment only. It does not establish diagnostic accuracy, patient-specific prediction, clinical normal ranges, medical-device fitness, or external biological validation.

## 1. Freeze the mathematical contract

Use the state order `LV, SA, SV, RV, PA, PV`, where SA/SV and PA/PV mean lumped systemic and pulmonary arterial/venous volumes. Atria are omitted; **PV is not a measured left-atrial pressure and SV is not a modeled right atrium**. Any proxy interpretation must be explicit and qualified.

Define exactly six directed edge orientations:

| Edge | Upstream → downstream | Law |
|---|---|---|
| Aortic valve `q_av` | LV → SA | `max(P_LV-P_SA,0)/R_av` |
| Systemic bed `q_sys` | SA → SV | `(P_SA-P_SV)/R_sys` |
| Tricuspid surrogate `q_tv` | SV → RV | `max(P_SV-P_RV,0)/R_tv` |
| Pulmonary valve `q_pv` | RV → PA | `max(P_RV-P_PA,0)/R_pv` |
| Pulmonary bed `q_pul` | PA → PV | `(P_PA-P_PV)/R_pul` |
| Mitral surrogate `q_mv` | PV → LV | `max(P_PV-P_LV,0)/R_mv` |

The resistive beds remain signed; forcing every vascular edge nonnegative silently changes the model. Ideal competent valves are nonnegative and must have zero flow under a nonpositive forward pressure difference. Diode valves omit inertia, closing-volume flow, regurgitation and pressure-wave propagation.

```text
dV_LV/dt = q_mv  - q_av
dV_SA/dt = q_av  - q_sys
dV_SV/dt = q_sys - q_tv
dV_RV/dt = q_tv  - q_pv
dV_PA/dt = q_pv  - q_pul
dV_PV/dt = q_pul - q_mv
```

For a minimal linear-elastance implementation use `P_v(t)=E_v(t)*(V_v-V0_v)+P_ext_v` for each ventricle, and `P_i=(V_i-V0_i)/C_i+P_ext_i` for each vessel. All pressure differences must use a consistent reference; set external pressures explicitly, even if all are zero. If a nonlinear passive relation is implemented instead, declare it separately and re-derive pressure-domain tests; do not test the wrong constitutive law.

Use `E(t)=Emin+(Emax-Emin)*a(t)` with a fully specified periodic activation `a`, `0<=a<=1`, `T=60/HR`, and `Emax>=Emin>0`. Document onset, peak, relaxation, left/right phase relationship and cycle-boundary behavior. Reduced LV contractility changes **LV Emax only**, within its valid range, leaving RV parameters, minimum LV elastance, volume inventory, resistances, compliances and heart rate unchanged. Scaling the whole elastance curve changes diastolic properties as well and is a different intervention.

### Dimensions and transformations

| Quantity | Working units | Required dimensional relation |
|---|---|---|
| Time / heart rate | s / beats per minute | `T=60/HR` seconds |
| Volume / pressure | mL / mmHg | Declare pressure reference |
| Flow | mL/s | volume/time |
| Resistance | mmHg·s/mL | pressure/flow |
| Compliance | mL/mmHg | volume/pressure |
| Elastance | mmHg/mL | pressure/volume |
| EF | dimensionless fraction | `SV/EDV`; convert to percent only for display |
| Cardiac output | L/min | `(integral(q_av dt)/T)*60/1000` |

A mathematical unit checker must distinguish dimensions from scaling: mL and L are dimensionally compatible but not numerically identical; rate conversion also requires the time scale. CellML explicitly requires unit-reduction compatibility and accounting for multiplying factors on mapped variables.[16] Do not accept a unit conversion merely because both strings contain “pressure.”

## 2. Independent checks and preliminary acceptance gates

These gates are meant to be exercised after implementation by a reviewer who does not reuse the implementation's derivative or metrics routines as the sole oracle.

### V1 — algebraic topology and conservation

Construct an independent incidence matrix `B` with one `-1` and one `+1` per edge. Check every column sums to zero, there are exactly the declared endpoints, and the graph is the intended closed loop. Derive `dV=Bq`; therefore `1^T dV=0` and total blood volume is constant. This identity holds regardless of the elastance waveform and is stronger than checking a plausible numerical sum.

At representative states and deterministic seeded random states within the declared domain, independently compute pressures/flows and all six derivative entries. Require scaled derivative-sum residual `abs(sum(dV))/max(1,sum(abs(q))) <= 1e-12`. Require agreement of each derivative with its separately constructed inflow-minus-outflow, not just the sum. For trajectories require relative total-volume drift `max_t(abs(sum(V(t))-sum(V(0))))/sum(V(0)) <= 1e-9`, reporting absolute drift in mL too. No volume clipping, renormalization or hidden inventory correction is allowed to make this check pass.

Mutation cases to require later: reverse a single sign, omit an edge contribution, double-count one flow, swap systemic and pulmonary endpoints, and inject an external source. Some wrong topologies still conserve total volume; anatomical edge checks must catch those separately.

### V2 — constitutive identities, finite domain and valve direction

Test elastance extrema, periodicity (`E(t+T)=E(t)`), phase-boundary continuity as applicable, and nonnegative finite activation. At fixed volume, pressure must follow the declared equation and its derivative with respect to volume must equal the declared local elastance or inverse compliance. Constant offsets `V0` are physical parameters, not clipping thresholds: `V<V0` produces negative stressed volume, which is not the same as negative total volume. Decide whether such states are outside the model's interpretation domain; never hide them by clipping pressure.

Test every valve at positive, zero and negative gradient, including tiny gradients around the switch. Require no reverse competent-valve flow and nonnegative instantaneous dissipated power `q*deltaP`. For a signed vascular resistor require `q*deltaP=(deltaP)^2/R>=0`. Check finite values and positive total compartment volumes at accepted steps and any accessible Runge–Kutta stages. Reject nonfinite inputs, negative/zero R or C, invalid E bounds, nonpositive HR, invalid timing and invalid solver settings explicitly. A positive parameter is not automatically a numerically safe setting.

### V3 — analytically solvable subproblems

1. **Zero-gradient passive state:** with constant elastance and all connected pressures equal, the derivative must be zero and volumes remain constant.
2. **Two passive reservoirs:** isolate two compliances C1/C2 connected by resistance R, with constant V0 and external pressures. Independently derive `deltaP(t)=deltaP(0)*exp[-t*(1/C1+1/C2)/R]`; conserve `V1+V2`. Compare to this exact solution over several time constants. This checks signs, time units and integration independently of cardiac waveforms.
3. **Fixed-volume driven chamber:** if both incident flows are zero, volume must stay fixed while `P(t)=E(t)*(V-V0)+P_ext` varies. Reject any method that mistakes changing pressure for a volume source.
4. **Unit covariance:** scale volumes and V0 consistently from mL to L, with corresponding E/R/C changes; after conversion back, physical trajectories must agree within numerical tolerance. This is a separate test from checking unit labels.

For the smooth reservoir test, use the exact error and demonstrate decreasing errors under step halving. A fourth-order scheme should approach its expected order in a smooth, resolved regime; this is not a blanket demand for fourth-order behavior at valve switches.

### V4 — temporal convergence, phase and periodicity

Use at least three step sizes `h, h/2, h/4`; a starting proposal is 2, 1 and 0.5 ms, with each actual step adjusted to divide the cardiac period exactly. Report requested and actual steps. Resolve the fastest time scales; 0.5 ms is not assumed sufficient for every resistance/compliance choice. Store native-step data for checks, not only downsampled plots.

For each baseline and impaired case, run to a periodic criterion, not simply a fixed beat count. Proposed gate: maximum absolute six-volume difference at matching phase on consecutive beats <= `1e-4 mL` for three successive beats, plus finite-state and conservation checks. Report beat count, terminal residual, tolerance and maximum allowed beats. Failure to reach this criterion is an explicit nonconvergence result, never a valid equilibrated output. Compare complete final-beat waveforms on a common phase grid as an additional diagnostic.

Require the two finest runs to agree within 0.5% for forward CO, EDV, ESV, EF, MAP, mean PV pressure and peak LV pressure, using `abs(a-b)/max(abs(b), floor)` with floors of 1 mL for volumes, 1 mmHg for pressures, 0.1 L/min for output, and 0.01 for fractional EF. Report absolute errors too. Require maximum phase-aligned pressure/volume waveform error <=1% with explicitly declared scales; refine again if either criterion fails or errors do not trend down. Examine valve opening/closing times for grid artifacts.

Separate sources of error: (a) fixed-duration runs from identical initial states isolate time discretization; (b) separately equilibrated runs estimate steady-cycle outputs. Do not let different convergence cutoffs or phase shifts masquerade as integration error. Ideal diode laws are continuous but kinked; a naive RK4 error ratio of exactly sixteen is not required at switching events.

### V5 — local and cycle-integrated balance; independent metrics

Independently integrate native-step flows and check each compartment's `V_end-V_start = integral(Qin-Qout)`. Trapezoidal postprocessing and RK stages need not have identical quadrature error, so demonstrate residual reduction under refinement rather than demanding machine precision for this integrated identity. At periodic steady state all six **net cycle-integrated edge flows** must agree within the periodic and quadrature error budget; the LV and RV outputs cannot be persistently different in this closed loop.

Recompute EDV/ESV, SV, EF, forward stroke volume, CO, mean pressure and peak pressure from saved arrays using a separate reader. State whether EDV/ESV are extrema or event-defined. A volume-extremum SV equals integrated ejection only when inflow/outflow do not overlap and the chamber is periodic; test this condition. If simultaneous inlet/outlet forward flow occurs, report it and withhold the usual SV/EF throughput interpretation. The inspected CardioLab documentation makes a comparable distinction.[12]

Do not test conservation of total mechanical energy as if the heart were passive. For this specific linear model, at zero constant external pressure, an optional independently derived power check is

`U=sum_v[0.5*E_v(t)*(V_v-V0_v)^2]+sum_i[(V_i-V0_i)^2/(2*C_i)]`

`dU/dt=0.5*sum_v[E_v'(t)*(V_v-V0_v)^2]-sum_edges[q*deltaP]`.

This separates active prescribed-elastance work from resistive dissipation. It must be re-derived if there are nonlinear chambers, time-varying V0/compliance, external-pressure work or other energy-storage terms.

### V6 — repeatability and failure honesty

Record code and configuration hashes, parameter units/provenance, state order, solver/version, step settings, initialization, convergence settings, output schema and deterministic seed. Run each canonical configuration twice and compare numerical arrays and metrics, excluding timestamps from strict equality. Cross-platform tolerance is distinct from same-environment deterministic replay. Ensure changing sampling/plot density does not change integrated metrics.

Return a nonzero exit status or structured explicit failure for invalid configurations/nonconvergence. Never emit fabricated replacement waveforms, silently change parameters, or reuse a previous run under a new label. Preserve every failed scenario in the report denominator. A plot is not an execution log.

## 3. Reduced-contractility mechanistic experiment

Pre-register baseline and a specified lower `Emax_LV`, with everything else frozen. Publish both exact configurations. Use both independent-equilibrium comparisons and, if supported, a separately labeled abrupt perturbation from the baseline equilibrium. Do not describe independent equilibria as a treatment-response time series.

Within the chosen valid regime, the mechanistic hypothesis is reduced forward output and reduced EF, typically with increased ESV. Test signs and effect sizes against refinement uncertainty, and report rather than tune away an unexpected sign. A local sweep across several Emax values can reveal regime changes; do not claim universal monotonicity from one pair. Repeat nearby initial distributions with identical total volume to probe basin dependence. Any difference between semantic-assisted and manual **equivalent** configurations must be no larger than numerical repeatability error.

Do **not** require pulmonary venous pressure to increase by a preset clinical amount or label a curve “pulmonary edema.” Burkhoff and Tyberg's theoretical analysis showed that substantial filling-pressure rises depended importantly on venous capacity and compensatory mechanisms, not simply the isolated LV strength reduction.[26] The proposed model lacks those mechanisms. No EF cutoff or “HFrEF diagnosis” is justified solely by this experiment.

## 4. Semantic manual-versus-assisted experiment

### Aim and conditions

Question: for a fixed, independently specified connection task, does the semantic layer detect mistakes beyond dimensional checking **without altering the valid numerical model**?

Use three conditions if feasible:

- **Manual/unassisted:** participant or explicitly labeled scripted configuration selects bindings from the same catalog.
- **Units-only validator:** adds dimension and scale checks, but no anatomical/quantity-role rules.
- **Semantic-assisted:** adds property identity, entity/context, port direction, topology and allowed-parameter rules; suggestions require acceptance and ambiguous cases abstain.

Keep numerical core, task information, initial catalog and final independent acceptance tests identical. Freeze a gold-standard answer key independently of the assistant's matching function. Include multiple valid tasks and more than one invalid family, and report the full denominators. If there are no actual human participants, call it a **synthetic fault-injection benchmark**, not a user study; do not report a scripted baseline's wall time as manual human effort.

### Required negative and positive controls

| Fixture | Expected outcome |
|---|---|
| Valid LV Emax replacement with identical units, context and declared range | Accept; only intended parameter changes |
| LV vs RV elastance, same dimensions | Reject anatomical mismatch |
| Elastance vs compliance | Reject incompatible dimensions |
| Pressure vs volume | Reject physical-property mismatch |
| Flow in mL/s vs L/min | Accept only through an explicit, tested conversion |
| Flow orientation reversed | Reject or require an explicit sign transformation with endpoint audit |
| Absolute vs transmural pressure | Reject absent explicit reference transformation |
| Mean pressure vs instantaneous pressure | Reject temporal-semantics mismatch |
| Pulmonary venous reservoir vs left atrium | Do not assert identity merely from a proxy label |
| Edge substitution that conserves mass but connects the wrong circulation | Reject topology/anatomy mismatch |
| Emax below Emin, or NaN/inf | Reject parameter-domain mismatch |
| Missing/ambiguous property, entity, units or multiple candidate targets | Abstain with a visible reason; never choose a plausible-looking default |
| Duplicate identifier or annotation binding inconsistent with actual numerical field | Reject before integration |
| Unchanged/baseline configuration through assistant | Numerical equivalence with direct invocation |

The SemGen annotation protocol warns that auto-assigned physical properties are not guaranteed correct and requires user confirmation.[17] Its composition paper describes directionality, granularity, missing-term and post-merge assumption issues.[18] These are motivations for these controls, not evidence that a local matcher solves every case.

### Measurement and analysis

Report per-fixture: task ID, family, independently assigned truth, manual/units/semantic decision, accepted configuration diff, rejection/abstention reason, and solver result if valid. Define false acceptance of an unsafe binding as the primary safety endpoint; also report true rejection, false rejection of valid tasks, correct acceptance and abstention separately. Calculate precision/recall only with stated denominators and an explicit policy for abstentions. Do not count repeated identical runs as independent samples.

For a genuine user study, separately pre-register recruitment/expertise, training, task difficulty, randomized or counterbalanced condition order, task assignment, scoring and time measurement. Record total time to a correct configuration, final error count, correction/rework and failures/timeouts, not just successful completion times. Include annotation-authoring and maintenance costs, setup/training, review and adjudication; reusable annotations are not cost-free. Analyze paired outcomes and uncertainty with participant/task clustering; a small convenience pilot supports only pilot conclusions.

Use holdout task families and multiple model contexts for any generalization claim. To distinguish semantic benefit from hardcoded domain knowledge or richer validation generally, report a units-only ablation and which semantic rule detects each error. Do not conflate reduced search space, fewer candidate clicks or a seeded-error detection rate with measured human productivity.

### Ontology and interoperability claim limits

A JSON/JSON-LD registry of local concepts, type checks and relations is a semantic schema; it is not automatically a formally reasoned ontology, a SemSim-compliant model, CellML serialization, an OPB mapping, or interoperability with SemGen. External ontology IDs must resolve to inspected definitions with version/provenance. If no real mappings or reasoner were used, say so. Identical property labels do not guarantee equations, assumptions, species, granularity, initial state or boundary conditions are compatible. The published SemGen experience expressly retains substantial expert judgment after merging.[18]

## 5. Independent implementation review handoff

After core and semantics are frozen, the independent reviewer should inspect actual source and run the approved local implementation. Deliver an evidence matrix with columns `criterion`, `command/case`, `observed value`, `threshold`, `pass/fail/untested`, and `artifact path`. Separate source inspection, executed mathematics, mechanistic expectations, semantic benchmark evidence and unresolved biological validation. Include unexpected outcomes and failed cases; count tested configurations programmatically.

Minimum artifacts: hashed canonical configs; native-step trajectories; convergence/refinement table; independent metrics comparison; local/global balance residuals; complete semantic confusion/abstention table; repeatability comparison; error-path evidence; and a limitations statement. No acceptance criterion is marked passed merely because a development test shares the same faulty helper or because an upstream project reports similar tests.

No such implementation evidence is claimed in this initial research assignment. External data calibration, uncertainty/identifiability analysis, expert review and any clinical validation remain future work.

## Sources

[12] https://raw.githubusercontent.com/Carraway-and-Gatsby/cardiac-simulator/main/docs/physiology-model.md — CardioLab model equations and scientific scope
[16] https://www.cellml.org/cellml/2.0 — CellML 2.0 normative specification
[17] https://raw.githubusercontent.com/wiki/SemBioProcess/SemGen/Annotation-protocol.md — SemGen annotation protocol
[18] https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0145621 — Neal et al. 2015 semantic cardiomyocyte composition
[25] https://pmc.ncbi.nlm.nih.gov/articles/PMC3103466 — Shi et al. 2011 review of 0D and 1D blood flow models
[26] https://pubmed.ncbi.nlm.nih.gov/8238596 — Burkhoff and Tyberg 1993 theoretical LV dysfunction analysis
