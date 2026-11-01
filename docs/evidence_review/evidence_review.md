# Evidence review for the Smith 2004 semantic layer (2026-11-01)

Status: evidence review only. No OWL was generated, no model, experiment or UI code was changed, and no mapping below is adopted. Candidates are proposals with the evidence location beside them; where the retained sources do not settle a point it is marked `UNKNOWN`. Abstract-only sources (Smith 2004, Rosse and Mejino 2003, the two OMEX specification records) were not used to fix any relation direction or mapping.

Companion files in this folder:

- `evidence_cards.md`: one card per source (identifiers, exact quotations with location, claim versus interpretation versus independent confirmation, licence, limits).
- `smith2004_variable_dictionary.{json,md}`: all 76 variables and 32 equations of the canonical CellML with units, role, SemSim annotation, reference point, direction and unit plausibility.
- `d_sources.json`: retrieval ledger (URLs, method, licence, SHA-256) for the new `docs/evidence/d_*` files.

Source identifiers used below: S1 Gennari 2011, S2 Cook 2013 (OPB dependencies), S3 Harmonizing 2019, S4 Rosse and Mejino 2003 (abstract), S5 SemGen 2019, S6 Smith 2004 (author manuscript, S6P), S7 SHACL, S8 PROV-O, S9 SemSim-annotated Smith CellML (PMR workspace 267), S10 OPB releases, S11 FMA releases, S12 Wiley passages (Colunga 2020, Jones 2021), S13 Neal 2014, S14 Neal 2015, S15/S16 OMEX metadata specifications (abstracts), S17 Paeme 2011, S18 Revie 2013, S19 Pironet 2013. Project files: `physiology.md`, `ontology.md`, `src/physiosim/ontology/__init__.py` (the registry), `orchestration_state.md` (Hermes OpenCOR runs).

## 1. What was obtained

| Source | Access achieved | Retained as |
|---|---|---|
| S1 Gennari 2011 | full text (PMC author manuscript, all rights reserved) | quotations only |
| S2 Cook 2013 | full text, CC BY 2.0 | `d_fulltext_PMC3904761_cook2013_opb.xml` |
| S3 Harmonizing 2019 | full text, CC BY (Europe PMC) | `d_fulltext_PMC6433895_neal2019_harmonizing.xml` |
| S4 Rosse and Mejino 2003 | abstract | card only |
| S5 SemGen 2019 | PMC page (all rights reserved); supplement not open | quotations only |
| S6 Smith 2004 | author manuscript (LaTeX, 36 pp., created 2003-08-27) read in full; published version paywalled and not seen | not retained (copyright); quotations, page numbers and SHA-256 in card S6P |
| S7 SHACL, S8 PROV-O | W3C Recommendations read | quotations |
| S9 SemSim-annotated Smith CellML | already retained (`a_smith_2004.cellml`), now fully parsed | `d_semsim_ws267_annotations_by_variable.json`, `d_ols_fma_terms_ws267.json` |
| S10 OPB | GitHub master OWL + bundled v1.07; BioPortal blocked (403/401) | `d_opb_master_excerpt_and_version_diff.json` |
| S11 FMA | OWL header, OLS record, UW release page; licence document not retrieved | `d_fma_*`, `d_ols_fma_ontology.json` |
| S12 Wiley passages | 20 passages / 13 articles via the Wiley connector | quotations only |
| S13 Neal 2014, S14 Neal 2015 | full text, CC BY | `d_fulltext_PMC4183381…`, `d_fulltext_PMC4696653…` |
| S15/S16 OMEX metadata v1.0, v1.2 | abstract only in Europe PMC XML; publisher page refused (HTTP 405) | short XML records |
| S17 Paeme 2011, S18 Revie 2013, S19 Pironet 2013 | full text, CC BY | `d_fulltext_PMC3271239…`, `…PMC3621159…`, `…PMC3610305…` |

Connector failures worth knowing: the PubMed connector's `search_articles` returned an API error for every query (full-text and metadata calls worked); Europe PMC `fullTextXML` returned HTTP 500 for the two non-open-access PMC items (S1, S5), as the user also saw; BioPortal requires an API key; Smith's 2004 University of Canterbury thesis (cited by S19 as the source of the total blood volume) was not located by web search.

## 2. The four questions and what the sources say

### Q1. Same unit, different meaning, compartment or reference point

Evidence that the distinction is needed and how the literature makes it:

