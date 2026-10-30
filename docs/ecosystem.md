# Ecosystem reuse assessment — independent research review

## Scope and disposition

Research-only inspection, retrieved 2026-10-30 UTC. No third-party model, package, browser demo, installation script, or test was executed. HTTP responses, source text, checksums and retrieval timestamps are retained in `docs/evidence/c_*`; `c_sources.json` owns the citation numbering. Statements about upstream tests below describe upstream documentation, not tests independently reproduced here. License screening is technical due diligence, not legal advice.

**Recommendation:** implement and verify the small six-compartment research model independently; keep an explicit future adapter boundary for the existing CardioLab engine and CellML exchange. Do not imply that all alternatives are freely redistributable or that a local semantic registry is a SemSim implementation. Do not copy restricted implementations into a permissively licensed core.

## Exact requested repository: accessible, not missing

The exact `Carraway-and-Gatsby/cardiac-simulator` GitHub page, repository API and raw `main/README.md` were accessible without authentication and returned HTTP 200.[1][2][3]
The license and physiology documentation were also accessible; the API reports the exact full name, default branch `main`, and MIT license.[2][10][12]
The resolved `main` commit was `b3f437403e709f11099f50b38272f77ded5ea9b5`; its raw numerical engine and license were separately fetched successfully.[13][27][28]
The first generic web search was unhelpful, which is not evidence of repository absence. Transport failures, 404s on guessed filenames, and search omissions must never be reported as proof of nonexistence.

The repository is **CardioLab**, a React/TypeScript/Three.js educational lab, with a rendering-independent numerical engine and explicit warnings against clinical interpretation.[3][12]
The inspected engine implements **eight** volume compartments: LA, LV, systemic arteries, systemic veins, RA, RV, pulmonary arteries and pulmonary veins; it includes exponential passive ventricular pressure, time-varying activation, resistive vascular paths, ideal competent valves and a signed mitral-regurgitation path.[12][27]
Its published documentation describes conservation checks, RK4 step refinement and periodic convergence, but explicitly says parameters are engineering estimates and external waveform validation and cardiovascular-expert review remain outstanding.[12]

### Feasible reuse, with boundaries

- **Original code/documentation:** the pinned MIT license permits reuse and modification subject to preservation of its copyright and permission notice.[28] Preserve those notices if source is copied or translated; a language port is not grounds to omit attribution.
- **Not all repository content is MIT:** HRA-derived anatomical material retains CC BY 4.0; upstream notices distinguish code, anatomical metadata, generated meshes and dependencies.[11] No anatomical asset is required for the proposed six-state mathematical prototype.
- **Adapter rather than silent equivalence:** the existing TypeScript `simulate`, `evaluateState`, and `volumeDerivative` interfaces are plausible integration points based on source inspection, not an executed interoperability demonstration.[27] A six-state model cannot drop LA/RA and retain an eight-state parameter set without re-deriving topology, initialization and pressure interpretation.
- **Reuse testing ideas, not validation claims:** cross-check conserved edge signs, beat alignment, signed flows and domain diagnostics. Upstream flags simultaneous forward filling/ejection and passive-pressure dominance as interpretation failures even when numerical convergence succeeds.[12][27]
- **Decision for this task:** reference and potential future bridge only. The present baseline/reduced-contractility model should be labeled a separate reduced model, not “the CardioLab engine,” a reproduction of its outputs, or an externally validated successor.

## Alternatives and license gates

| Ecosystem | Evidence inspected | Reuse decision for this prototype |
|---|---|---|
| Physiome Model Repository / CellML | The inspected cardiovascular model's license/citation page states CC BY 3.0. CellML 2.0 specifies components, explicit units and variable equivalence constraints.[8][16] | Good route for **model exchange and independent reference cases**. License each chosen model and imported dependency separately; repository policy does not automatically settle every linked asset's rights. No model was executed or imported. |
| OpenCOR | Current repository `LICENSE.txt` is GPL v3, independently corroborated by the official licensing page and GitHub metadata.[6][15][23] | Potential separate verification tool; do not embed code while assuming Apache permissions. Review copyleft and bundled-library terms before redistribution/linking. Version-specific import/export compatibility is untested. |
| SemSim / SemGen | SemGen describes composite physical-property/entity/process annotations; SemSim descriptions connect biological meaning to mathematical implementation.[4][18] SemGen's README permits redistribution/use **for non-commercial purposes**, requires the entire notice, and identifies separate JxBrowser commercial restrictions.[4] | Reuse the **published conceptual approach**, with citations, through independently written typed metadata and validation. Do not vendor SemGen or represent it as unrestricted BSD/MIT software. This inspection does not establish a separate redistributable license for every SemSim ontology artifact. |
| CircAdapt | Current framework EULA grants academic User/Developer User rights for educational, non-commercial and research purposes; it restricts modification for Users and distribution of code/improvements for Developer Users without permission.[5] The documentation exposes component-verification sections.[29] | Useful scientific comparator; **not approved for code reuse or bundling** here. Obtain appropriate permission and confirm eligibility before execution/adaptation/distribution. Do not generalize older CircAdapt licensing statements to this framework. |
| Pulse Physiology Engine | `stable/LICENSE` and `NOTICE` establish Apache 2.0 for the engine and identify third-party components.[20][21] Methodology describes a closed-loop cardiovascular system, time-varying heart elastance, tuning and feedback; the heart representation omits explicit atria.[22] | Permissive-engine reuse is plausible after version and dependency audit. More appropriate as a later independently configured comparator than a drop-in six-state dependency. Tuning, feedback, topology and hidden defaults must be matched before any numerical comparison. |

