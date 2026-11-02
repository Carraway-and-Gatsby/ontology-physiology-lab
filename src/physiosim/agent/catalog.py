"""Numeric parameter ports generated from the real dataclasses and offline IDs.

Dotted volume ports expose individual tuple entries without changing engine code.
"""
from dataclasses import asdict, fields, replace
from functools import lru_cache
import json
import math
from pathlib import Path

from physiosim.models.cardiovascular import Parameters, COMPARTMENTS as P1_COMPARTMENTS
from physiosim.models.four_chamber_m1 import FourChamberM1Parameters, COMPARTMENTS as M1_COMPARTMENTS

MODELS = ('phase1', 'm1')
COMPARTMENTS = {'phase1': P1_COMPARTMENTS, 'm1': M1_COMPARTMENTS}


def synthetic_fixture():
    """Lightweight equivalent of the demo fixture (equality tested against it).

    The demo imports pint/rdflib through its manifest, so cannot run in Pyodide.
    New atrial/inflow values are synthetic test choices, never literature values.
    """
    values = asdict(Parameters())
    values.update(elastance_la=.15, elastance_ra=.10,
                  resistance_venous_return=.05, resistance_pulmonary_venous=.05,
                  unstressed_volumes=(10., 700., 2500., 20., 10., 100., 400., 20.),
                  initial_volumes=(140., 850., 3200., 60., 140., 180., 490., 60.))
    return FourChamberM1Parameters(**values)


def default_parameters(model):
    if model not in MODELS:
        raise ValueError('model must be phase1 or m1')
    return Parameters() if model == 'phase1' else synthetic_fixture()


@lru_cache(maxsize=1)
def knowledge():
    # Path access avoids executing physiosim.ontology.__init__ (rdflib/pint).
    return json.loads(Path(__file__).with_name('knowledge.json').read_text(encoding='utf-8'))


def iri(curie):
    """Expand Uberon; return an FMA IRI only when the source records it."""
    if curie.startswith('FMA:'):
        return next((x['record']['base_iri'] for x in knowledge()['source']['catalog']
                     if x['record']['base_id'] == curie), None)
    return 'http://purl.obolibrary.org/obo/' + curie.replace(':', '_')


def known_ids():
    ids = set()
    for n in knowledge()['anatomy']['nodes']:
        for key in ('uberon', 'fma'):
            if n.get(key):
                ids.add(n[key])
                if iri(n[key]):
                    ids.add(iri(n[key]))
    for x in knowledge()['source']['catalog']:
        r = x['record']
        ids.update((r['base_id'], r['base_iri']))
    for x in knowledge()['source']['claims']:
        ids.add(x['record']['relation'])
    return ids


def _binding(model, name):
    base, _, component = name.partition('.')
    key = None
    relation = 'parameter_context'
    if component:
        key = component + '_cavity' if component in ('lv', 'rv', 'la', 'ra') else {
            'sa': 'systemic_arterial_lumen', 'sv': 'systemic_venous_lumen',
            'pa': 'pulmonary_arterial_lumen', 'pv': 'pulmonary_venous_lumen'}[component]
        relation = 'blood_contained_in' if component in ('lv', 'rv', 'la', 'ra') else 'lumped_compartment_context'
    elif name == 'heart_rate':
        key = 'heart'
    elif name.startswith(('emin_', 'emax_')):
        # Legacy registry explicitly binds E to ventricular organ, not cavity/wall.
        key = name.rsplit('_', 1)[1]
    elif name.startswith('elastance_'):
        key = name.rsplit('_', 1)[1] + '_cavity'
        relation = 'chamber_context_not_selected_mechanical_bearer'
    elif name.startswith('compliance_'):
        component = name.rsplit('_', 1)[1]
        key = {'sa': 'systemic_arterial_lumen', 'sv': 'systemic_venous_lumen',
               'pa': 'pulmonary_arterial_lumen', 'pv': 'pulmonary_venous_lumen'}[component]
        relation = 'lumped_compartment_context'
    elif name.startswith('resistance_'):
        key = {'aortic': 'aortic_valve', 'mitral': 'mitral_valve',
               'tricuspid': 'tricuspid_valve', 'pulmonary_valve': 'pulmonary_valve'}.get(name[11:])
        relation = 'flow_location'
    # Phase1 peripheral compartments are explicitly project-local in the registry.
    if model == 'phase1' and component in ('sa', 'sv', 'pa', 'pv'):
        return None
    if key is None:
        return None
    for i, node in enumerate(knowledge()['anatomy']['nodes']):
        if node['key'] == key:
            ids = [{'id': node[k], 'iri': iri(node[k]), 'label': node.get(k+'_label', node['structure']),
                    'relation': 'related_structure' if k == 'uberon' and node['primary'] != 'UBERON' else 'source_v2_identifier'}
                   for k in ('uberon', 'fma') if node.get(k)]
            return {'key': key, 'label': node['structure'], 'relation': relation, 'ids': ids,
                    'primary_id': node['uberon'] if node['primary'] == 'UBERON' else node['fma'],
                    'source': 'src/physiosim/ontology/anatomy_nodes_v2.json#/nodes/'+str(i),
                    'scope': 'Existing project anatomical context; no identity, calibration or external revalidation asserted.'}
    return None


