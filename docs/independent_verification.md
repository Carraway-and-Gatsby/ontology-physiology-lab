# Independent implementation verification — observed results

## Post-review owner remediation

The original review below and `docs/evidence/c_verify_results.json` are preserved as a historical snapshot. After handoff, the owner reproduced the paired-empty-metadata bug with a failing regression test and added required-field/flow-orientation checks. The independently authored generator was then re-executed against the final installed wheel via `scripts/verify_independent.py`, writing fresh evidence to `results/independent/c_verify_results.json` without replacing the original snapshot. Both missing-reference and missing-anatomy probes now reject. Numerical refinement and the reported stricter-periodicity/quadrature limitations reproduce unchanged. Changed equations and free-text source context remain outside the equivalence check.

The final installed-wheel full suite returned **64 passed, 5 RDFLib warnings** (`results/tests.xml`). The separate 12-fixture manual/units-only/semantic benchmark is now implemented in `results/phase1/semantic_benchmark.json`, including an actual incorrectly labeled numerical payload that remains falsely accepted. This completes that bounded synthetic comparison, not the full prospective semantic composition protocol or a human study.

## Outcome and scope

**Bounded numerical milestone: PASS. Entire prospective protocol: NOT COMPLETE.**
This report verifies the current project equations and a small fixed set of exploratory configurations. It is not biological validation, a normal-reference calibration, a heart-failure diagnosis, or a replication of the source publication.

The independent suite returned **12 passed**. The complete repository suite returned **63 passed, 5 warnings** (RDFLib deprecations). Before new tests were added, the existing suite independently returned 46 passed. Concurrent parent work added tests during this review; these totals describe different snapshots, not inconsistent denominators. No production files were modified by this reviewer.

Reproduce from the repository root:

```sh
.venv/bin/python docs/evidence/c_verify_run.py
.venv/bin/python -m pytest tests/test_independent_verification.py -q
.venv/bin/python -m pytest tests -q
```

Evidence:

- [`c_verify_results.json`](evidence/c_verify_results.json): exact parameters, configuration SHA-256 hashes, source hashes, solver/version metadata, every numerical comparison, and eight semantic probes.
- [`c_verify_run.py`](evidence/c_verify_run.py): independent equation/metric reader and evidence generator.
- `evidence/c_verify_{baseline,reduced}_{default,tight,fine}.npz`: **six** configurations, each with complete sampled trajectories, native accepted-step trajectories, independent native pressures/flows, and per-beat residuals.
- [`c_verify_execution.txt`](evidence/c_verify_execution.txt), [`c_verify_independent_pytest.txt`](evidence/c_verify_independent_pytest.txt), [`c_verify_pytest.txt`](evidence/c_verify_pytest.txt): actual execution logs.
- `tests/test_independent_verification.py`: mathematical, mutation-control, unit, equilibrium, trajectory and semantic checks.

Environment recorded in JSON: Python 3.11.15, NumPy 2.4.6, SciPy 1.17.1, Pint 0.25.3, macOS arm64. Same-environment determinism is tested; cross-platform bitwise identity is not claimed. Source hashes matched the inspected model, simulation, ontology, generator and independent test files at completion.

## Frozen experiment and independent oracles

The six state order is `(lv, sa, sv, rv, pa, pv)`; directed edges are `(lv,sa), (sa,sv), (sv,rv), (rv,pa), (pa,pv), (pv,lv)`. The reviewer constructs an explicit signed incidence matrix, not `np.roll`, and independently computes pressure, valve flow and vascular-resistor flow. The alternative activation formula is `sin(pi*phase/systolic_fraction)**2`. Eighty seeded random states exercise pressure/flow/derivative agreement. A deliberately wrong circulation still conserves inventory but fails the endpoint-specific oracle. Additional sign/scaling/source mutations are rejected.

Baseline uses the unchanged exploratory `Parameters()` values. Reduced contractility changes **only** `emax_lv` from 2.5 to 1.25 mmHg/mL. Both start from the same 5000 mL distribution and run **60 cycles, 48 s**, not an abrupt intervention and not a solver that terminates on equilibrium. DOP853 is used with:

| Label | rtol | atol (mL) | maximum step (s) | sampled points/beat |
|---|---:|---:|---:|---:|
| default | 1e-7 | 1e-8 | 0.008 = T/100 | 400 |
| tight (parent CLI settings) | 1e-9 | 1e-10 | 0.004 = T/200 | 400 |
| fine | 1e-11 | 1e-12 | 0.002 = T/400 | 400 |