### Important conflicting documentation

The CellML modeling-environments directory describes OpenCOR as Apache v2.0 and refers to release 0.5.[9] The directly inspected current repository license is **GNU GPL version 3**, and the official OpenCOR licensing page independently agrees.[6][23] Prefer the artifact-specific license over an older ecosystem directory description. This is a concrete reason not to infer licensing from search summaries.

SemGen's license starts with familiar redistribution language, but the operative phrase is “permitted for non-commercial purposes”; calling it BSD merely from its opening wording would be incorrect.[4] CircAdapt's current EULA also distinguishes User and Developer User, and specifies that improvements belong to the licensor.[5] Neither is a safe default dependency for a permissively redistributable prototype.

The inspected Physiome license/citation page is specifically for *Zero dimensional (lumped parameter) modelling of native human cardiovascular dynamics*.[8] It supplies an attribution route, not evidence that its equations or numerical outputs have been checked here. CellML validity is a syntactic/mathematical encoding property: equivalent-variable links require compatible unit reductions and scaling, but these rules alone do not establish biological compatibility.[16]

## Scientific basis and limits of reuse

A review of 0D/1D models motivates the hydraulic-electrical analogy, compartment ODEs and the need to choose dimensionality for the research question; it also discusses parameter-identification difficulties as model detail increases.[25] The Smith et al. 2004 abstract concerns a minimal haemodynamic model **including ventricular interaction and valve dynamics**.[19] Our intended simple elastance/diode six-compartment system should not be named a faithful Smith reproduction: full equations and original parameter tables were not independently obtained in this review, and those extra mechanisms are outside the intended reduced model.

Burkhoff and Tyberg's theoretical closed-loop study is especially relevant to reduced contractility: decreasing LV end-systolic elastance reduced output and mean arterial pressure, but a large pulmonary venous pressure rise depended on additional mechanisms, particularly venous unstressed volume changes.[26] Therefore a contractility-only experiment must not promise pulmonary edema, a specific filling-pressure increase, or the full phenotype of clinical heart failure. The cited study is a theoretical analysis, not clinical validation of this software.

SemGen's published composition study reports successful cardiomyocyte merges **and** important manual adjustments, granularity/directionality problems and missing ontology terms.[18] Its time-saving discussion explicitly says formal timing tests had not yet been performed and calls its evidence anecdotal.[18] The appropriate local claim is narrower: “the rule-based assistant detected these predefined incompatible bindings and produced equivalent permitted configurations.” It is not yet “ontology improves scientists' productivity,” “automatic biological integration,” or validation of arbitrary model composition.

## Concrete scientific and engineering risks

1. **Attribution/identity risk:** eight-compartment CardioLab, six-compartment reduced dynamics, and published minimal models are distinct systems. Display topology, equation version and provenance with every result.
2. **Validation-transfer risk:** upstream tests, documentation and plausible waveforms do not validate newly written code or establish external biological accuracy. Mathematical verification and biological validation must be reported separately.
3. **Missing physiology:** omitting atria, baroreflexes, ventricular interaction, pericardium, nonlinear filling mechanics, valve inertia and distributed wave effects limits what can be inferred. These are deliberate proposed-model omissions, not newly discovered defects in an implemented core.
4. **Parameter provenance/identifiability:** label estimated values as estimates, not clinical normal values. A plausible output alone cannot identify the unique generating parameters; the literature describes this difficulty.[25]
5. **Numerical false assurance:** conservation can pass with reversed or physiologically wrong edges; a stable-looking last beat can be unconverged; valve kinks can reduce the observed integration order. Independent equation, direction, periodicity and refinement checks are required.
6. **Semantic false assurance:** same dimension does not mean same anatomy, pressure reference, scale, sign or variable role. A label match is not a constitutive-law or whole-model compatibility proof. Published SemGen experience illustrates directionality and granularity mismatches.[18]
7. **Experimental confounding:** a hand-authored “manual failure” versus a curated assistant success shows a test-fixture difference, not measured human performance. Include unit-only and semantic-rule conditions, independent ground truth and annotation cost.
8. **License risk:** GPL OpenCOR, non-commercial SemGen/JxBrowser terms, and the current CircAdapt EULA require explicit decisions rather than assuming “public source” means unrestricted reuse.[4][5][6]

