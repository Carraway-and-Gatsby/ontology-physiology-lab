"""Bounded provenance capture; downloads data only, never executes sources."""
import concurrent.futures
import datetime
import hashlib
import json
from pathlib import Path
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs/evidence'

def get(url):
    with urllib.request.urlopen(url, timeout=50) as r:
        data = r.read(5_000_000)
        return data, {'url': url, 'resolved_url': r.url, 'retrieved_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data), 'http_status': r.status}

def term_query(pair):
    ontology, label = pair
    url = 'https://www.ebi.ac.uk/ols4/api/search?' + urllib.parse.urlencode(dict(q=label, ontology=ontology, exact='true', rows=10))
    data, provenance = get(url)
    docs = json.loads(data)['response']['docs']
    selected = [d for d in docs if d.get('label', '').lower() == label.lower() and d.get('ontology_name') == ontology]
    return {'query': pair, 'provenance': provenance, 'records': selected}

if __name__ == '__main__':
    pairs = [('fma', 'Left ventricle'), ('fma', 'Right ventricle'), ('fma', 'Portion of blood'), ('fma', 'Heart'), ('go', 'blood circulation'), ('go', 'heart contraction'), ('doid', 'congestive heart failure')]
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        records = list(pool.map(term_query, pairs))
    (OUT / 'b_ols_terms.json').write_text(json.dumps(records, indent=2))
    print([(r['query'], [(d['iri'], d['label']) for d in r['records']]) for r in records])
    url = 'https://raw.githubusercontent.com/SemBioProcess/SemGen/master/src/semsim/owl/OPBv1.07.owl'
    data, provenance = get(url)
    root = ET.fromstring(data)
    ns = {'owl': 'http://www.w3.org/2002/07/owl#', 'rdfs': 'http://www.w3.org/2000/01/rdf-schema#'}
    selected = []
    for c in root.findall('owl:Class', ns):
        labels = [x.text for x in c.findall('rdfs:label', ns)]
        if any(any(w in (l or '').lower() for w in ('fluid', 'frequency')) for l in labels):
            selected.append(ET.tostring(c, encoding='unicode'))
    (OUT / 'b_opb_excerpt.json').write_text(json.dumps({'provenance': provenance, 'retrieval_note': 'Official SemBioProcess/SemGen bundled OPB v1.07; bounded selected class XML, not whole ontology.', 'class_xml': selected}, indent=2))
    print('\n'.join(selected)[:18000])