- The composite-annotation grammar: exactly one physical property, at least one physical entity, the first entity being the bearer, further entities linked by RO relations (S1 quote 4). Granularity, role players and input/output arrangement are named as three separate axes of mismatch (S14 quote 1).
- The SemSim annotation of this very model (S9) distinguishes P_lv, P_rv, P_ao, P_vc, P_pa, P_pu only by the entity chain: `Portion of blood` (fma9670) `part_of` cavity of left ventricle (fma9466) / cavity of right ventricle (fma9291) / lumen of aorta (fma12239) / set of lumens of vena cava trunks (fma280059) / lumen of pulmonary trunk (fma14167) / lumen of pulmonary venous tree organ (fma52455). The property is the same (OPB_00509) and the unit is the same.
- Reference point is not part of the entity-chain grammar and is not represented in S9; the OMEX/SemSim energy-differential form (S16 item 9, S21) can carry it as a sink. The equations show what has to be carried: P_lv and P_rv include P_peri = P_pcd + P_th (E5, E8, E14); P_pa and P_pu include P_th (E19, E21); P_ao and P_vc do not (E23, E25); P_lvf and P_rvf are free-wall pressures that exclude P_peri (S18 (A.4) text). Under the energy-differential convention (S16 item 9, S21) the six chamber pressures share one unspecified sink, the model's common ground, while P_lvf and P_rvf are transmural with the pericardial contents as sink. What differs among the chamber pressures is which external pressures enter each pressure law: none for P_ao and P_vc (E23, E25), P_th for P_pa and P_pu (E19, E21), P_peri = P_pcd + P_th for P_lv and P_rv (E5, E8, E14). That is dependency information, treated under Q2, not a difference of reference point.
- Temporal meaning: all 32 equations are instantaneous; the project's `CO` and `SV` are complete-beat quantities (`ontology.md`). No source in this set annotates temporal aggregation; S14 Table 2 lists "Temporal solution domain" only as the shared time variable.
- Compartments that are functional rather than structural: Pironet notes the atria are merged into the pulmonary vein compartment (S19 quote 2); Neal 2015 says many model entities are "defined by their physiological function rather than their structural characteristics" (S14 quote 17). This is the situation of the project's local `sa`, `sv`, `pa`, `pv` concepts, which `ontology.md` already keeps local.

Candidate concepts (proposals, each with its evidence):

| candidate | evidence | status |
|---|---|---|
| Pressure variables are annotated as properties of an energy differential with source and sink (S16 item 9); chamber pressures have an unspecified sink (common ground), free-wall pressures have the pericardial contents as sink (S21) | OMEX metadata v1.2 §2.3.7.3; SemGen protocol step 5; equations E5, E8, E14, E19, E21, E23, E25 for the external-pressure terms | adopted as a documentation decision (decisions.md); the registry `reference` string is unchanged; whether the common ground is atmospheric is UNKNOWN; the entity for pericardial contents is not selected; the external-pressure terms are recorded under Q2, not as reference values |
| Bearer entity = `Portion of blood` part_of a cavity/lumen, not the organ | S9 table; S1 quote 4; S4 abstract (material versus non-material entities) | candidate; conflicts with the project registry's use of fma7101 "Left ventricle" and fma7098 for P_lv/V_lv (conflict C5) |
| Flow direction encoded as process source/sink participants | S9 (all six Q_*); S5 protocol step 5 ("anonymous … defined by their generating sources and sinks"); S14 quote 6 | candidate; the project encodes the same information as an `orientation` pair; both are explicit, the SemSim form names the entities |
| Constitutive parameters (E_es, lambda, P_0, R, L, V_d, V_0) annotated with an OPB constitutive property only, no entity | S14 quote 4; SemGen protocol step 6; S9 (all such variables have free text only) | candidate; OPB_00160 Fluid flow resistance and OPB_00076 Fluid volumetric elastance are confirmed present and unchanged in OPB master (S10); OPB_00104 Fluid inertance is a candidate for L_* |
| V_spt is "the blood volume displaced by the septum", a difference term, not a fluid volume of an organ part | S18 (A.11)-(A.14) text; E6, E12, E18 | candidate meaning; OPB property UNKNOWN (S9 labels it with a dependency class, see C6) |
| Valve flows are processes located at their valve: `bqbiol:occursIn` the valve node (Q_mt mitral, Q_av aortic, Q_tc tricuspid, Q_pv pulmonary) | BioModels.net qualifiers 1.1 occursIn (S22); manuscript Figure 1 valve elements R.mt, R.av/L.av, R.tc, R.pv/L.pv (S6P); E29-E32 | adopted as a documentation decision (decisions.md "Anatomical structures as nodes"); SHACL rules G10 and S5; registry unchanged |

