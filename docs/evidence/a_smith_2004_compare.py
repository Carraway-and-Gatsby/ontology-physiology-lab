"""Static comparison of the two retained Smith 2004 CellML captures; nothing is simulated."""
from collections import Counter
from pathlib import Path
import hashlib
import json
import xml.etree.ElementTree as ET

here = Path(__file__).parent
captures = {
    'workspace_267': here / 'a_smith_2004.cellml',
    'canonical': here / 'a_smith_2004_canonical.cellml',
}


def local(tag):
    return tag.split('}', 1)[-1]


def attr(e, name):
    return next((v for k, v in e.attrib.items() if local(k) == name), None)


def mathml(e):
    # Text form of one MathML subtree; keeps cn values/units, drops ids and whitespace.
    t = local(e.tag)
    if t == 'ci':
        return e.text.strip()
    if t == 'cn':
        parts = [p.strip() for p in e.itertext() if p.strip()]
        value = float('e'.join(parts)) if attr(e, 'type') == 'e-notation' else float(parts[0])
        return '%r[%s]' % (value, attr(e, 'units'))
    kids = list(e)
    if t == 'apply':
        return '%s(%s)' % (local(kids[0].tag), ', '.join(mathml(k) for k in kids[1:]))
    return '%s{%s}' % (t, '; '.join(mathml(k) for k in kids)) if kids else t


def load(path):
    root = ET.parse(path).getroot()
    model = {'namespace': root.tag[1:].split('}')[0], 'components': {}, 'connections': set()}
    for c in (x for x in root if local(x.tag) == 'component'):
        variables = {attr(v, 'name'): {k: attr(v, k) for k in ('units', 'initial_value', 'public_interface', 'private_interface')}
                     for v in c if local(v.tag) == 'variable'}
        equations, defined = [], set()
        for eq in (a for m in c if local(m.tag) == 'math' for a in m if local(a.tag) == 'apply'):
            equations.append(mathml(eq))
            lhs = list(eq)[1]
            if local(lhs.tag) == 'ci':
                defined.add(lhs.text.strip())
            elif local(lhs.tag) == 'apply' and local(list(lhs)[0].tag) == 'diff':
                defined.update(x.text.strip() for x in lhs if local(x.tag) == 'ci')
        model['components'][attr(c, 'name')] = {'variables': variables, 'equations': equations, 'defined': defined}
    for cn in (x for x in root if local(x.tag) == 'connection'):
        mc = next(x for x in cn if local(x.tag) == 'map_components')
        for mv in (x for x in cn if local(x.tag) == 'map_variables'):
            pair = sorted([(attr(mc, 'component_1'), attr(mv, 'variable_1')), (attr(mc, 'component_2'), attr(mv, 'variable_2'))])
            model['connections'].add(tuple(map(tuple, pair)))
    return model


def unvalued(model):
    # Owned variables with neither an initial_value nor a defining equation.
    return sorted('%s.%s' % (c, n) for c, comp in model['components'].items() for n, v in comp['variables'].items()
                  if 'in' not in (v['public_interface'], v['private_interface'])
                  and v['initial_value'] is None and n not in comp['defined'])


models = {k: load(p) for k, p in captures.items()}
a, b = models['workspace_267'], models['canonical']
common = sorted(set(a['components']) & set(b['components']))
value_only = []
for c in common:
    va, vb = a['components'][c]['variables'], b['components'][c]['variables']
    for n in sorted(set(va) | set(vb)):
        if va.get(n) != vb.get(n):
            strip = lambda v: {k: x for k, x in (v or {}).items() if k != 'initial_value'}
            assert strip(va.get(n)) == strip(vb.get(n)), (c, n)
            value_only.append({'variable': '%s.%s' % (c, n), 'workspace_267': va[n]['initial_value'], 'canonical': vb[n]['initial_value']})
states = sorted({x['variable'] for x in value_only}
                & {'%s.%s' % (c, n) for c in common for n in b['components'][c]['defined']})
report = {
    'scope': 'Static structural comparison of two retained CellML captures; neither file was simulated',
    'files': {k: {'path': p.name, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'namespace': models[k]['namespace']}
              for k, p in captures.items()},
    'components': {k: len(m['components']) for k, m in models.items()},
    'common_components': len(common),
    'equations': {k: sum(len(c['equations']) for c in m['components'].values()) for k, m in models.items()},
    'equation_sets_identical': all(Counter(a['components'][c]['equations']) == Counter(b['components'][c]['equations']) for c in common),
    'connections': {k: len(m['connections']) for k, m in models.items()},
    'connections_identical': a['connections'] == b['connections'],
    'variables_differing_only_in_initial_value': len(value_only),
    'missing_initial_values_in_workspace_267': {
        'state_initial_conditions': states,
        'parameters': sorted({x['variable'] for x in value_only} - set(states)),
    },
    'unvalued_without_defining_equation': {k: unvalued(m) for k, m in models.items()},
    'initial_value_differences': value_only,
}
path = Path(__file__).with_name('a_smith_2004_compare.json')
path.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: v for k, v in report.items() if k != 'initial_value_differences'}, indent=2))