## Evidence and next gate

`c_sources.json` is the citation ledger; `evidence/c_retrievals.json` records raw-response paths, HTTP status, retrieval timestamp and SHA-256. Plain-text derivatives are provided for readable quote verification. GitHub and raw-file captures are observations at retrieval time; only the numerical engine and its MIT license were additionally pinned to the resolved CardioLab commit. A missing `OpenCOR/README.md` returned 404; `README.rst`, repository metadata and the official licensing page were accessible, so the filename failure is not a repository failure.[14][15][24]

Before importing external code: record exact commit/version, inspect all copied-file and dependency notices, document modifications and attribution, and then request an execution/integration review. Before physiological claims: obtain appropriate external reference data and expert review. The separate `verification_protocol.md` defines the local mathematical and semantic acceptance gates; none are recorded as passed in this research-only assignment.

## Sources

[1] https://github.com/Carraway-and-Gatsby/cardiac-simulator — Exact requested GitHub repository
[2] https://api.github.com/repos/Carraway-and-Gatsby/cardiac-simulator — GitHub repository metadata
[3] https://raw.githubusercontent.com/Carraway-and-Gatsby/cardiac-simulator/main/README.md — CardioLab README
[4] https://raw.githubusercontent.com/SemBioProcess/SemGen/master/README.md — SemGen README and license
[5] https://framework.circadapt.org/latest/license.html — CircAdapt framework current EULA
[6] https://raw.githubusercontent.com/opencor/opencor/master/LICENSE.txt — OpenCOR repository GPLv3 license
[8] https://models.physiomeproject.org/exposure/3c63146a30a3118ee7725784743b9a7d/ModelMain.cellml/license_citation — Physiome cardiovascular model license and citation
[9] https://www.cellml.org/tools/modeling-environments — CellML modeling environments directory
[10] https://raw.githubusercontent.com/Carraway-and-Gatsby/cardiac-simulator/main/LICENSE — CardioLab MIT license on main
[11] https://raw.githubusercontent.com/Carraway-and-Gatsby/cardiac-simulator/main/THIRD_PARTY_NOTICES.md — CardioLab third-party notices
[12] https://raw.githubusercontent.com/Carraway-and-Gatsby/cardiac-simulator/main/docs/physiology-model.md — CardioLab model equations and scientific scope
[13] https://api.github.com/repos/Carraway-and-Gatsby/cardiac-simulator/commits/main — CardioLab main commit metadata
[14] https://raw.githubusercontent.com/opencor/opencor/master/README.md — HTTP 404 for guessed OpenCOR README.md path
[15] https://api.github.com/repos/opencor/opencor — OpenCOR repository metadata
[16] https://www.cellml.org/cellml/2.0 — CellML 2.0 normative specification
[18] https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0145621 — Neal et al. 2015 semantic cardiomyocyte composition
[19] https://pubmed.ncbi.nlm.nih.gov/15036180 — Smith et al. 2004 minimal haemodynamic model abstract
[20] https://gitlab.kitware.com/physiology/engine/-/raw/stable/LICENSE — Pulse stable branch Apache 2.0 license
[21] https://gitlab.kitware.com/physiology/engine/-/raw/stable/NOTICE — Pulse stable branch copyright and dependency notice
[22] https://pulse.kitware.com/_cardiovascular_methodology.html — Pulse cardiovascular methodology
[23] https://www.opencor.ws/licensing.html — OpenCOR official licensing page
[24] https://raw.githubusercontent.com/opencor/opencor/master/README.rst — OpenCOR accessible README.rst
[25] https://pmc.ncbi.nlm.nih.gov/articles/PMC3103466 — Shi et al. 2011 review of 0D and 1D blood flow models
[26] https://pubmed.ncbi.nlm.nih.gov/8238596 — Burkhoff and Tyberg 1993 theoretical LV dysfunction analysis
[27] https://raw.githubusercontent.com/Carraway-and-Gatsby/cardiac-simulator/b3f437403e709f11099f50b38272f77ded5ea9b5/src/simulation/engine.ts — CardioLab numerical engine at pinned commit
[28] https://raw.githubusercontent.com/Carraway-and-Gatsby/cardiac-simulator/b3f437403e709f11099f50b38272f77ded5ea9b5/LICENSE — CardioLab MIT license at pinned commit
[29] https://framework.circadapt.org/latest/userguide/verification/index.html — CircAdapt component verification index