**Superseded for identifiers and compartment meaning by `anatomy_nodes_v2.md` (2026-11-01); the table below is kept as the v1 record.** Anatomical structures referenced by the Smith model and their node status (decisions.md "Anatomical structures as nodes"). FMA identifiers are label-checked in OLS FMA 5.1.0 (`docs/evidence/d_ols_fma_heart_structures.json`, `d_ols_fma_terms_ws267.json`). "ws267" is the SemSim annotation in PMR workspace 267; "shapes" is the OMEX-form data and fixtures under `shacl/`; "registry" is `src/physiosim/ontology/__init__.py`.

| structure | FMA | role in the Smith model | ws267 | shapes | registry |
|---|---|---|---|---|---|
| Cavity of left ventricle | fma9466 | container of LV blood (P_lv, V_lv) | node | node | no: Left ventricle fma7101 (C5 pending) |
| Cavity of right ventricle | fma9291 | container of RV blood | node | node | no: Right ventricle fma7098 |
| Lumen of aorta | fma12239 | aortic blood (P_ao, V_ao) | node | node | no: local `sa` |
| Set of lumens of vena cava trunks | fma280059 | vena cava blood | node | node | no: local `sv` |
| Lumen of pulmonary trunk | fma14167 | P_pa in ws267 | node | node | no: local `pa` |
| Lumen of pulmonary arterial tree | fma52449 | V_pa in ws267 (split from P_pa, rule S3) | node | node | no |
| Lumen of pulmonary venous tree organ | fma52455 | pulmonary venous blood | node | node | no: local `pv` |
| Mitral valve | fma7235 | location of Q_mt (E29) | text only | node (occursIn) | no |
| Aortic valve | fma7236 | location of Q_av (E30) | text only ("atrial valve" in free text) | node (occursIn) | no |
| Tricuspid valve | fma7234 | location of Q_tc (E31) | text only | node (occursIn) | no |
| Pulmonary valve | fma7246 | location of Q_pv (E32) | text only | node (occursIn) | no |
| Wall of left ventricle | fma9556 | LV free wall (P_lvf, V_lvf) | node (with the OPB_01061 defect) | no | no |
| Wall of right ventricle | fma9533 | RV free wall | node (same defect) | no | no |
| Interventricular septum | fma7133 | septum free wall (V_spt, E18) | no: ws267 uses Cardiac septum fma7180, which also covers the interatrial septum | no | no |
| Pericardium | fma9869 | wall across which P_pcd acts (E4) | node (as V_pcd bearer, defective) | no | no |
| Pericardial cavity | fma11350 | space of P_peri; sink of P_lvf, P_rvf | no | node | no |
| Portion of pericardial fluid | fma9887 | contents of the pericardial space | node (P_peri) | node | no |
| Thoracic cavity | fma7565 | space of P_th; sink of P_pcd | no | no (no fluid entity selected; S21) | no |
| Left atrium / Cavity of left atrium | fma7097 / fma9465 | part of the pulmonary venous compartment's blood (S19; Figure 1 node "P.la"; interpretation, see decisions.md) | no | node: blood in fma9465 is a bqbiol:hasPart part of the compartment blood (rule S6) | no |
| Right atrium / Cavity of right atrium | fma7096 / fma11359 | part of the vena cava compartment's blood (Figure 1 node "P.ra"; interpretation, see decisions.md) | no | node: blood in fma11359 is a bqbiol:hasPart part of the compartment blood (rule S6) | no |
| Valve of inferior vena cava; Valve of coronary sinus; Valve of foramen ovale | fma9240; fma9242; fma75348 | not modelled | no | no | no; whether omitted structures get nodes is not decided |

### Q2. "Represents the same thing" versus "depends on through an equation"

The sources draw this line explicitly:

