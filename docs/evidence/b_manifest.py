"""Rebuild the source manifest and citation ledger from retained evidence."""
from pathlib import Path
import json
import subprocess
import xml.etree.ElementTree as ET
from physiosim.ontology import ANATOMY, PROPERTIES, BLOOD, CONTEXTS, cardiovascular_registry

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'docs/evidence'
ledger = EVIDENCE / 'b_citations.json'
script = Path.home() / '.hermes/skills/research/grounded-citations/scripts/sources.py'

def cite(*args):
    result = subprocess.run(['python3', str(script), '--ledger', str(ledger), *args], capture_output=True, text=True, check=True)
    print(result.stdout.strip())

cite('reset')
ols = json.loads((EVIDENCE / 'b_ols_terms.json').read_text())
opb = json.loads((EVIDENCE / 'b_opb_excerpt.json').read_text())
cellml = json.loads((EVIDENCE / 'b_cellml.json').read_text())
source_by_uri = {}
for q in ols:
    for d in q['records']:
        source_by_uri[d['iri']] = {**q['provenance'], 'evidence_file': 'docs/evidence/b_ols_terms.json', 'label': d['label'], 'verification': 'exact-label EBI OLS4 API ontology-filtered response'}
for xml in opb['class_xml']:
    e = ET.fromstring(xml)
    source_by_uri[e.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about')] = {**opb['provenance'], 'evidence_file': 'docs/evidence/b_opb_excerpt.json', 'label': e.find('{http://www.w3.org/2000/01/rdf-schema#}label').text, 'verification': 'rdfs:label in SemBioProcess-bundled OPB v1.07 OWL download'}
terms = {c.uri: c for c in (*ANATOMY.values(), *PROPERTIES.values(), BLOOD, *CONTEXTS.values()) if not c.local}
entries = [{**source_by_uri[uri], 'uri': uri} for uri in terms]
manifest = {'scope': 'Verified labels are external source data; variable mapping, relations and equations are local model assertions.', 'external_terms': entries, 'cellml_conventions': {k: v for k, v in cellml.items() if k != 'excerpt'}, 'limitations': ['OPB is a SemBioProcess-bundled v1.07 snapshot, not a claim of latest release.', 'FMA/GO/DOID labels verified through EBI OLS4; not full ontology downloads.', 'No external exact identifiers asserted for aggregate circulation compartments, compliance, stroke volume or cardiac output.', 'No OWL entailment, CellML serialization or clinical disease diagnosis.'], 'retrieval_failures': [{'url': 'https://www.ebi.ac.uk/ols4/api/search?q=fluid%20pressure&ontology=opb&rows=5', 'result': 'empty OPB result; switched to bundled ontology download'}, {'url': 'https://www.cellml.org/specifications/metadata/1.0', 'result': '404; corrected via search to official metadata specification URL'}, {'url': 'https://tutorial-on-cellml-opencor-and-pmr.readthedocs.io/en/latest/annotation.html', 'result': '403; used official CellML specification instead'}]}
(ROOT / 'docs/ontology_sources.json').write_text(json.dumps(manifest, indent=2))
cite('add', opb['provenance']['url'], '--title', 'OPB v1.07 bundled by SemBioProcess')
cite('quote', '1', '--text', 'Fluid volumetric elastance', '--from', str(EVIDENCE / 'b_opb_excerpt.json'))
for i, q in enumerate(ols, start=2):
    cite('add', q['provenance']['url'], '--title', 'EBI OLS4: ' + q['query'][1])
    d = q['records'][0]
    quote = '"label": ' + json.dumps(d['label']) + ', "obo_id": ' + json.dumps(d['obo_id'])
    cite('quote', str(i), '--text', quote, '--from', str(EVIDENCE / 'b_ols_terms.json'))
cite('add', cellml['url'], '--title', 'CellML Metadata 1.0 Specification')
cite('quote', '9', '--text', 'The CellML specification recommends the use of the Resource Description Framework for the association of metadata with CellML objects.', '--from', str(EVIDENCE / 'b_cellml.json'))
print(json.dumps({'variables': len(cardiovascular_registry()), 'verified_external_terms': len(terms)}, indent=2))
