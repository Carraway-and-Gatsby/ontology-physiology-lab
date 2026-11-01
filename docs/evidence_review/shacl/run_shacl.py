"""Validate Smith 2004 annotations with the SHACL shapes in this folder.

1. Checks every entry of smith2004_dependencies.ttl against the equations in
   ../smith2004_variable_dictionary.json (flow sign and capacitive chain).
2. Runs the three control fixtures and requires exactly the results in expected_results.json.
3. Validates ws267_omex_form.ttl (the translated SemSim annotation of PMR workspace 267) and writes
   report_ws267.json and report_ws267.md. Non-conformance of ws267 is a finding, not a failure.

Exit status: 0 when the dependency check and all controls pass; 1 otherwise.
Usage: python -I run_shacl.py   (environment: requirements-shacl.txt)
"""
import hashlib
import json
import pathlib
import platform
import re
import sys

import pyshacl
import rdflib
from rdflib import Namespace, URIRef
from rdflib.namespace import RDF

HERE = pathlib.Path(__file__).resolve().parent
SH = Namespace('http://www.w3.org/ns/shacl#')
DEP = Namespace('https://example.org/physiosim/dependency#')


def load(*names):
    g = rdflib.Graph()
    for n in names:
        g.parse(HERE / n)
    return g


def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def check_dependencies():
    d = json.loads((HERE.parent / 'smith2004_variable_dictionary.json').read_text())
    eqs = {e['id']: e for e in d['equations']}
    defines = {e['defines']: e for e in d['equations']}
    g = load('smith2004_dependencies.ttl')
    name = lambda u: str(u).rsplit('#', 1)[-1]
    problems = []

    def closure(var, seen=None):
        seen = set() if seen is None else seen
        e = defines.get(var)
        if not e or var in seen:
            return seen
        seen.add(var)
        for u in e['uses']:
            closure(u, seen)
            seen.add(u)
        return seen

    for dep in set(g.subjects(DEP.equation, None)):
        ids = [s.strip() for s in str(g.value(dep, DEP.equation)).split(',')]
        missing = [i for i in ids if i not in eqs]
        if missing:
            problems.append(f'{name(dep)}: unknown equation ids {missing}')
            continue
        if (dep, DEP.flow, None) in g:
            q, up, down = (name(g.value(dep, p)) for p in (DEP.flow, DEP.upstreamPressure, DEP.downstreamPressure))
            e = eqs[ids[0]]
            if e['defines'] != q or f'({up} - {down})' not in e['infix']:
                problems.append(f'{name(dep)}: {ids[0]} does not define {q} from ({up} - {down})')
        else:
            p, v = name(g.value(dep, DEP.pressure)), name(g.value(dep, DEP.amount))
            reach = closure(p)
            if v not in reach:
                problems.append(f'{name(dep)}: {v} is not reachable from {p} through the equations')
            off_path = [i for i in ids if eqs[i]['defines'] not in reach]
            if off_path:
                problems.append(f'{name(dep)}: equations {off_path} are not on the path from {p} to {v}')
    return problems


def validate(data_files, shape_files, with_deps):
    data = load(*data_files, *(['smith2004_dependencies.ttl'] if with_deps else []))
    shapes = load(*shape_files)
    conforms, report, _ = pyshacl.validate(data, shacl_graph=shapes, inference='none',
                                           allow_warnings=True, allow_infos=True, abort_on_first=False)
    rows = []
    nested = set(report.objects(None, SH.detail))  # sh:detail results belong to their parent (e.g. G6 -> FluidPortion)
    for r in report.subjects(RDF.type, SH.ValidationResult):
        if r in nested:
            continue
        msg = str(report.value(r, SH.resultMessage) or '')
        rows.append({
            'focus': str(report.value(r, SH.focusNode)),
            'code': msg.split(':', 1)[0] if re.match(r'^[GS]\d+[ab]?:', msg) else 'UNCODED',
            'severity': str(report.value(r, SH.resultSeverity)).rsplit('#', 1)[-1],
            'message': msg,
            'value': str(report.value(r, SH.value)) if report.value(r, SH.value) is not None else None,
        })
    rows.sort(key=lambda x: (x['code'], x['focus']))
    return conforms, rows


def main():
    ok = True
    problems = check_dependencies()
    print('dependency check:', 'ok' if not problems else problems)
    ok &= not problems

    expected = json.loads((HERE / 'expected_results.json').read_text())
    for fixture in ('conforming', 'generic_violations', 'smith_violations'):
        spec = expected[fixture]
        _, rows = validate([f'fixtures/{fixture}.ttl'], spec['shapes'], spec['with_dependencies'])
        got = sorted((r['focus'], r['code'], r['severity']) for r in rows)
        want = sorted(tuple(x) for x in spec['results'])
        same = got == want
        ok &= same
        print(f'control {fixture}: {"pass" if same else "FAIL"} ({len(got)} results, expected {len(want)})')
        if not same:
            print('  unexpected:', sorted(set(got) - set(want)))
            print('  missing:   ', sorted(set(want) - set(got)))

    conforms, rows = validate(['ws267_omex_form.ttl'], ['shapes_omex_v1_2.ttl', 'shapes_smith2004.ttl'], True)
    counts = {}
    for r in rows:
        counts.setdefault(r['code'], {}).setdefault(r['severity'], 0)
        counts[r['code']][r['severity']] += 1
    files = ['shapes_omex_v1_2.ttl', 'shapes_smith2004.ttl', 'smith2004_dependencies.ttl', 'ws267_omex_form.ttl',
             'expected_results.json', 'fixtures/conforming.ttl', 'fixtures/generic_violations.ttl', 'fixtures/smith_violations.ttl']
    out = {
        'data': 'ws267_omex_form.ttl (translated from docs/evidence/a_smith_2004.cellml)',
        'conforms': conforms, 'controls_pass': bool(ok), 'counts_by_rule': counts, 'results': rows,
        'environment': {'python': platform.python_version(), 'pyshacl': pyshacl.__version__, 'rdflib': rdflib.__version__},
        'sha256': {f: sha(HERE / f) for f in files},
    }
    (HERE / 'report_ws267.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n')
    print(f'ws267: conforms={conforms}; results by rule: {json.dumps(counts, sort_keys=True)}')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
