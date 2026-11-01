"""Translate the SemSim RDF embedded in PMR workspace 267 (docs/evidence/a_smith_2004.cellml)
into the OMEX metadata v1.2 form so it can be validated by the shapes in this folder.

Mechanical rules (each is a vocabulary rename or a structural collapse, never a correction):
  property node  semsim:hasPhysicalDefinition X  ->  variable bqbiol:isVersionOf norm(X)
  property node  semsim:physicalPropertyOf B     ->  variable bqbiol:isPropertyOf B'
  entity node    semsim:hasPhysicalDefinition Y  ->  B' bqbiol:is norm(Y)
  entity node    ro:part_of Z                    ->  B' bqbiol:isPartOf norm(definition of Z)
  process node   semsim:has{Source,Sink,Mediator}Participant, hasPhysicalEntityReference,
                 hasMultiplier                   ->  same local names in the OMEX v1.2 SemSim namespace
  process node   semsim:name                     ->  dc:description
  variable       semsim:hasPhysicalDefinition X  ->  variable bqbiol:is norm(X)   (only 'time')
  variable       dcterms:description             ->  kept (OMEX's dc: prefix is purl.org/dc/terms/)
Copies of one CellML variable joined by <connection>/<map_variables> are merged into one subject;
each original RDF subject is kept as prov:wasDerivedFrom. Local nodes are named by their content,
so identical annotations on different copies collapse and genuinely different ones stay distinct.
Identifier normalisation follows OMEX v1.2 §2.1 (https://identifiers.org/opb:OPB_nnnnn) and the node
specification v2 (../anatomy_nodes_v2.md): an FMA identifier is rewritten to the Uberon identifier only
when that Uberon term carries the same FMA cross-reference (docs/evidence/d_uberon_fma_map.json), which is
an equivalence, not a correction; every other FMA identifier, including the v1 vessel lumens, is kept as
https://identifiers.org/FMA:nnnn. Defects in the source annotation are preserved on purpose.

Usage: python -I translate_ws267.py <a_smith_2004.cellml> <output.ttl> [<d_uberon_fma_map.json>]
"""
import json
import pathlib
import re
import sys
import xml.etree.ElementTree as ET

import rdflib
from rdflib import Namespace, URIRef, Literal
from rdflib.namespace import RDF

C = None  # CellML namespace, read from the root element (workspace 267 is CellML 1.1)
CMETA = '{http://www.cellml.org/metadata/1.0#}id'
OLD = Namespace('http://www.bhi.washington.edu/SemSim#')
RO = Namespace('http://www.obofoundry.org/ro/ro.owl#')
DCT = Namespace('http://purl.org/dc/terms/')
BQBIOL = Namespace('http://biomodels.net/biology-qualifiers/')
SEMSIM = Namespace('http://bime.uw.edu/semsim/')
PROV = Namespace('http://www.w3.org/ns/prov#')
MODEL = Namespace('http://omex-library.org/smith2004_ws267.omex/Smith_2004.cellml#')
LOCAL = Namespace('http://omex-library.org/smith2004_ws267.omex/Smith_2004.rdf#')
SRC = 'https://models.physiomeproject.org/workspace/267/rawfile/6ae217019bf59fc1e22e2dc5235751c6fcf6be24/Smith_2004.cellml#'


FMA_TO_UBERON = {}  # filled in main() from the retained Uberon-FMA mapping


def norm(uri):
    s = str(uri)
    m = re.search(r'OPB_(\d+)$', s)
    if m:
        return URIRef('https://identifiers.org/opb:OPB_' + m.group(1))
    m = re.search(r'FMA_(\d+)$', s)
    if m:
        fma = 'FMA:' + m.group(1)
        if fma in FMA_TO_UBERON:
            return URIRef('https://identifiers.org/' + FMA_TO_UBERON[fma])
        return URIRef('https://identifiers.org/' + fma)
    return URIRef(s)


def short(uri):
    return re.sub(r'[^A-Za-z0-9]+', '', str(uri).rsplit('/', 1)[-1])