- Gennari 2011: the composite annotation "is for model variables, and is not sufficient for annotating the model equations" and roles in equations are a separate concern (S1 quotes 10, 11).
- Cook 2013 adds OPB *dependency* classes with role-bound *players* for exactly this purpose (S2 quotes 2, 4), and says instance-level role binding was still future work (S2 quote 8).
- Neal 2014: input/output status is computational, equivalence is semantic, and resolving an equivalence rewrites who depends on whom (S13 quotes 1, 5, 6). Neal 2015 gives the concrete case: choosing one model's calcium concentration implicitly chose its buffering formulation "because the equation that solves for calcium concentration uses" it (S14 quote 18).
- SemGen's merger lists overlaps (equivalence) and then "makes the appropriate computational links" (dependency) as a second step (S14 quote 3; S5 quotes 4-5).

Candidate relation set for the Smith model (proposal; equation ids from the dictionary):

| relation kind | candidate vocabulary | Smith equations it would describe | evidence |
|---|---|---|---|
| identity of meaning (variable ↔ composite annotation) | `isComputationalComponentFor` / `hasPhysicalDefinition` / `physicalPropertyOf` (SemSim, as used in S9); OMEX form not verified (S15/S16 abstract-only) | each variable once | S1 quote 4, S9 |
| capacitive dependency (pressure from volume) | OPB_01543 Fluid capacitive dependency: "the volume of a fluid depends the differential of fluid pressures across its boundary" | E10, E16, E19, E21, E23, E25 (linear); E4, E11, E17 (exponential EDPVR) | S2 quote 3; S10 definitions |
| resistive flow dependency | OPB_01572 Resistive flow dependency | E27, E28 | S2 quote 3; S10 |
| inductive dependency (valve inertance) | OPB_01541 Fluid inductive dependency; property OPB_00104 Fluid inertance | E29-E32 (the non-zero branch) | S2 quote 6; S10 |
| boundary / temporal integrative dependency (volume from flows) | OPB_01173 Temporal integrative dependency | E9, E15, E20, E22, E24, E26 | S2 quote 5; S10 |
| additive / difference dependencies | OPB_01194 Additive dependency, OPB_01195 Difference dependency | E3, E5, E6, E8, E12, E14 | S10 (no `rdfs:comment` on these two classes: definition UNKNOWN) |
| weighted activation (E7, E13), driver E1-E2, septum balance E18, piecewise valve switching | no OPB class identified in the retained excerpt | — | `UNKNOWN`; Cook 2013 says non-proportional dependencies are "beyond the scope of the OPB" (S2 quote 7) |

The project's registry stores `depends_on` as a tuple of names and `equation` as a string on the variable itself. That conflates the two layers the sources separate. Recording this is the finding; changing the registry is out of scope for this review.

### Q3. Which connections to allow and which to reject

Rules stated by the sources:

- Allowed: links at points of biophysical overlap, with one surviving implementation chosen by a person (S14 quote 3; S13 quote 4). Deliberately linking through one variable only is legitimate (S14, Tran substitution).
- Must reject: two formulations of the same property both feeding a variable of interest, "a logical inconsistency in the model that must be avoided" (S14 quote 8); a merged model that is "biologically overdetermined" (S13 quote 4).
- Tolerated: redundant content that is "a computational dead end" (S14 quote 9); harm is judged on the dependency graph, not on the annotation.
- Not decidable by annotation alone: range-of-validity violations (S13 quotes 2-3); custom (local) entities (S14 quote 5); synonymous terms from different ontologies (S13 quote 8); reversed source/sink conventions (S14 quote 15).

Concrete cases for the Smith model, with the evidence that decides each. "Reject" means reject as *direct equivalence*; a component equation may still relate the two.

