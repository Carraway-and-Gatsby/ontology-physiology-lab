# SHACL validation of the Smith 2004 annotations (2026-11-01; valve rules G10 and S5 and atrium rule S6 added the same day)

Generated from `report_ws267.json` by hand after running `run_shacl.py` (Python 3.11.15, pyshacl 0.26.0, rdflib 7.6.0; `requirements-shacl.txt`). SHA-256 of every input is in the JSON.

## What was run

| step | input | outcome |
|---|---|---|
| Dependency check | `smith2004_dependencies.ttl` against the equations in `../smith2004_variable_dictionary.json` | pass: every flow sign and every pressure-to-volume chain matches E6-E32 |
| Positive control | `fixtures/conforming.ttl`, both shape files, dependencies | pass: 0 results |
| Negative control, generic | `fixtures/generic_violations.ttl`, generic shapes | pass: exactly the 13 expected results (9 Violation, 3 Warning, 1 Info) |
| Negative control, Smith | `fixtures/smith_violations.ttl`, both shape files, dependencies | pass: exactly the 8 expected results |
| Finding | `ws267_omex_form.ttl` (workspace 267 SemSim RDF translated to OMEX v1.2 form), both shape files, dependencies | does not conform: 20 Violations, 4 Warnings, 46 Info |

The negative controls caught two defects in the first draft of the shapes, both fixed before the finding run. The Warning and Info rules reported as Violations because `sh:severity` had been placed on the SPARQL constraint rather than on the shape. A nested `sh:detail` result from G6 was also being counted as a separate result.

## Results on workspace 267

| rule | severity | variables | meaning |
|---|---|---|---|
| G1 property class | Violation | V_lvf, V_rvf, V_spt | annotated with OPB_01061 "van't Hoff law of osmosis", a dependency class, not a property; the manuscript says these "are not physical volumes" (S6P p. 10) |
| G2a fluid-volume bearer | Violation | V_pcd | borne by fma9869 Pericardium (tissue); E3 and manuscript Eq. 11 define it as V_lv + V_rv (R4) |
| G3 pressure form | Violation | P_lv, P_rv, P_ao, P_vc, P_pa, P_pu, P_peri | pressures annotated as properties of an entity, the pre-OMEX form; under the pressure-reference decision they must be energy differentials |
| S2 transmural pressure | Violation | P_lvf, P_rvf | free text only; no energy-differential annotation with a pericardial sink |
| S5 valve location | Violation | Q_mt, Q_av, Q_tc, Q_pv | the processes are not located at any valve; the valves appear only in free text ("Blood flow through aortic valve"), not as nodes (decisions.md "Anatomical structures as nodes") |
| S6 atrium in venous compartment | Violation | V_pu, V_vc | the venous compartments are annotated to the vessel lumens only, with no part in the left or right atrial cavity (decisions.md "Atria as separate nodes") |
| S3 capacitive pair | Violation | P_pa / V_pa (E19) | P_pa borne by blood in fma14167 Lumen of pulmonary trunk, V_pa by blood in fma52449 Lumen of pulmonary arterial tree: different entities |
| G0 missing bearer | Warning | P_pcd, V_0_spt, V_d_spt, V_d_pa | property given, bearer missing; the three volumes are PV-law parameters, which may be better annotated as constitutive properties |
| G9 free text only | Info | 46 variables, including all E_es, R, L, lambda, P_0, V_0 and most V_d parameters, P_th and the driver | no structured annotation |

No results for S1 (no chamber pressure has a sink), S4 (all six flow directions agree with E27-E32), G4-G6 (every process and participant is well formed), G7, G8 (every container is a label-checked FMA term) or G10 (no process has a location at all).

## The four C6 defects

| defect (evidence_review.md C6) | caught | by |
|---|---|---|
| OPB_01061 on V_lvf, V_rvf, V_spt | yes | G1 |
| P_pa and V_pa annotated to different lumens | yes | S3, using the E19 dependency |
| "Pericardial blood volume" as free text on the pressure P_peri | no | text versus structure; no shape reads free text |
| "atrial valve" free text for the aortic valve (Q_av, R_av, L_av) | no | same; the structured process for Q_av is correct and passes S4 |

## Limits

- The translation to OMEX form is mechanical (`translate_ws267.py` docstring) and keeps every defect. Running the shapes on the original vocabulary would need a second set of paths; this was not done.
- The allowed OPB property list (G1) and the checked FMA container list (G8) are project choices; both are written out with labels in `shapes_omex_v1_2.ttl`.
- P_pcd and P_th are outside S1/S2 coverage because no FMA entity was selected for the thoracic-cavity contents (S21).
- `smith2004_dependencies.ttl` is hand-written from the equations; the runner re-checks it against the dictionary, but the dictionary itself is a mechanical transcription of the CellML.
- Conformance shows that an annotation has the agreed structure. It does not show that the annotation is physiologically right, and it sees no numbers, units or solver behaviour (evidence_review.md section 5).
- S3 and S4 compare entity nodes, not containers, so that a lumped compartment (two containers) is compared as one blood portion. Two separately written nodes with identical content would therefore be reported as different; the ws267 translation and the fixtures name entity nodes by content, so this does not arise there.