def main(cellml_path, out_path, map_path=None):
    global C
    map_path = pathlib.Path(map_path) if map_path else pathlib.Path(__file__).resolve().parents[2] / 'evidence' / 'd_uberon_fma_map.json'
    for r in json.loads(map_path.read_text())['results']:
        if r.get('match'):
            FMA_TO_UBERON[r['fma']] = r['match']['uberon']
    text = open(cellml_path, encoding='utf-8').read()
    root = ET.fromstring(text)
    C = root.tag.split('}')[0] + '}'
    if root.tag != C + 'model':
        raise SystemExit(f'unexpected root element {root.tag}')
    # cmeta:id -> (component, variable); connected variables -> union-find classes
    by_cmeta, parent = {}, {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for comp in root.findall(C + 'component'):
        for v in comp.findall(C + 'variable'):
            key = (comp.get('name'), v.get('name'))
            find(key)
            if v.get(CMETA):
                by_cmeta[v.get(CMETA)] = key
    for con in root.findall(C + 'connection'):
        mc = con.find(C + 'map_components')
        for mv in con.findall(C + 'map_variables'):
            a = (mc.get('component_1'), mv.get('variable_1'))
            b = (mc.get('component_2'), mv.get('variable_2'))
            parent[find(a)] = find(b)
    classes = {}
    for key in list(parent):
        classes.setdefault(find(key), set()).add(key)
    class_name = {}
    for rep, members in classes.items():
        names = {m[1] for m in members}
        if len(names) != 1:
            raise SystemExit(f'connected variables with different names: {sorted(members)}')
        class_name[rep] = names.pop()
    if len(set(class_name.values())) != len(class_name):
        raise SystemExit('two unconnected CellML variables share a name; naming scheme would merge them')

    rdf_text = re.search(r'<rdf:RDF.*?</rdf:RDF>', text, re.S).group(0)
    rdf_text = rdf_text.replace('<rdf:RDF ', '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" '
                                'xmlns:semsim="http://www.bhi.washington.edu/SemSim#" '
                                'xmlns:dcterms="http://purl.org/dc/terms/" xmlns:cmeta="http://www.cellml.org/metadata/1.0#" '
                                'xmlns:vCard="http://www.w3.org/2001/vcard-rdf/3.0#" ', 1)
    src = rdflib.Graph()
    src.parse(data=rdf_text, format='xml', publicID=SRC)

    def subject_key(s):
        frag = str(s).split('#', 1)[-1]
        if frag in by_cmeta:
            return by_cmeta[frag]
        if '.' in frag:
            comp, var = frag.split('.', 1)
            if (comp, var) in parent:
                return (comp, var)
        return None

    out = rdflib.Graph(bind_namespaces='none')
    for prefix, ns in (('bqbiol', BQBIOL), ('semsim', SEMSIM), ('dc', DCT), ('prov', PROV),
                       ('OMEXmodel', MODEL), ('local', LOCAL),
                       ('opb', Namespace('https://identifiers.org/opb:')),
                       ('fma', Namespace('https://identifiers.org/FMA:')),
                       ('uberon', Namespace('https://identifiers.org/UBERON:'))):
        out.bind(prefix, ns, override=True, replace=True)

    def entity(node):
        """Translate an entity node; return (content-named local IRI, short key)."""
        defs = sorted(norm(o) for o in src.objects(node, OLD.hasPhysicalDefinition))
        parts = []
        for z in src.objects(node, RO.part_of):
            parts += [norm(o) for o in src.objects(z, OLD.hasPhysicalDefinition)]
        name = '_'.join(short(d) for d in defs) or 'custom'
        if parts:
            name += '_in_' + '_'.join(short(p) for p in sorted(parts))
        iri = LOCAL['entity_' + name]
        for d in defs:
            out.add((iri, BQBIOL['is'], d))
        for p in parts:
            out.add((iri, BQBIOL.isPartOf, p))
        return iri, name

    def bearer(node):
        """Translate the bearer of a property (entity, or process/energy differential)."""
        roles = [(OLD.hasSourceParticipant, 'src'), (OLD.hasSinkParticipant, 'snk'), (OLD.hasMediatorParticipant, 'med')]
        if any(True for r, _ in roles for _o in src.objects(node, r)):
            parts = []
            for pred, tag in roles:
                for part in src.objects(node, pred):
                    ents = [entity(e) for e in src.objects(part, OLD.hasPhysicalEntityReference)]  # (iri, key)
                    mult = list(src.objects(part, OLD.hasMultiplier))
                    parts.append((pred, tag, ents, mult))
            name = '__'.join(f"{tag}_{'+'.join(k for _, k in ents)}" for _, tag, ents, _ in sorted(parts, key=lambda x: x[1]))
            iri = LOCAL['process_' + name]
            processed.add(node)
            for nm in src.objects(node, OLD.name):
                out.add((iri, DCT.description, Literal(str(nm))))
            for desc in src.objects(node, DCT.description):
                out.add((iri, DCT.description, desc))
            for pred, tag, ents, mult in parts:
                piri = LOCAL[f"{tag}_of_{name}"]
                out.add((iri, SEMSIM[pred.split('#')[-1]], piri))
                for e, _k in ents:
                    out.add((piri, SEMSIM.hasPhysicalEntityReference, e))
                for m in mult:
                    out.add((piri, SEMSIM.hasMultiplier, m))
            return iri
        return entity(node)[0]

    processed = set()
    stats = {'subjects': 0, 'unmapped': []}
    for s in set(src.subjects()):
        key = subject_key(s)
        if key is None:
            continue
        stats['subjects'] += 1
        var = MODEL[class_name[find(key)]]
        out.add((var, PROV.wasDerivedFrom, s))
        for desc in src.objects(s, DCT.description):
            out.add((var, DCT.description, desc))
        for d in src.objects(s, OLD.hasPhysicalDefinition):
            out.add((var, BQBIOL['is'], norm(d)))
        for prop in src.objects(s, OLD.isComputationalComponentFor):
            for d in src.objects(prop, OLD.hasPhysicalDefinition):
                out.add((var, BQBIOL.isVersionOf, norm(d)))
            for b in src.objects(prop, OLD.physicalPropertyOf):
                out.add((var, BQBIOL.isPropertyOf, bearer(b)))
    for s in set(src.subjects()):
        if str(s).startswith(SRC) and subject_key(s) is None and s not in processed and (s, DCT.description, None) in src:
            stats['unmapped'].append(str(s))
    header = ('# Generated by translate_ws267.py from docs/evidence/a_smith_2004.cellml (PMR workspace 267,\n'
              '# CC BY 3.0 Unported; SemSim annotation by Chris Thompson). Vocabulary translated to OMEX\n'
              '# metadata v1.2 form; FMA identifiers with an exact Uberon equivalent (same FMA xref) written as\n'
              '# Uberon per node specification v2; content unchanged, defects preserved. See the module docstring.\n'
              f"# Source RDF subjects mapped to CellML variables: {stats['subjects']}; unmapped described subjects: {len(stats['unmapped'])}\n")
    open(out_path, 'w', encoding='utf-8').write(header + out.serialize(format='turtle'))
    print(f"subjects mapped {stats['subjects']}, variables {len(set(out.subjects(PROV.wasDerivedFrom, None)))}, "
          f"triples {len(out)}, unmapped described subjects {stats['unmapped']}")


if __name__ == '__main__':
    main(*sys.argv[1:4])