| # | proposed connection | decision | evidence |
|---|---|---|---|
| R1 | Smith `P_lv` ≡ Smith `P_lvf` (both kPa-labelled pressures of the left ventricle) | reject | E8: P_lv = P_lvf + P_peri; S18 (A.4) "free wall pressures" exclude septum and pericardium |
| R2 | Smith `P_ao` ≡ Smith `P_pa` as "the same kind of arterial pressure" for a shared reference | reject | E19 includes P_th, E23 does not; different reference class |
| R3 | Smith `V_spt` ≡ a fluid volume of the cardiac septum | reject | S6P p. 10: the free wall volumes "are not physical volumes, but are deﬁned to capture the deﬂection of the cardiac free walls"; S18: displaced blood volume; E6, E12 difference terms; S9 annotation to OPB_01061 is itself defective (C6) |
| R4 | Smith `V_pcd` ≡ fluid volume of the pericardium (fma9869) as annotated in S9 | reject as stated | E3 and S6P Eq. (11): V_pcd = V_lv + V_rv, which "excludes the volume of the atria and the myocardium" (S6P p. 11); the bearer is not the pericardium |
| R5 | Smith `Q_av` (instantaneous) ≡ project `CO` (complete-beat mean) | reject | temporal context differs (`ontology.md`); no source annotates aggregation |
| R6 | Smith `Q_av` ≡ project `Q_aortic` | candidate allow; C1 decided, no conversion | same property (OPB_00299), same direction (S9 source blood in LV cavity → sink blood in aortic lumen; project orientation lv→sa); C5's chosen blood-in-cavity/lumen participants make the intended granularity explicit, but named aortic lumen versus local aggregate sa still requires a human-asserted source/sink mapping with provenance, not automatic entity identity (S14 quote 5; `ontology.md`, Explicit local concepts); pressure reference is not applicable to a flow |
| R7 | Smith `P_lv` ≡ project `P_lv` | candidate allow; C1 decided, no conversion | same property (OPB_00509); both are chamber pressures with an unspecified sink, so the reference is the common ground in each model, and equating them assumes the two grounds coincide, which must be stated with provenance; bearer: S9 blood in cavity of LV (the chosen C5 form) versus registry fma7101 (implementation pending); the pressure laws differ in their external terms (E8: P_lv = P_lvf + P_peri; project: external pressure zero, `src/physiosim/ontology/__init__.py`:89-90), which is a dependency difference under Q2 and a post-merge assumption to reconcile (S14 quotes 12-13), not a reference mismatch |
| R8 | Smith `P_ao` ≡ project `P_sa` | candidate allow; C1 decided, no conversion | Smith P_ao has no external-pressure term (E23); read-only project equation `P = (V - V0)/C` has no external term (`src/physiosim/ontology/__init__.py`:89; `physiology.md`:94); bearers still differ (S9 lumen of aorta versus local aggregate "systemic arteries"), requiring a human-asserted mapping with provenance (`ontology.md`, Explicit local concepts); C5 creates no automatic entity identity; P_vc's pending C3 status (an external-pressure term, not a reference point) does not bear on P_ao |
| R9 | project `HR` → OPB_01212 Event frequency in current OPB | blocked | identifier absent from OPB master (C4); only valid against the pinned v1.07 file |
| R10 | Smith `R_sys` ≡ project `R_systemic` | candidate allow | both OPB_00160, both aorta/systemic-arterial → vena-cava/systemic-venous paths; path endpoints differ in granularity (as R6) |
| R11 | Smith `E_es_lvf` ≡ project `E_lv` | reject as equivalence | E_es_lvf is the end-systolic slope of the free wall (S17 quote 2); project E_lv is a time-varying elastance E(t); Smith's time variation is in e(t) (E7), so the project's E_lv corresponds to a *product* term, a dependency, not a variable |
| R12 | Smith `V_lv` ≡ project `V_lv` | candidate allow; registry implementation pending | same property (OPB_00154), both ODE states integrating valve flows (E9 versus project `dV/dt = Q_in - Q_out`); C5's chosen blood-in-LV-cavity form aligns the intended bearer with S9, resolving the design choice, but current registry still uses fma7101 (`src/physiosim/ontology/__init__.py`:37,86); this remains a candidate mapping with S9/project provenance, not an implemented registry change; V_lv (mL) has no pressure-reference slot |
| R13 | any Smith pressure ≡ any project pressure *with a numeric unit conversion kPa→mmHg* | reject the conversion; compare without a factor | decided 2026-11-01 (decisions.md, user): the CellML numerals are read as mmHg-based, so applying the declared kPa→mmHg factor of 7.5 would corrupt the comparison; comparisons use the values as they stand and cite the decision |

### Q4. Which errors are semantic information and which need numeric or provenance checks

The sources separate three things: semantic annotation (meaning), provenance/curatorial metadata (origin), and numeric behaviour (S3 quote 1; S14 quotes 10-13). Applied to what this project has actually encountered:

