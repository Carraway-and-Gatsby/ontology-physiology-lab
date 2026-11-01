"""Check local PROV traceability with stdlib and rdflib; never execute evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef, XSD


PROV = Namespace('http://www.w3.org/ns/prov#')
META = Namespace('urn:smith2004:prov:')
CELLML_NAME = 'smith_chase_nokes_shaw_wake_2004.cellml'
ARCHIVE_NAME = 'OpenCOR-0-8-3-Linux.tar.gz'
ALLOWED_URIS = (
    str(PROV), str(META), str(RDF), str(RDFS), str(XSD),
)
RECOMMENDATION = 'https://www.w3.org/TR/2013/REC-prov-o-20130430/'


class Checks:
    def __init__(self):
        self.failed = 0
        self.matched = 0
        self.skipped = 0

    def report(self, check, ok, detail=''):
        if not ok:
            self.failed += 1
        print(json.dumps({'check': check, 'status': 'OK' if ok else 'FAIL',
                          'detail': detail}, sort_keys=True))

    def finish(self, code=None):
        print(json.dumps({'summary': {'failed': self.failed,
                                      'matched': self.matched,
                                      'skipped': self.skipped}}, sort_keys=True))
        return code if code is not None else int(self.failed != 0)


def plain(value):
    return (isinstance(value, Literal) and value.datatype is None
            and value.language is None)


def check_metadata(graph, checks):
    """Validate metadata before checking existence, including malformed absent files."""
    nodes = set()
    for predicate in (META.serverPath, META.sha256, META.byteSize):
        nodes.update(graph.subjects(predicate, None))
    checks.report('file-records', bool(nodes), f'{len(nodes)} records')
    paths = {}
    for node in sorted(nodes, key=str):
        path_values = list(graph.objects(node, META.serverPath))
        hashes = list(graph.objects(node, META.sha256))
        sizes = list(graph.objects(node, META.byteSize))
        is_entity = (node, RDF.type, PROV.Entity) in graph
        path_ok = (len(path_values) == 1 and plain(path_values[0])
                   and str(path_values[0]).startswith('/')
                   and not str(path_values[0]).startswith('//')
                   and '\x00' not in str(path_values[0]))
        hash_ok = (len(hashes) == 1 and plain(hashes[0])
                   and re.fullmatch(r'[0-9a-f]{64}', str(hashes[0])) is not None)
        size_ok = (len(sizes) == 1 and isinstance(sizes[0], Literal)
                   and sizes[0].datatype == XSD.integer
                   and isinstance(sizes[0].toPython(), int)
                   and not isinstance(sizes[0].toPython(), bool)
                   and sizes[0].toPython() >= 0)
        checks.report('file-metadata', is_entity and path_ok and hash_ok and size_ok,
                      f'{node}: Entity={is_entity}, path={path_ok}, sha256={hash_ok}, byteSize={size_ok}')
        # Retain valid paths for relation checks even if their hashes are malformed.
        if path_ok:
            paths[node] = Path(str(path_values[0]))
        if not (is_entity and path_ok and hash_ok and size_ok):
            continue
        path = paths[node]
        try:
            with path.open('rb') as stream:
                digest = hashlib.sha256()
                size = 0
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(block)
                    size += len(block)
        except FileNotFoundError:
            checks.skipped += 1
            print(json.dumps({'check': 'file-content', 'status': 'SKIP',
                              'node': str(node), 'detail': 'missing file'}, sort_keys=True))
            continue
        except OSError as exc:
            checks.report('file-content', False, f'{node}: {type(exc).__name__}')
            continue
        matches = digest.hexdigest() == str(hashes[0]) and size == int(sizes[0])
        checks.report('file-content', matches,
                      f'{node}: sha256={digest.hexdigest()}, byteSize={size}')
        if matches:
            checks.matched += 1
    return paths


def check_relations(graph, paths, checks):
    entities = set(graph.subjects(RDF.type, PROV.Entity))
    csvs = {node for node, path in paths.items() if path.suffix.lower() == '.csv'}
    csvs.update(node for node in entities if str(node).lower().endswith('.csv'))
    csvs.update(node for node in entities
                if any(str(label).lower().endswith('.csv')
                       for label in graph.objects(node, RDFS.label)))
    checks.report('csv-records', bool(csvs), f'{len(csvs)} CSV Entities')
    rk4 = set()
    for node in sorted(csvs, key=str):
        generators = list(graph.objects(node, PROV.wasGeneratedBy))
        checks.report('csv-generator-cardinality', len(generators) == 1,
                      f'{node}: {len(generators)} generators')
        for generator in generators:
            checks.report('csv-generator-activity',
                          (generator, RDF.type, PROV.Activity) in graph, str(generator))
    # Check every RK4 Activity, even one with no CSV. CSV generators are not all
    # assumed to be RK4: a comparison may itself generate additional CSV Entities.
    for node in graph.subjects(RDF.type, PROV.Activity):
        methods = list(graph.objects(node, META.integrationMethod))
        labels = list(graph.objects(node, RDFS.label))
        if (any(str(value).upper() == 'RK4' for value in methods)
                or any(re.search(r'\bRK4\b', str(label), re.I) for label in labels)
                or list(graph.objects(node, META.stepSeconds))):
            rk4.add(node)
    cells = {node for node, path in paths.items() if path.name == CELLML_NAME}
    archives = {node for node, path in paths.items() if path.name == ARCHIVE_NAME}
    checks.report('canonical-input-records', len(cells) == 1 and len(archives) == 1,
                  f'CellML={len(cells)}, OpenCOR={len(archives)}')
    checks.report('rk4-records', bool(rk4), f'{len(rk4)} RK4 Activities')
    for activity in sorted(rk4, key=str):
        uses = set(graph.objects(activity, PROV.used))
        checks.report('rk4-used-cellml', len(cells) == 1 and cells <= uses, str(activity))
        checks.report('rk4-used-opencor', len(archives) == 1 and archives <= uses, str(activity))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ttl', type=Path,
                        default=Path(__file__).with_name('smith2004_opencor_runs.ttl'))
    args = parser.parse_args(argv)
    checks = Checks()
    try:
        text = args.ttl.read_text(encoding='utf-8')
    except (OSError, UnicodeError) as exc:
        checks.report('ttl-read', False, type(exc).__name__)
        return checks.finish(2)
    checks.report('privacy-at-sign', '@' not in text)
    checks.report('privacy-ipv4', re.search(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', text) is None)
    graph = Graph()
    try:
        # Parse local text only; no URL retrieval, imports or reasoning.
        graph.parse(data=text, format='turtle')
    except Exception as exc:
        checks.report('ttl-parse', False, type(exc).__name__)
        return checks.finish(2)
    checks.report('ttl-parse', True, f'{len(graph)} triples')
    forbidden_uris = {str(term) for triple in graph for term in triple
                      if isinstance(term, URIRef)
                      and not str(term).startswith(ALLOWED_URIS)
                      and str(term) != RECOMMENDATION}
    literal_urls = {url for triple in graph for term in triple if isinstance(term, Literal)
                    for url in re.findall(r'(?:https?|ftp|ssh|file)://[^\s<>"\']+', str(term))
                    if url != RECOMMENDATION and not url.startswith(ALLOWED_URIS[:1])}
    checks.report('privacy-uri-allowlist', not forbidden_uris and not literal_urls,
                  f'{len(forbidden_uris)} forbidden identifiers, {len(literal_urls)} forbidden literal URLs')
    for person in graph.subjects(RDF.type, PROV.Person):
        checks.report('privacy-person-label',
                      list(graph.objects(person, RDFS.label)) == [Literal('project owner')],
                      str(person))
    paths = check_metadata(graph, checks)
    check_relations(graph, paths, checks)
    return checks.finish()


if __name__ == '__main__':
    sys.exit(main())