This is **coupled step-cap/tolerance refinement**, not an isolated order-of-accuracy estimate for cardiac valve switching. Adaptive native steps can be much smaller: the finest baseline run ranged from 1.72e-6 to 0.002 s over 29,307 accepted steps. The exact ranges and counts for all runs are saved. A separate smooth analytical reservoir test isolates step refinement.

The native-step solver calls the actual production RHS while monitoring all RHS-evaluated stage states for finite values and positive volumes. Its dense samples are checked by a fresh public `simulate()` invocation for both tight scenarios: **volumes, pressures and flows are exactly equal**, establishing same-environment deterministic replay and correspondence to the public API.

Independent metrics are read back from saved NPZ arrays, using an explicit trapezoidal sum rather than `SimulationResult.metrics()`. The largest discrepancy with production metrics was **8.88e-16**. That is an implementation agreement check, not proof of negligible sampling quadrature error.

## Acceptance matrix

| Criterion / executed case | Observed | Gate | Status / artifact |
|---|---|---|---|
| V1 independent topology, pressure, flows, RHS; 80 seeded states | Correct entries and scaled derivative-sum residual | 1e-12 conservation residual; close componentwise agreement | PASS; independent pytest |
| Topology negative controls | Conserving wrong endpoints and sign/scaling/source faults detected | Reject mutated oracle outputs | PASS; independent pytest |
| Whole-trajectory inventory; six runs | Maximum relative drift 6.73e-15; native absolute drift <=3.37e-11 mL | Relative drift <=1e-9 | PASS; JSON + NPZ |
| Evaluated RK stage domain; six runs | All finite; minimum volume >=46.91 mL | Finite and positive total volumes | PASS for tested runs, not arbitrary parameters |
| Valve gradients/dissipation | Each edge at -100, -1e-9, 0, 1e-9, 100 mmHg agrees with declared law | Diodes nonnegative; resistor `Q*deltaP=deltaP^2/R` | PASS; independent pytest |
| Pint dimensions | Pressure, flow, resistance, compliance, elastance, power and rate conversion checked; wrong dimensions rejected | Dimensional compatibility and actual multiplier | PASS; independent pytest |
| Actual unit covariance | RHS error 3.64e-12 mL/s; trajectory error 8.65e-8 mL; pressure error 3.47e-8 mmHg | 1e-8 mL/s; 2e-5 mL/mmHg | PASS; JSON `unit_covariance` |
| Constant passive equal-pressure state | Remains fixed over three cycles | Volume change <=1e-9 mL | PASS; independent pytest |
| Exact passive two-reservoir solution | Errors decrease 6.14e-5 → 7.25e-6 → 9.04e-7 mL | Monotonic decrease; finest <1e-5 mL | PASS; JSON `passive_reservoir_refinement` |
| Repeated tight trajectories; both scenarios | Exactly equal V/P/Q arrays | Exact same-environment equality | PASS; JSON `repeatability` |
| Internal baseline regression | CO ~7.6993, MAP ~133.50, ESV ~75.135 | 0.2% around rounded internal anchors | PASS; not a biological range |
| Tight/fine scalar metrics; both scenarios | Largest relative error 1.06e-7 | <=0.005 (0.5%) | PASS; JSON `comparisons` |
| Tight/fine final-beat waveforms | Largest scaled pressure/volume error 1.21e-7 | <=0.01 (1%) | PASS; JSON `comparisons` |
| Fixed 60-beat milestone periodicity; all six runs | Last residual <0.00219 mL | <0.1 mL | PASS; not stringent steady state |
| Strict final-three-beat periodicity | Baseline default/tight fail; reduced default fails; others pass | Every last-three residual <=1e-4 mL | MIXED; table below |
| Cycle-integrated local balance | ~0.05–0.06 mL residual at 400 samples/beat | Refinement evidence, not machine precision | PARTIAL; sampling-limited, see below |
| Complete prospective semantic benchmark | Eight targeted probes only | Full prespecified fixtures and comparison conditions | NOT COMPLETE |
| External biological validation | No patient/reference dataset | Independent observations/calibration | NOT PERFORMED |

The 0.1 mL milestone gate is explicitly different from the prospective 1e-4 mL gate. The 0.2% regression allowance protects the declared implementation against accidental changes and comfortably exceeds measured tight/fine numerical error; it has no physiological authority.

### Unit covariance and analytical subproblem details

Pint supplies both multipliers: mL → L = 0.001 and mmHg → Pa = 133.322387415. Initial/unstressed volumes, both elastance extrema, every compliance and resistance, and the solver's absolute tolerance are transformed consistently. The **actual production pressure/RHS/trajectory routines** are then run in the transformed numeric representation and converted back. Time stays in seconds. This tests equation covariance, not a claim that the public API or its hardcoded metric labels support alternate units. Pressure and volume outputs are both checked.