| observed problem | class | why | what would check it |
|---|---|---|---|
| CellML declares kPa for values that behave as mmHg (C1) | provenance + numeric | S17 tabulates the identical numerals in mmHg; S6 abstract reports mmHg; the semantic layer cannot know which label is right | decided 2026-11-01 from the 2004 manuscript (S6P), Paeme (S17) and simulated magnitudes (decisions.md); a check against the published Figure 7 waveform remains open; PROV-O `wasDerivedFrom`/`wasQuotedFrom` from paper to CellML would record the source of each value |
| negative Q_av held constant over each closed-valve span (runs A-C; C11) | numeric | S17 quote 6 and S6: the original solver changed the state set by phase; a fixed-state ODE run of E29-E32 is a different numerical procedure | solver study; not an annotation matter |
| SemSim annotates V_lvf, V_rvf, V_spt with OPB_01061 (a dependency class) | semantic QC | S3 recommendation (vi) names exactly this check; S7 `sh:class` or `sh:in` on the property slot would flag it | SHACL shape on allowed property classes |
| SemSim free text "Pericardial blood volume" on a pressure; "atrial valve" for the aortic valve | semantic QC (text versus structured annotation) | S3 quote 9 | human review; a text/annotation consistency check cannot be automated from these sources |
| P_pa and V_pa annotated to different lumens (S9) | semantic QC | the capacitive dependency E19 relates them, so one bearer is expected | shape: variables linked by a capacitive dependency share a bearer |
| `identifiers.org/opb/...` → 403; `bhi.washington.edu/OPB#...` → 404 | provenance / infrastructure | S3 recommends identifiers.org for resolvability; resolution currently fails without credentials | record resolution status and date with each identifier; pin the OWL file hash |
| OPB_01212 absent from OPB master; 67 labels changed | provenance / version | S13 quote 9 (term obsolescence); S8 `wasRevisionOf`, `specializationOf` | pin `owl:versionIRI` (OPB master has none) or the file hash; re-verify labels per release |
| project benchmark: correct metadata on the wrong numeric column | provenance | S3 quote 1 and S14 quote 12: semantics does not see numbers | PROV-O chain from CSV column to variable to run; numeric replay |
| different compartment granularity (named lumen versus lumped "systemic arteries") | semantic, but not decidable automatically | S14 quotes 5, 16, 17 | human assertion with recorded rationale |

## 3. Unresolved conflicts

