# Cardiovascular semantic registry

## Scope and evidence

`physiosim.ontology` provides an entirely offline registry of **34 variables** and an RDFLib named-graph export. It distinguishes physical property, anatomical context, physical bearer, temporal meaning, units, flow direction, equations, dependencies, and source context. This is a project annotation layer, not an imported reference ontology or a clinical reasoning system.

The bundled OPB v1.07 ontology verifies `Fluid pressure` (`OPB_00509`), `Fluid volume` (`OPB_00154`), `Fluid flow rate` (`OPB_00299`), `Fluid flow resistance` (`OPB_00160`), `Fluid volumetric elastance` (`OPB_00076`), and `Event frequency` (`OPB_01212`).[1] The download is the SemBioProcess project's bundled snapshot, **not a claim to the latest OPB release**.

Anatomy follows the anatomical node specification v2 (`evidence_review/anatomy_nodes_v2.json`; `decisions.md`, "Anatomical node specification v2"): the Uberon term is the identifier and the FMA term it cross-references is kept on the node (`Concept.xref`, exported as `oboInOwl:hasDbXref`). The registry uses ten v2 nodes: `blood` (`UBERON:0000178`, FMA:9670), `cavity of left ventricle` (`UBERON:0016514`, FMA:9466), `cavity of right ventricle` (`UBERON:0016509`, FMA:9291), the four valves (`UBERON:0002137` aortic, `UBERON:0002135` mitral, `UBERON:0002134` tricuspid, `UBERON:0002146` pulmonary), `heart` (`UBERON:0000948`, FMA:7088), `heart left ventricle` (`UBERON:0002084`, FMA:7101) and `heart right ventricle` (`UBERON:0002080`, FMA:7098). Labels and cross-references are checked in tests against the Uberon 2026-10-01 records in `evidence/d_uberon_fma_map.json`. The v1 FMA records (`fma7101`, `fma7098`, `fma9670`, `fma7088`) remain in `evidence/b_ols_terms.json` as label evidence for those four FMA cross-references.[2][3][4][5]

GO provides process context `blood circulation` (`GO_0008015`) and `heart contraction` (`GO_0060047`).[6][7] The Disease Ontology label `congestive heart failure` (`DOID_6000`) is retained as disease vocabulary context only, **not an assertion that the baseline has that disease**.[8]

CellML Metadata 1.0 recommends RDF for associating metadata with CellML objects.[9] This project follows that separation of mathematical model and semantic metadata, using local composite property/bearer/location relations. Two standard BioModels.net biology qualifiers replace local relations (user decision, `decisions.md`, "Node specification v2 applied to the registry"): `bqbiol:isPartOf` links blood to its v2 cavity (C5 "part_of", in the form the SHACL shapes use) and `bqbiol:occursIn` links each valve flow to its valve ("Anatomical structures as nodes"). All other relations remain project-local, so this is use of those two qualifiers, not conformance to the qualifier vocabulary as a whole. It does **not** claim CellML, SemSim or OMEX conformance and does not serialize CellML. The registered variables are not automatically executable equations.

All external identifiers used in the built-in catalog are label-checked against retained evidence in tests. `ontology_sources.json` records the exact retrieval URLs, UTC retrieval timestamps, SHA-256 hashes of full retrieved responses, bounded evidence filenames, verification method, and limitations. `evidence/b_opb_excerpt.json` retains selected class XML; `evidence/b_ols_terms.json` retains exact-label API records; `evidence/b_cellml.json` retains a bounded specification excerpt. Hashes identify the original responses, **not** the reduced evidence files. The citation ledger is `evidence/b_citations.json`.

## Explicit local concepts

The namespace `https://example.org/physiosim/` intentionally identifies project-local concepts. It is not advertised as a resolvable external ontology. `Concept.local` marks local extensions.

The lumped systemic/pulmonary arterial and venous compartments, whole six-compartment circulation, six modeled flow paths, volume compliance, cardiac output, and stroke volume are local concepts. No unverified external identifiers are used for these concepts. Their local status does not imply external terms do not exist; exact suitable mappings were not established in this bounded research task. Aggregate compartments are not equated to a single named artery, vein, or organ. The v2 vessel-lumen nodes describe the Smith 2004 compartments; no recorded decision maps this model's `sa`, `sv`, `pa` or `pv` to them, so they stay local.