A useful failed negative control is preserved in `c_verify_negative_control_failure.txt`: scaling volume and V0 but leaving all hydraulic parameters unchanged can cancel in this homogeneous volume ODE. It therefore did **not** detect the intended error. The corrected negative control omits only resistance conversion, producing an RHS discrepancy >2.46e9 mL/s. This is why dimensional labels and a volume-only covariance check are insufficient.

For the smooth reservoir test, make both ventricular elastances constant and place LV/RV/PA/PV at the systemic pair's eventual common pressure. SA starts above it and SV below it, keeping their incident valves closed during relaxation. The full production six-state model then has the exact systemic gradient

`deltaP(t) = deltaP(0) * exp[-t*(1/C_sa + 1/C_sv)/R_systemic]`.

RK23 with fixed loose tolerances and maximum steps 0.2, 0.1, 0.05 s gives the decreasing errors above. The other four compartments change by <=2.14e-14 mL. This exercises a genuine analytical limit of the implemented six-state model, not an unrelated toy solver.

## Observed final-beat values

Tight settings, 60 beats, **400 samples/beat**:

| Quantity | Baseline | Reduced LV Emax |
|---|---:|---:|
| Forward aortic SV (mL) | 102.657512 | 89.324647 |
| CO (L/min) | 7.699313 | 6.699349 |
| Sampled LV EDV (mL) | 177.734852 | 214.082329 |
| Sampled LV ESV (mL) | 75.134911 | 124.704929 |
| EF from volume extrema | 0.577264 | 0.417491 |
| Systemic systolic/diastolic pressure (mmHg) | 163.0098 / 104.7027 | 142.8290 / 91.4241 |
| Systemic mean pressure (mmHg) | 133.499192 | 116.433598 |
| Mean pulmonary venous pressure (mmHg) | 10.938102 | 12.998776 |
| Peak LV pressure (mmHg) | 165.483105 | 145.355114 |

The reduced-contractility signs are much larger than discretization uncertainty: lower CO/EF, higher ESV and pulmonary venous pressure. These observations are restricted to this pair, this initial inventory and this model. The baseline systemic pressure is elevated; it must not be relabeled healthy. PV is a lumped reservoir, **not an explicitly modeled left atrium or a measured filling pressure**.

## Refinement, periodicity and the 0.3153 mL discrepancy

| Comparison | Maximum full-trajectory volume error (mL) | Maximum last-beat volume error (mL) | Maximum last-beat pressure error (mmHg) |
|---|---:|---:|---:|
| Baseline default vs tight | 0.315254 | 0.00138404 | 0.000575767 |
| Baseline tight vs fine | 0.00102928 | 0.0000174082 | 0.00000719191 |
| Reduced default vs tight | 0.0397007 | 0.000224454 | 0.0000962476 |
| Reduced tight vs fine | 0.000915791 | 0.00000804577 | 0.00000241807 |

The baseline discrepancy peaks in **SA at t=28.856 s**; it is not confined to the very first beat. It falls strongly with refinement and does not materially change the final scalar conclusion, but it rules out machine-precision agreement of default trajectories. Baseline tight/fine full-history disagreement still reaches 0.00103 mL. Waveform gates use each compartment's maximum absolute fine final-beat magnitude with a floor of 1 mL or 1 mmHg; the exact scaled values are in JSON. Scalar relative-error floors are 1 mL, 1 mmHg, 0.1 L/min and 0.01 fractional EF.

| Scenario/settings | Beat 58 residual (mL) | Beat 59 | Beat 60 | Final three <=1e-4? |
|---|---:|---:|---:|---|
| Baseline/default | 0.00555381 | 0.00278466 | 0.00218081 | No |
| Baseline/tight | 0.000233051 | 0.0000737344 | 0.0000229051 | **No** |
| Baseline/fine | 8.78645e-7 | 3.54829e-7 | 2.30878e-7 | Yes |
| Reduced/default | 0.00222671 | 0.00190571 | 0.00197731 | No |
| Reduced/tight | 9.42363e-6 | 7.38725e-6 | 9.56887e-6 | Yes |
| Reduced/fine | 1.73052e-7 | 1.51037e-7 | 1.97689e-7 | Yes |

The tight baseline earlier achieves three consecutive small residuals ending at beat 35, but later violates the strict threshold again. An earlier passing window is **not** persistent proof of numerical steady state. All runs pass the parent's 0.1 mL milestone gate. For stronger numerical claims, `rtol=1e-11, atol=1e-12, max_step=T/400` resolves these final residuals in both scenarios. This review did not implement automatic periodicity-based termination or prove stability.