- **C1 Units of the CellML.** Declared kPa, kPa/mL, kPa·s/mL, kPa·s²/mL. The 2004 author manuscript (S6P) uses mmHg, ml and s throughout (26 occurrences of "mmHg", none of "kPa"), including the inertance unit "L = 10^-6 mmHg s^2/ml" (p. 17), but it tabulates no parameter values. The CellML numerals appear with mmHg-based units in Paeme 2011 Tables 1-3, and the six CellML initial volumes sum exactly to the manuscript's "total stressed blood volume of 1500 milli-litres" (p. 17). Status: the kPa labels are not supported by the source paper; reading the numerals as mmHg-based rests on Paeme and on simulated magnitudes, not on a parameter table from the paper. Decided 2026-11-01 (decisions.md, user): the numerals are read as mmHg-based and no conversion factor is applied, which lifts R13. The remaining uncertainty, that the authors state no individual numeral's unit, is recorded with the decision.
- **C2 V_tot.** CellML 5.5 "mL" ("Total blood volume in the body"); Paeme 5.5 l. The manuscript simulates "a total stressed blood volume of 1500 milli-litres" (S6P p. 17), which equals the sum of the six CellML initial volumes (1500.0 mL; every chamber V_d is 0). V_tot is used by no equation and is not the quantity the paper simulates; its label fits 5.5 l mislabelled as mL. Resolved as an annotation defect with no simulation effect.
- **C3 Thoracic pressure outside the heart.** The manuscript applies P_th only through the pericardial pressure, P_peri = P_pcd + P_th (S6P Eq. 14), says the peripheral chambers use the linear law of Eq. (1) "requiring only E es and V d" (p. 13), and Figure 1 marks no thoracic boundary. The CellML adds +P_th to P_pa and P_pu (E19, E21) but not to P_ao or P_vc; Revie 2013 (A.3) adds it to P_pa, P_pu and P_vc. Neither variant is in the manuscript. The source of the peripheral P_th terms is UNKNOWN (possibly the Matlab code the CellML was translated from). This concerns external-pressure terms, not reference points.
- **C4 OPB identifier and URI stability.** OPB_01212 Event frequency (project `HR`) is absent from OPB master (22 identifiers removed, 67 relabelled between v1.07 and master); neither OPB URI form dereferences without credentials; the OPB repository states no licence. The project's six other OPB identifiers are unchanged.
- **C5 Bearer granularity.** Project P_lv/V_lv anatomy is fma7101 "Left ventricle" (an organ part); the SemSim reference annotation uses `Portion of blood part_of Cavity of left ventricle` (fma9466). Both labels verify in FMA 5.1.0. They are not the same entity; the project decided to adopt the blood-in-cavity/lumen form over organ-only anatomy (S9; Q1). This is a project resolution of a design choice, not a new scientific finding or physical equivalence between compartments. Registry fma7101/fma7098 remains the actual implementation until a future change; implementation is pending.
- **C6 Reference annotation defects.** OPB_01061 on three volumes; "Pericardial blood volume" text on P_peri; "atrial valve" text on Q_av/R_av/L_av; P_pa/V_pa split across two lumens. The SemSim file is evidence of practice, not an authority; its errors must not be copied. The SHACL shapes (`shacl/`, section 5) catch the first and the last (rules G1 and S3) and cannot catch the two free-text defects.
- **C7 Driver timing.** The manuscript gives Eq. (5) with "A=1, B=80, C=0.27 and N=1" for the single-chamber profile of Figure 3 (S6P p. 8) and "a fixed heart rate of 80 beats/minute" for the closed loop (p. 17), which matches the CellML period of 0.75 s. It does not state C for the closed-loop runs; CellML C = 0.375 s (half the period) has no located source. Paeme's C_1 = 0.27 s matches the manuscript's Figure 3 value.
- **C8 Aortic elastance.** Paeme Table 1 prints E_ao = 0.0; CellML 0.6913. Almost certainly a typesetting error in Paeme, but recorded as such. The manuscript gives no value.
- **C9 Inertance on the inflow valves.** The manuscript includes inertia "only … where the velocity ﬂuctuations are signiﬁcant, such as in the aorta and the pulmonary artery" (S6P p. 9), excludes it for "the systemic and pulmonary veins (R pu and R vc)" (p. 13), and Figure 1 draws inductors only as L.av and L.pv. The CellML has non-zero L_mt and L_tc with inertial ODEs for Q_mt and Q_tc (E29, E31); Paeme 2011 Table 2 carries the same four values. The source of L_mt and L_tc is UNKNOWN.
- **C10 Offsets in the septum equation.** Manuscript Eq. (20) contains V_d,lvf, V_o,lvf, V_d,rvf and V_o,rvf inside the free-wall terms; CellML E18 omits them, as does Revie (A.11). With the CellML values (all four are 0) there is no numerical effect, but there would be if those parameters changed.
- **C11 Valve-law encoding.** The manuscript implements "close on ﬂow, open on pressure" by changing the state vector: "When a ﬂow rate (Q) becomes negative, it is removed from the state vector" and is "reincluded" when the pressure gradient favours forward flow (S6P pp. 14-15). The CellML instead keeps Q as a state and sets dQ/dt = 0 while ΔP < 0 and Q < 0 (E29-E32), so a negative Q reached within one step is held, not reset to zero. Read-only check of runs A, B and C (Hermes request [redacted: request id]; `analyze_c11.py` SHA-256 eb3da405…7a5, `c11-results.json` SHA-256 a3baef9a…5af; inputs match the PROV record hashes): each run has three Q_av < 0 spans, Q_av is exactly constant within every span (max − min = 0), and P_lv − P_ao < 0 at every sample in every span. That is the sampled behaviour E30 predicts and supports reading the negative values as an artefact of the CellML encoding rather than physiology; the 1 ms output cannot show the step in which each value arose. The size of the frozen value does not scale uniformly with the step: B/C ratios are 2.0000, 16.27 and 10.50 for spans 1-3. Only span 1, which starts at t = 0 from Q_av = 0 with P_lv − P_ao = −94, halves with the step. One possible reason, not tested, is that span 1 begins on a step boundary while the later spans begin mid-step at an arbitrary phase.

## 4. UNKNOWN register

- Smith 2004 parameter values: the author manuscript has no parameter table; whether the published version adds one is UNKNOWN (published version not seen).
- Sources of the peripheral P_th terms (C3), of L_mt and L_tc (C9), and of the closed-loop driver delay C = 0.375 s (C7): none is in the manuscript.
- OPB licence; OPB official current version identifier (BioPortal not reachable; OWL has no versionIRI).
- FMA licence text (UW draft document not retrieved); FMA release used by Rosse and Mejino 2003 versus 5.1.0.
- OMEX metadata normative rules (both records abstract-only; publisher page refused).
- Which CellML hemodynamics model is the Harmonizing paper's example archive.
- OPB definitions for OPB_01194/01195 (no `rdfs:comment`) and whether OPB dependency classes carry formal player restrictions.
- An OPB class for the weighted activation law E7/E13, the Gaussian driver and the piecewise valve switch.
- Temporal-aggregation vocabulary for beat-mean quantities (none found in this source set).
- SemGen 2019 supplementary merging example (not open access).

