# Anatomical node specification v2 (2026-11-01)

Established under the user's directive that nodes be built from the latest knowledge. This page is the current node list for the Smith 2004 semantic layer. Propagated on 2026-11-01 to the SHACL shapes, fixtures and the workspace 267 translation (`shacl/`, rules S7 and the v2 identifier check); the project registry uses the v2 identifiers for the nodes it refers to (blood, heart, both ventricles and ventricular cavities, the four valves) and keeps its peripheral compartments local (`decisions.md`, "Node specification v2 applied to the registry"). Machine-readable copy: `anatomy_nodes_v2.json`.

## Principles and their sources

1. **Identifier: Uberon first, FMA where Uberon lacks the structure, and always both.** Current physiology infrastructure works this way. NIH SPARC: "our core anatomical ontology is UBERON, a pan-species anatomical ontology", supplemented with FMA and EMAPA (S23). SCKAN 2025: "UBERON … forms the “backbone” of its anatomical terminology efforts. Species-specific ontologies such as FMA … are used to supplement as necessary" (S23). HRA 2023 states the rule this specification adopts: the identifier "was based on the UBERON ID if possible. If the vessel was not in UBERON, we used an FMA ID if it existed" (S23). A 2024 OMEX-style annotation of a CellML circulation model from the Auckland group, described by its README as preliminary, writes blood in the LV cavity as UBERON:0000178 part of UBERON:0016514 (S23). Counter-evidence is recorded: OMEX metadata v1.2 (2021) recommends FMA and does not mention Uberon, and Physiome repository practice up to 2023 is FMA-based (S16, S23). Status: Uberon release 2026-10-01, active, CC BY 3.0; FMA 5.1.0 released 2026-05-15, CC BY 4.0, listed "inactive" by the OBO Foundry. Equivalence: 25 of 30 structures have a Uberon term carrying the same FMA cross-reference (`docs/evidence/d_uberon_fma_map.json`); Uberon's bridge file defines each FMA class as the Uberon class restricted to Homo sapiens (S23).
2. **Bearer form unchanged.** Blood is part of a cavity or lumen (decisions.md, C5). Heart chambers use Uberon cavity terms. Vessels use FMA lumen terms, because Uberon has no vessel-specific lumen, only "lumen of blood vessel" UBERON:0010161.
3. **Compartment meaning comes from the source paper.** The manuscript says the peripheral circulation is "modelled using elastic chambers, simulating the arteries and veins, and resistances, simulating blood ﬂow through the capillaries" (S6P pp. 12-13). The "aorta", "vena cava", "pulmonary artery" and "pulmonary vein" chambers are therefore lumped arterial and venous beds named after a representative vessel, and Smith-derived models describe them as systemic and pulmonary arteries and veins (S12, S24). This is an interpretation of the paper's wording; the pressure targets still refer to aortic and pulmonary-artery pressure (S6P p. 17).
4. **Which structures are nodes.** (a) Every structure a variable, process or equation refers to (decisions.md, valves). (b) Structures the model lumps: the atria, as parts of the venous compartments (decisions.md, atria). (c) Catalogue nodes, with identifiers but no assertions in the Smith graph, for heart structures current adult closed-loop models do not represent. All surveyed general-purpose models since 2018 represent four chambers and four valves; none of the adult models surveyed includes the valve of the inferior vena cava or of the coronary sinus, and the foramen ovale appears only in fetal and neonatal models (S24). Recent reviews describe the Eustachian valve as becoming "irrelevant" after the foramen ovale closes and the coronary sinus valve as a vestigial remnant (S24).

## Node table

`primary` names the ontology of the primary identifier. Classes: modelled (referred to by the model), lumped part, catalogue (identifier only), reference (organ-level term for registry and context).