### Postprocessing accuracy is separate from ODE accuracy

At tight settings, resampling the **same dense numerical solution** changes forward SV:

| Samples/beat | Baseline SV (mL) | Reduced SV (mL) |
|---|---:|---:|
| 400 | 102.657512 | 89.324647 |
| 800 | 102.585148 | 89.368582 |
| 1600 | 102.598942 | 89.377265 |

The 400-to-1600 differences are approximately **0.0571% and 0.0589%**, respectively: below the 0.5% milestone scalar gate, but much larger than tight/fine ODE metric differences. Baseline quadrature is not monotone under doubling because valve timing interacts with the sampling grid. Do not report all displayed SV/CO digits as accurate. At 400 samples/beat, flow SV minus sampled volume excursion is +0.05757 mL baseline and -0.05275 mL reduced. No simultaneous LV inlet/outlet flow occurs at final-beat sample points; event-exact absence was not established.

Native accepted-step trapezoidal integration also does **not** reproduce the high-order solver's stage quadrature. Whole-48-s maximum local balance errors decrease as follows:

| Settings | Baseline native trapezoidal balance error (mL) | Reduced (mL) |
|---|---:|---:|
| default | 79.8885 | 54.8115 |
| tight | 24.8613 | 17.1302 |
| fine | 6.76093 | 4.47323 |

These large accumulated **postprocessing residuals** must not be hidden or confused with the <=3.37e-11 mL global inventory drift of the ODE states. The native nodes alone are inadequate for precise cumulative flow quadrature. Final-beat 400-sample local residuals remain about 0.0586/0.0528 mL despite tighter ODE tolerances. For high-accuracy balance/throughput claims, use independently refined dense quadrature or integrated-flow auxiliary states and verify convergence. This reviewer leaves that production change to the owner.

## Semantic inspection and unresolved risks

The eight executed probes are saved individually:

| Probe | Actual decision | Interpretation |
|---|---|---|
| Wrong ventricular anatomy | Reject | Desired |
| Wrong pressure reference | Reject | Desired |
| Wrong temporal context | Reject | Desired |
| Wrong pressure dimensions | Reject | Desired |
| Both references missing (`''`) | **Accept** | Completeness gap |
| Both anatomy IRIs missing (`''`) | **Accept** | Completeness gap |
| Equation changed to `P = V*C`, metadata otherwise same | **Accept** | No equation-equivalence analysis |
| Incompatible source-context text only | **Accept** | Source context is not enforced |

The two missing-metadata cases would fail the prospective fail-closed/abstention requirement. This is a **critical claim limitation** if the checker is presented as a general safe composition validator. For the curated built-in registry these probes do not demonstrate an incorrect physiological trajectory, but arbitrary caller annotations are not fully validated. Equation strings and compatible annotation labels cannot establish compatible numerical equations. This is an equality-based connection checker, not a complete anatomy/topology/registry reasoner.

At the final inspected snapshot the parent corrected `SV` to `integral(Q_aortic, complete_beat)` with dependency `Q_aortic`, matching the simulation's flow-based SV. EF remains separately based on volume extrema. The original EDV−ESV annotation would have been a real semantic mismatch. Pressure references use fixed external zero; gauge and transmural interpretations coincide only under that assumption. Atria are omitted; the reservoir labels correctly remain local rather than falsely declaring atrial identity. RDF graph labels and project assertions are not OWL-derived physiological truths, and this review did not re-resolve external ontology definitions.

## Remaining protocol work and development honesty

Not completed: full semantic confusion/abstention benchmark with manual/units-only ablations; exhaustive registry completeness and parameter-binding checks; human usability study; event-resolved valve timing; independent fixed-volume driven-chamber case; strict automatic periodicity termination; nearby-initial-condition/basin study; multi-level contractility sweep; cross-platform reproducibility; formal energy/power balance; patient/reference-data validation or uncertainty/identifiability analysis. Existing suite error-path tests were rerun, but they do not exhaust all arbitrary malformed numerical inputs.

A transient full-suite failure from exact floating-point CO equality is preserved in `c_verify_full_suite_initial.txt`; the reviewer did not edit that parent-owned code/test. The final complete run passes. `c_verify_red.txt` and `c_verify_reservoir_red.txt` preserve expected missing-oracle failures before the new evidence helpers were implemented. This is independent verification of pre-existing production code, not a claim that the reviewer retroactively developed that production code test-first.