Cardiac output is explicitly **complete-beat mean aortic outflow**, not instantaneous aortic flow. Stroke volume is **the integral of forward aortic flow over a complete beat**, matching the executable `stroke_volume_ml` metric; it is not total ventricular volume. The separately reported volume-extrema ejection fraction uses `(EDV-ESV)/EDV`, and sampled `EDV-ESV` can differ from flow-integrated SV. Their properties remain distinct even when dimensions coincide. Heart rate uses OPB event frequency with heart-contraction process context.

## Registry and model names

```python
from physiosim.ontology import cardiovascular_registry
r = cardiovascular_registry()
pressure = r['P_lv']
print(pressure.property.uri, pressure.anatomy.uri, pressure.unit)
```

| Variables | Canonical units | Meaning |
|---|---|---|
| `P_lv`, `P_rv`, `P_sa`, `P_sv`, `P_pa`, `P_pv` | `mmHg` | Compartment blood pressure |
| `V_lv`, `V_rv`, `V_sa`, `V_sv`, `V_pa`, `V_pv` | `mL` | Compartment blood volume |
| `E_lv`, `E_rv` | `mmHg/mL` | Time-varying ventricular elastance |
| `C_sa`, `C_sv`, `C_pa`, `C_pv` | `mL/mmHg` | Linear compartment compliance |
| `Q_aortic`, `Q_systemic`, `Q_tricuspid`, `Q_pulmonary_valve`, `Q_pulmonary`, `Q_mitral` | `mL/s` | Directed flow |
| Corresponding six `R_…` names | `mmHg*s/mL` | Flow-path resistance |
| `HR` | `1/min` | Heart contraction frequency |
| `CO` | `mL/s` | Complete-beat mean aortic outflow |
| `SV` | `mL` | Forward aortic flow integrated over a full beat |
| `V_total` | `mL` | Sum of six compartment volumes |

LV and RV volume and pressure are properties of blood that is part of the ventricular cavity (C5); `E_lv`, `E_rv`, `CO` and `SV` keep the organ-level ventricle and `HR` the heart. The four valve flows carry `occurs_in`, the valve where the flow process takes place; the systemic and pulmonary bed flows and all resistances have none. Orientation codes are `lv→sa→sv→rv→pa→pv→lv`; their flow endpoints are the compartment containers. Venous reservoirs subsume atrial filling in this simplified model; the tricuspid and mitral paths do not assert a literal direct anatomical vein-to-ventricle connection. All pressures use the same explicitly recorded model-gauge reference, with fixed external pressure zero. Local equation strings describe the intended model relationships; `V0`, activation, and extrema are equation placeholders, not separately registered variables.

## Connection API: explicit rescaling, never silent equivalence

```python
from dataclasses import replace
from physiosim.ontology import UnitConversion, validate_connection
p_pa = replace(r['P_lv'], name='pressure_port_pa', unit='Pa')
connection = validate_connection(
    r['P_lv'], p_pa,
    conversion=UnitConversion(source_unit='mmHg', target_unit='Pa'),
)
p_pa_value = connection.convert(120.0)
```

`validate_connection(source, target, *, conversion=None)` returns an immutable `Connection` or raises `SemanticConnectionError`. The returned `factor` and `convert(value)` are the **required numeric conversion contract**. A simulation connector must actually apply `.convert` when moving numeric values; obtaining validation alone does not rescale arrays elsewhere.

Validation first rejects empty required descriptors (including anatomy/property identifiers, references and biological context) and missing/unknown flow endpoints. It then requires exact anatomy/property URIs, flow-process location (`occurs_in`), bearer kind, biological context, temporal context, reference, and orientation equality. It checks each endpoint's units against the known property contract as well as checking conversion compatibility. Unknown properties fail closed. Differently spelled unit strings require an explicit `UnitConversion`, even if Pint would regard them as aliases. The contract must exactly match the source and target unit strings; Pint computes the numeric multiplier. Custom unchecked factors, offsets, and sign reversal are not supported. Supported scale conversions include mmHg↔Pa, mL↔L, 1/min↔1/s, mL/s↔L/min, and compatible resistance/compliance/elastance units.

This validates **direct variable equivalence**, not biological causation or physical adjacency. Connecting LV pressure directly to RV pressure is rejected; connecting a pressure to a flow is rejected even if a user attempts to relabel units. Reversed or missing flow orientation at one endpoint is rejected. A separate physical junction/component must implement pressure-drop equations, sign conventions, and conservation laws.

## RDF API and provenance boundaries

```python
from pathlib import Path
from physiosim.ontology import build_graph, export_graph

dataset = build_graph(r)             # rdflib.Dataset
text = export_graph(r, format='trig') # also supports 'nquads'
Path('annotations.trig').write_text(text)
```