def catalogue(model):
    p = default_parameters(model)
    entries = []
    for field in fields(p):
        base = field.name
        value = getattr(p, base)
        ports = [(base+'.'+c, float(v)) for c, v in zip(COMPARTMENTS[model], value)] if base.endswith('volumes') else [(base, float(value))]
        for name, default in ports:
            lower, upper = default * .1, default * 5
            if base == 'systolic_fraction':
                upper = min(upper, .95)
            if base.startswith('emin_'):
                upper = min(upper, getattr(p, 'emax_'+base[-2:]))
            if base.startswith('emax_'):
                lower = max(lower, getattr(p, 'emin_'+base[-2:]))
            # Validate both endpoints with engine validators as well as combined runs.
            unit = ('mL' if base.endswith('volumes') else 'mmHg*s/mL' if base.startswith('resistance_')
                    else 'mL/mmHg' if base.startswith('compliance_') else 'beat/min' if base == 'heart_rate'
                    else 'dimensionless' if base == 'systolic_fraction' else 'mmHg/mL')
            if base.endswith('volumes'):
                description = ('Initial total blood volume' if base == 'initial_volumes' else 'Unstressed reference volume') + ' in '+name.split('.')[1]+'.'
            elif base.startswith('resistance_'):
                description = 'Resistance of the '+base[11:].replace('_', ' ')+' flow path; not valve area or drug effect.'
            elif base.startswith('compliance_'):
                description = 'Linear reservoir compliance in '+base[11:]+'.'
            elif base.startswith(('emax_', 'emin_')):
                description = ('Peak' if base.startswith('emax') else 'Passive minimum')+' elastance of '+base[-2:]+'.'
            elif base.startswith('elastance_'):
                description = 'Constant passive atrial elastance of '+base[-2:]+'.'
            else:
                description = {'heart_rate': 'Imposed pacing rate; no reflex regulation.',
                               'systolic_fraction': 'Synchronous ventricular activation pulse width as a fraction of the cycle.'}[base]
            binding = _binding(model, name)
            entries.append({'name': name, 'models': [model], 'unit': unit, 'default': default,
                            'allowed': [lower, upper], 'description': description, 'binding': binding,
                            'binding_note': None if binding else 'No anatomical ontology binding in the existing model contract; project-local parameter/context.',
                            'default_provenance': 'Parameters() exploratory default' if model == 'phase1' else 'synthetic_fixture() explicit synthetic test input'})
    return entries


def flatten(parameters, model):
    result = {}
    for field, value in asdict(parameters).items():
        if field.endswith('volumes'):
            result.update({field+'.'+c: float(v) for c, v in zip(COMPARTMENTS[model], value)})
        else:
            result[field] = float(value)
    return result


def apply_values(parameters, model, overrides, *, allow_scale):
    if not isinstance(overrides, dict):
        raise ValueError('parameter overrides must be an object')
    ports = {x['name']: x for x in catalogue(model)}
    flat = flatten(parameters, model)
    original = dict(flat)
    for name, spec in overrides.items():
        if name not in ports:
            raise ValueError('unknown parameter: '+str(name))
        if isinstance(spec, dict):
            if not allow_scale or set(spec) != {'scale'}:
                raise ValueError('only intervention {"scale": finite positive number} is supported')
            factor = spec['scale']
            if isinstance(factor, bool) or not isinstance(factor, (int, float)) or not math.isfinite(factor) or factor <= 0:
                raise ValueError('scale must be a finite positive number')
            value = flat[name] * factor
        else:
            value = spec
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError('parameter must be a finite real number: '+name)
        lo, hi = ports[name]['allowed']
        if not lo <= value <= hi:
            raise ValueError(f'{name} outside conservative range [{lo}, {hi}]')
        flat[name] = float(value)
    values = asdict(parameters)
    for name, value in flat.items():
        base, dot, c = name.partition('.')
        if dot:
            v = list(values[base]); v[COMPARTMENTS[model].index(c)] = value; values[base] = tuple(v)
        else:
            values[base] = value
    updated = replace(parameters, **values)  # rechecks coupled Emax/Emin constraints
    changes = [{'parameter': name, 'baseline': original[name], 'intervention': flat[name]} for name in sorted(overrides)]
    return updated, changes