## 5. What SHACL and PROV-O can and cannot do here

- SHACL (S7) validates an RDF graph against shapes and reports `sh:conforms`; it can enforce the structural rules above (one bearer per pressure, allowed property classes, source and sink present on flows, equal reference slots for asserted equivalences, shared bearer across a capacitive dependency). It cannot test physiological validity or numeric agreement, and a shape passes vacuously on unannotated data unless `sh:minCount` is used.
- PROV-O (S8) records which file, run, solver and agent produced which artefact and how one version derives from another (`wasDerivedFrom`, `wasRevisionOf`, `hadPrimarySource`, `wasQuotedFrom`); `alternateOf`/`specializationOf` are the closest standard terms for "two annotations of the same thing from different aspects" without asserting identity. It does not validate anything.
- Neither standard demonstrates physiological plausibility; the brief's separation between the standards' role and physiological validation holds.
- Shapes written 2026-11-01 (`shacl/`) in the identifiers of the node specification v2: eleven generic rules for OMEX v1.2 composite annotations (property class, bearer present, fluid volume bearer, energy differentials, processes, participants as single or lumped fluid portions, constitutive properties, v2 containers, v2 valve locations, coverage) and seven Smith-specific rules (chamber pressures have no sink, free-wall pressures have one, a pressure and its volume are the same blood, flow direction matches the driving pressure difference, valve flows occur in their valve, venous compartments include their atrium, each compartment lies in its v2 container), the third to fifth reading equation dependencies from `shacl/smith2004_dependencies.ttl`. Positive and negative control fixtures produce exactly their expected results, and the runner checks that every anatomical identifier is a v2 primary identifier. On the workspace 267 annotation, translated to OMEX form, there are 22 Violations, 7 Warnings and 46 Info results (`shacl/report_ws267.md`); all six flow directions agree with the equations.

## 6. Manual comparison group (design sketch, same knowledge for both arms)

The brief asks for a hand-performed semantic and unit comparison that receives the same knowledge as the ontology-assisted path, so that no advantage is assumed. Neal 2015 is the precedent: automatic overlap detection was scored against a human expert and missed about half the overlaps (S14 quote 19).

- Material given to both arms: `smith2004_variable_dictionary.md` (without the "candidate" tables of this document), the S9 annotation table, the project registry listing from `ontology.md`, and the equations.
- Task, fixed in advance: decide each of R1-R13 (and a held-out set of further pairs) as allow / reject / cannot decide, giving the reason and the unit factor if any.
- Arms: (a) two people with the material only; (b) the same material plus the SemSim/OPB composite annotations and the candidate SHACL rules once written. Order and pairs are fixed before anyone sees the answers; decisions and reasons are recorded per pair.
- Outcomes: agreement with the evidence-based decision in this document (which is itself open to challenge), time per pair, number of "cannot decide" answers, and whether C1 is caught without being told.
- What this does not show: anything about numeric correctness or physiology; it compares decision quality on mapping questions only.

## 7. Scope of this review and next steps that follow from it

Done: full texts of six papers and three derivative papers read; the 2004 author manuscript read in full (S6P); OMEX metadata v1.2 read; two W3C Recommendations read; the SemSim reference annotation of the Smith model parsed and label-checked; OPB versions compared; the variable dictionary produced; C5, the pressure reference and the C1 unit reading decided; SHACL shapes written, controlled and run; PROV-O record of the OpenCOR runs committed and confirmed against the server files (`prov/`). Not done: no OWL written; no registry change; no numeric work; the published 2004 article (as opposed to the manuscript) and OMEX v1.0 not seen.

Next steps that the evidence supports, in order: numeric comparison of the Smith CellML runs with the project model is now permitted under the C1 decision and stays report-only; resolve the unsourced CellML features (C3 peripheral P_th, C7 driver delay, C9 inflow inertances), for example from the Matlab code the CellML was translated from; check the CellML output against the manuscript's Figure 7; select FMA entities for the thoracic-cavity contents so P_pcd and P_th can be annotated; carry the v2 node specification (`anatomy_nodes_v2.md`), already propagated to the SHACL layer, into the registry.