Three graph identifiers are used:

- `…/graph/verified-labels`: verified external labels, source links and the FMA cross-reference of each v2 node, not ontology entailments.
- `…/graph/model-assertions`: project variable annotations, composite bearers (`bqbiol:isPartOf` a v2 cavity, otherwise `sim:locatedIn`), valve-flow locations (`bqbiol:occursIn`), local concepts, equations, dependencies, process context and directed flow endpoints.
- `…/graph/provenance`: explicit graph status and the non-diagnostic disease-context note.

No `owl:sameAs`, `owl:equivalentClass`, `rdfs:subClassOf`, disease diagnoses, or ontology-derived causal edges are manufactured. Caller-provided unrecognized concepts stay in model assertions and are marked unverified. Turtle and other flattening formats are rejected by `export_graph` so graph boundaries cannot silently disappear. TriG serialization and reparsing are tested; current RDFLib emits dependency-internal deprecation warnings during that operation.

## Executable bindings and integration corrections

`physiosim.ontology.bindings.observations(result)` binds every registered variable to the actual model array, parameter or computed metric. `connect_value(result, name, target, conversion=...)` validates metadata before transferring the numerical value and applying its explicit conversion. The main experiment exercises this route for cardiac output.

Integration review corrected the original SV descriptor from EDV minus ESV to forward aortic flow integrated over the final complete beat. The ejection-fraction metric remains volume-extrema based. `source_document` links each variable to `docs/physiology.md`; `applicable_contexts` identifies the three experimental parameter scenarios. Pressure reference is recorded for pressure variables, not incorrectly applied to unrelated quantities. Scenario applicability is descriptive metadata, not proof that different scenario results are interchangeable.

The archived `evidence/b_annotations.trig` is the original development export. The committed `results/phase1/` and `results/replay/` exports predate the v2 registry and still show v1 FMA identifiers; regenerate them, or call `export_graph`, for the current registry. Model relations, file references and scenario concepts are project-authored assertions.

## Validation limits

- No ontology reasoner, subclass closure, synonym equivalence, or cross-version identifier alignment.
- Source evidence verifies identifiers and labels, **not** that our variable mappings or equations are authoritative ontology entailments.
- No species, patient identity, geometry, tissue/material properties, or spatial resolution validation beyond the recorded local model context.
- No automatic inference of pressure reference or flow orientation; metadata must be supplied honestly.
- No equation parsing, mathematical proof of conservation, dynamical stability, clinical validity, or numeric result validation in this layer.
- Validation supports the built-in property catalog; extending it requires adding an explicit property-unit contract.
- No automatic equivalence between cardiac output and instantaneous flow, or between stroke volume and compartment volume.
- `build_graph` uses the known compartment/context codes for flow and process annotations; custom codes need corresponding catalog extensions.

Run offline tests with `PYTHONPATH=src .venv/bin/python -m pytest tests/test_ontology.py -q`. Implementation followed incremental RED→GREEN slices for registry construction, connection rejection/conversion, RDF export, and property/unit consistency.

## Sources

[1] https://raw.githubusercontent.com/SemBioProcess/SemGen/master/src/semsim/owl/OPBv1.07.owl — OPB v1.07 bundled by SemBioProcess
[2] https://www.ebi.ac.uk/ols4/api/search?q=Left+ventricle&ontology=fma&exact=true&rows=10 — EBI OLS4: Left ventricle
[3] https://www.ebi.ac.uk/ols4/api/search?q=Right+ventricle&ontology=fma&exact=true&rows=10 — EBI OLS4: Right ventricle
[4] https://www.ebi.ac.uk/ols4/api/search?q=Portion+of+blood&ontology=fma&exact=true&rows=10 — EBI OLS4: Portion of blood
[5] https://www.ebi.ac.uk/ols4/api/search?q=Heart&ontology=fma&exact=true&rows=10 — EBI OLS4: Heart
[6] https://www.ebi.ac.uk/ols4/api/search?q=blood+circulation&ontology=go&exact=true&rows=10 — EBI OLS4: blood circulation
[7] https://www.ebi.ac.uk/ols4/api/search?q=heart+contraction&ontology=go&exact=true&rows=10 — EBI OLS4: heart contraction
[8] https://www.ebi.ac.uk/ols4/api/search?q=congestive+heart+failure&ontology=doid&exact=true&rows=10 — EBI OLS4: congestive heart failure
[9] https://www.cellml.org/specifications/metadata — CellML Metadata 1.0 Specification