| key | structure | Uberon | FMA | primary | class | role in the Smith model | change from v1 |
|---|---|---|---|---|---|---|---|
| `blood` | Portion of blood | UBERON:0000178 blood | FMA:9670 | UBERON | modelled | the fluid of every chamber and compartment | v1 FMA:9670 -> UBERON primary |
| `pericardial_fluid` | Pericardial fluid | UBERON:0002409 pericardial fluid | FMA:9887 | UBERON | modelled | contents of the pericardial space; sink of P_lvf, P_rvf | v1 FMA:9887 -> UBERON primary |
| `lv_cavity` | Cavity of left ventricle | UBERON:0016514 cavity of left ventricle | FMA:9466 | UBERON | modelled | container of LV blood (P_lv, V_lv) | id scheme only |
| `rv_cavity` | Cavity of right ventricle | UBERON:0016509 cavity of right ventricle | FMA:9291 | UBERON | modelled | container of RV blood | id scheme only |
| `la_cavity` | Cavity of left atrium | UBERON:0016513 cavity of left atrium | FMA:9465 | UBERON | lumped part | part of the pulmonary venous compartment blood (lumped) | id scheme only |
| `ra_cavity` | Cavity of right atrium | UBERON:0016522 cavity of right atrium | FMA:11359 | UBERON | lumped part | part of the systemic venous compartment blood (lumped) | id scheme only |
| `mitral_valve` | Mitral valve | UBERON:0002135 mitral valve | FMA:7235 | UBERON | modelled | location of Q_mt (E29) | id scheme only |
| `aortic_valve` | Aortic valve | UBERON:0002137 aortic valve | FMA:7236 | UBERON | modelled | location of Q_av (E30) | id scheme only |
| `tricuspid_valve` | Tricuspid valve | UBERON:0002134 tricuspid valve | FMA:7234 | UBERON | modelled | location of Q_tc (E31) | id scheme only |
| `pulmonary_valve` | Pulmonary valve | UBERON:0002146 pulmonary valve | FMA:7246 | UBERON | modelled | location of Q_pv (E32) | id scheme only |
| `lv_wall` | Wall of left ventricle | UBERON:0036285 wall of left ventricle | FMA:9556 | UBERON | modelled | LV free wall (P_lvf across it) | id scheme only |
| `rv_wall` | Wall of right ventricle | UBERON:0036286 wall of right ventricle | FMA:9533 | UBERON | modelled | RV free wall (P_rvf across it) | id scheme only |
| `iv_septum` | Interventricular septum | UBERON:0002094 interventricular septum | FMA:7133 | UBERON | modelled | septum free wall (V_spt, E18) | replaces Cardiac septum FMA:7180 used in ws267 |
| `pericardium` | Pericardium | UBERON:0002407 pericardium | FMA:9869 | UBERON | modelled | wall across which P_pcd acts (E4) | id scheme only |
| `pericardial_cavity` | Pericardial cavity | UBERON:0001074 pericardial cavity | FMA:11350 | UBERON | modelled | space of P_peri; container of pericardial fluid | id scheme only |
| `thoracic_cavity` | Thoracic cavity | UBERON:0002224 thoracic cavity | FMA:7565 | UBERON | modelled | space of P_th; sink of P_pcd (contents entity still not selected) | id scheme only |
| `systemic_arterial_lumen` | Lumen of systemic arterial tree | UBERON:0004571 systemic arterial system (structure; Uberon has no lumen term) | FMA:52448 | FMA | modelled | container of the "aorta" compartment blood (P_ao, V_ao): lumped systemic arteries (S6P p. 12-13) | v1 Lumen of aorta FMA:12239 -> systemic arterial tree lumen |
| `systemic_venous_lumen` | Lumen of systemic venous tree organ | UBERON:0004581 systemic venous system (structure; no lumen term) | FMA:52454 | FMA | modelled | with the RA cavity, container of the "vena cava" compartment blood (P_vc, V_vc): lumped systemic veins | v1 Set of lumens of vena cava trunks FMA:280059 -> systemic venous tree lumen |
| `pulmonary_arterial_lumen` | Lumen of pulmonary arterial tree | UBERON:0002012 pulmonary artery (structure; no lumen term) | FMA:52449 | FMA | modelled | container of the "pulmonary artery" compartment blood (P_pa, V_pa) | resolves the ws267 P_pa (trunk FMA:14167) / V_pa split in favour of the tree lumen |
| `pulmonary_venous_lumen` | Lumen of pulmonary venous tree organ | UBERON:0013127 pulmonary venous system (structure; no lumen term, no FMA xref) | FMA:52455 | FMA | modelled | with the LA cavity, container of the "pulmonary vein" compartment blood (P_pu, V_pu) | unchanged |
| `svc` | Superior vena cava | UBERON:0001585 anterior vena cava | FMA:4720 | UBERON | catalogue | within the systemic venous compartment; separated only in detailed current models | new catalogue node |
| `ivc` | Inferior vena cava | UBERON:0001072 inferior vena cava | FMA:10951 | UBERON | catalogue | within the systemic venous compartment; separated only in detailed current models | new catalogue node |
| `coronary_sinus` | Coronary sinus | UBERON:0005438 coronary sinus | FMA:4706 | UBERON | catalogue | not in Smith; drains to the RA in models with a coronary circulation | new catalogue node |
| `ivc_valve` | Valve of inferior vena cava | UBERON:0005485 valve of inferior vena cava | FMA:9240 | UBERON | catalogue | not modelled; vestigial in adults; in no adult closed-loop model surveyed | was "omitted, undecided" |
| `cs_valve` | Valve of coronary sinus | UBERON:0004150 coronary sinus valve | FMA:9242 | UBERON | catalogue | not modelled; vestigial; in no adult closed-loop model surveyed | was "omitted, undecided" |
| `fo_valve` | Valve of foramen ovale | UBERON:0035186 valve of foramen ovale | FMA:75348 | UBERON | catalogue | not modelled; foramen ovale appears only in fetal/neonatal models, PFO only as an added branch | was "omitted, undecided" |
| `heart` | Heart | UBERON:0000948 heart | FMA:7088 | UBERON | reference | organ-level reference (registry HR context) | id scheme only |
| `lv` | Left ventricle | UBERON:0002084 heart left ventricle | FMA:7101 | UBERON | reference | organ-level reference used by the registry today (C5: bearer is the cavity) | id scheme only |
| `rv` | Right ventricle | UBERON:0002080 heart right ventricle | FMA:7098 | UBERON | reference | organ-level reference used by the registry today | id scheme only |
| `la` | Left atrium | UBERON:0002079 left cardiac atrium | FMA:7097 | UBERON | reference | organ-level reference | id scheme only |
| `ra` | Right atrium | UBERON:0002078 right cardiac atrium | FMA:7096 | UBERON | reference | organ-level reference | id scheme only |

## What changes when v2 is propagated

- 27 of the 31 nodes take a Uberon primary identifier; the four vessel-lumen nodes keep FMA. FMA remains on every node as the cross-reference.
- The four peripheral compartments change meaning: the "aorta" compartment becomes the systemic arterial tree lumen (v1: Lumen of aorta) and the "vena cava" compartment the systemic venous tree lumen plus the right atrial cavity (v1: Set of lumens of vena cava trunks). This brings Smith's compartments closer to the project's local `sa` and `sv` concepts (R6, R8, R10).
- The workspace 267 split of P_pa (Lumen of pulmonary trunk) and V_pa (Lumen of pulmonary arterial tree) is resolved: both use the pulmonary arterial tree lumen.
- The septum node is the interventricular septum (UBERON:0002094 / FMA:7133), not "Cardiac septum".
- The minor valves, the venae cavae and the coronary sinus are catalogue nodes.

## Not established

- No COMBINE document from 2022-2026 formally recommends Uberon over FMA; the identifier rule rests on SPARC, SCKAN and HRA practice (S23).
- Uberon quirks to watch: the aortic valve has no "connects" relation, the pulmonary valve connects to the generic cardiac ventricle, and the valve of foramen ovale sits under "anatomical conduit space" (S23, S24).
- The entity for the thoracic-cavity contents (source of P_th, sink of P_pcd) is still not selected.
- Principle 3 and the atrial lumping are interpretations of the paper, recorded as such.
