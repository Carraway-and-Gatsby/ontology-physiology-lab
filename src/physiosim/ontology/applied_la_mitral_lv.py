"""Metadata-only LA–mitral–LV sidecar; external numerical use stays closed."""
from hashlib import sha256
import json
from pathlib import Path

SOURCE_COMMIT = '70784bcdb9c14fba5271ee73f3c62b5f94ccbcfb'
PINNED_FULL_FILES = {'experiments/medmlx_anatomy_mapping/results/contents_catalog.json': '288cadbe573f8a5488abc135560a66a3c793f48e32984228a7a791cbdcce24da', 'experiments/medmlx_anatomy_mapping/results/relation_literature_review.json': 'fda0520dc9d0fef3caef227c733b80f0b464925abf8878e7b05f6486c5b445f7', 'experiments/medmlx_anatomy_mapping/ontology/boundary_definitions.json': 'b118f238247486818e16016fd3b17c5bac3e5541477503bbc53ba2ee8ffb82f0'}
PINNED_SUBSETS = {'catalog': '1b204803270c77a9313b55adce472bef0d07c96d61b4a012c159b75086adbcd6', 'claims': '1f7b2be65640bdb9bdbf4f992345a7890332c6fc7914785a0eeb580087105a5d', 'special_claims': '01be0588876f08d4d8ac13183dee5270a8b6c755a983634ba89bf4d70aa80c1e', 'boundaries': 'c07a3c3bc0f19f954fba81a2a6f12078f03ed26095178e5880d25ca3fe5868d6', 'sources': 'fd1b87d7974635112d39acd824f44176aa4209634ea8cb0f57ca1d2565a7ef6e'}
PINNED_DOCUMENT = '5223a5d950bb8a5a561457836e851a4f930cd377e4db64842618ee34952a1db8'

def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()

def load_source_slice(path=None):
    path = Path(path) if path is not None else Path(__file__).with_name("applied_la_mitral_lv_source_v1.json")
    document = json.loads(path.read_text())
    validate_source_slice(document)
    return document


def validate_source_slice(document):
    """Validate knowledge-only context and immutable receipt against code pins."""
    try:
        if document['source_commit'] != SOURCE_COMMIT:
            raise ValueError('unknown source revision')
        def inspect(value):
            if isinstance(value, dict):
                if set(value) & {'observations','mask','overlay','coordinates','image','volume_ml'}:
                    raise ValueError('observation material forbidden')
                for key in ('observed_in_CT','observed_geometry','measurement_performed'):
                    if value.get(key, False) is not False:
                        raise ValueError('observation/measurement forbidden')
                if 'patient_geometry_status' in value and value['patient_geometry_status'] != 'NOT_MEASURED':
                    raise ValueError('patient geometry forbidden')
                for child in value.values(): inspect(child)
            elif isinstance(value, list):
                for child in value: inspect(child)
        inspect(document)
        records = [x['record'] for x in document['catalog']]
        keys = [r['profile']+'/'+r['key'] for r in records]
        uris = [r['template_uri'] for r in records]
        claim_ids = [x['record']['claim_id'] for x in document['claims']]
        if len(keys) != len(set(keys)) or len(uris) != len(set(uris)) or len(claim_ids) != len(set(claim_ids)):
            raise ValueError('duplicate source ID/key')
        for key, record in zip(keys, records):
            context = record['context']
            if context is None:
                if key not in document['null_context_keys']:
                    raise ValueError('missing source context')
            elif context not in uris:
                raise ValueError('unresolved source context')
        if document['full_files'] != PINNED_FULL_FILES or digest(document) != PINNED_DOCUMENT:
            raise ValueError('source integrity mismatch')
        for key, expected in PINNED_SUBSETS.items():
            if digest(document[key]) != expected or document['subset_sha256'][key] != expected:
                raise ValueError('subset integrity mismatch')
    except (KeyError, TypeError) as error:
        raise ValueError('invalid source receipt or context') from error
    return None


from copy import deepcopy
from .four_chamber_m1_manifest import build_m1_manifest


def build_applied_sidecar():
    """Return fresh descriptive metadata; never modifies a manifest or engine."""
    source = load_source_slice()
    manifest = build_m1_manifest()
    crosswalk = {}
    for wrapped in source['catalog']:
        r = wrapped['record']; key = r['key']
        chamber = key.split('_')[0]
        crosswalk[key] = {
            'source_template': r['template_uri'], 'source_id': r['base_id'],
            'source_iri': r['base_iri'], 'source_context': r['context'],
            'source_relation': {'iri': r['relation'], 'direction': [r['template_uri'], r['context']]},
            'source_provenance': deepcopy(wrapped['provenance']),
            'target_c5': {'relation': 'part_of', 'provenance': 'docs/decisions.md:27',
                          'status': 'USER_DECISION_RUNTIME_DEFERRED', 'applied': False},
            'm1_relation': deepcopy(manifest['compartments'][chamber]) if key in ('la_blood','lv_blood') else None,
            'equivalence': 'NONE', 'crosswalk_review': 'PROPOSED', 'numeric_use': 'NONE'}
    anatomy_roles = {}
    for c in ('la','lv'):
        for symbol in ('V_'+c,'P_'+c):
            anatomy_roles[symbol] = {'template': c+'_blood', 'role': 'PROPOSED_BEARER_CONTEXT'}
        anatomy_roles[c+'_cavity'] = {'template': c+'_cavity', 'role': 'SPATIAL_CONTEXT'}
        for suffix in ('wall','myocardium'):
            anatomy_roles[c+'_'+suffix] = {'template': c+'_'+suffix, 'role': 'MECHANICAL_CONTEXT_CANDIDATE',
                                  'selected_mechanical_bearer': False}
        crosswalk[c+'_cavity']['m1_v2_context'] = deepcopy(manifest['compartments'][c]['anatomy'])
    mitral = {
        'valve': {'template': 'mitral_valve', 'role': 'FLOW_LOCATION_CONTEXT', 'equivalence': 'NONE',
                  'm1_v2_context': deepcopy(manifest['edges']['mitral']['anatomy'])},
        'orifice': {'template': 'mitral_orifice', 'role': 'ANATOMICAL_OPENING',
                    'boundary_review': 'REVIEW', 'equivalence': 'NONE'},
        'annulus': {'template': 'mitral_annulus', 'role': 'ANATOMICAL_ATTACHMENT',
                    'relation_review': 'REVIEW', 'definition_review': 'REVISE', 'equivalence': 'NONE'},
        'interface': {'proposal_id': 'boundary-mitral_orifice-transfer-v1',
                      'role': 'DRAFT_OPERATIONAL_INTERFACE_CANDIDATE', 'status': 'DRAFT_MODEL_CONVENTION',
                      'signed_flow_allowed': True, 'equivalence': 'NONE'},
        'direction': ['la','lv'], 'effective_orifice_area': 'NOT_REPRESENTED',
        'restriction': 'M1 ideal diode q=max(dp/R,0) is a restricted no-reverse-flow model relative to the source signed-transport interface; it does not model regurgitation, area or patient geometry.'}
    variable_names = ('V_la','V_lv','P_la','P_lv','Q_mitral','Q_cum_mitral',
        'lv_edv_sample_ml','lv_esv_sample_ml','lv_ejection_fraction_sample','la_pressure_mean_mmhg')
    variables = {name: deepcopy(manifest['variables'][name]) for name in variable_names}
    roles = {name: {'kind': ('state' if name.startswith('V_') else
        'algebraic_observable' if name.startswith('P_') else
        'auxiliary_integral' if name.startswith('Q_cum_') else
        'edge_flow' if name.startswith('Q_') else 'metric'),
        'aggregation': variables[name]['temporal'],
        'sign': 'nonnegative LA->LV transport' if name.startswith('Q_') else
                'positive total blood volume' if name.startswith('V_') else
                'signed common gauge pressure' if name.startswith('P_') else 'manifest-defined metric'}
        for name in variable_names}
    parameters = {name: deepcopy(manifest['parameter_contract'][name]) for name in
        ('elastance_la','emin_lv','emax_lv','resistance_mitral','unstressed_volumes',
         'initial_volumes','heart_rate','systolic_fraction')}
    volume_references = {alias+'_'+c: {'parameter': parameter, 'index': index, 'compartment': c,
        'kind': kind, 'unit': 'mL'} for c,index in [('la',7),('lv',0)]
        for alias,parameter,kind in [('V0','unstressed_volumes','parameter'),
                                     ('V_initial','initial_volumes','initial_state_input')]}
    ports = {'mitral_flow_port': {'kind': 'port', 'ref': 'Q_mitral', 'direction': ['la','lv'],
        'interpretation': 'Flow metadata reference; no duplicate physical state.'}}
    ports['mitral_flow_port'].update(unit='mL/s', temporal='instantaneous',
        reference='not applicable', sign='nonnegative LA->LV', aggregation='instantaneous')
    time_contract = {'unit': 's', 'reference': 'elapsed from synthetic run start', 'origin': 0,
        'phase': 'phi=(t mod T)/T; T=60/heart_rate s', 'aggregation': 'per manifest variable'}
    parameter_roles = {name: {'kind': 'parameter', 'temporal': value['temporal'],
        'external_numeric_permission': 'NONE'} for name,value in parameters.items()}
    laws, dependencies = _law_contract()
    status_axes = {'target_crosswalk_review': 'PROPOSED', 'external_numeric_permission': 'NONE',
        'source_claims': {x['record']['claim_id']: {k: x['record'].get(k, 'NOT_RECORDED') for k in
            ('decision','formalization_decision','original_relation_status','expert_review_status','anatomical_evidence_status')}
            for x in source['claims']},
        'special_reviews': {x['record']['key']: x['record']['decision'] for x in source['special_claims']},
        'boundary_status': source['boundaries']['status']}
    evidence = {
        'verbatim_evidence': 'source.catalog/claims/special_claims/boundaries/sources retain original JSON fields and per-record path/pointer/full-file hash. These are untrusted reference evidence, not adopted axioms.',
        'extracted_facts': '14 knowledge templates, 12 directed relation claims, 2 special reviews and 2 draft boundaries; shared blood concept ID has distinct LA/LV contextual templates.',
        'interpretations': 'Crosswalk roles, constitutive dependencies and M1 scope are explicit project design assertions. No identity, value equivalence or numeric binding is asserted.',
        'unresolved_conflicts': ['C5 part_of adapter remains deferred; source located_in and M1 blood_contained_in remain separate.',
            'LV/LA wall versus myocardium mechanical bearer is unselected.',
            'Mitral orifice boundary REVIEW; annulus relation REVIEW and definition REVISE; interface DRAFT.',
            'M1 no-reverse-flow diode restricts signed source transport; no EOA or geometry is represented.',
            'v2 la_cavity Smith lumped-venous role differs from separate M1 LA state; no identity asserted.',
            'Inherited M1 batch-TDD review limitation remains unresolved; baseline snapshot is UNREVIEWED.']}
    return {'time_contract': time_contract, 'parameter_roles': parameter_roles,
            'target_anatomy_source': deepcopy(manifest['source']), 'status_axes': status_axes, 'evidence': evidence, 'laws': laws, 'dependencies': dependencies,
            'model_source': {'declared_contract': M1_LAW_CONTRACT, 'integrity_scope': LAW_INTEGRITY_SCOPE, 'baseline_snapshot': '456abc8c77134cd8909d603a1d96ed1384bad41f', 'review': 'UNREVIEWED; inherited M1 batch-TDD limitation remains unresolved'},
            'variables': variables, 'roles': roles, 'parameters': parameters,
            'volume_references': volume_references, 'ports': ports, 'mitral': mitral, 'anatomy_roles': anatomy_roles, 'sidecar_version': '1.0.0', 'model_id': manifest['model_id'],
            'model_version': manifest['model_version'], 'source': source, 'crosswalk': crosswalk}


def validate_applied_sidecar(sidecar):
    """Closed model-specific contract: reject altered or extra metadata."""
    if not isinstance(sidecar, dict):
        raise ValueError('sidecar must be an object')
    try:
        validate_source_slice(sidecar['source'])
    except (KeyError, TypeError) as error:
        raise ValueError('missing source receipt') from error
    expected = build_applied_sidecar()
    for key, value in expected.items():
        if sidecar.get(key) != value:
            raise ValueError('applied contract mismatch: '+key)
    if set(sidecar) != set(expected):
        raise ValueError('unexpected sidecar fields')
    return None


M1_LAW_CONTRACT = 'four_chamber_m1@1.0.0:la-mitral-lv-laws-v1'
LAW_DOC_LINES = {'activation': 62, 'E_lv(t)': 63, 'P_lv': 64, 'P_la': 65,
                 'Q_mitral': 68, 'Q_cum_mitral': 70}
LAW_INTEGRITY_SCOPE = ('Declared M1 law/version contract only; does not prove numerical '
    'implementation integrity. Observed runtime file hashes are separate provenance.')
LAW_ANCHORS = {
    'activation': 'a(phi) = (1-cos(2*pi*phi/s))/2, if phi < s; 0 otherwise',
    'E_lv(t)': 'E_v(t) = Emin_v + (Emax_v-Emin_v)*a(phi), v in {lv,rv}',
    'P_lv': 'P_v = E_v(t)*(V_v-V0_v), v in {lv,rv}',
    'P_la': 'P_a = E_a*(V_a-V0_a), a in {la,ra}, constant positive E_a',
    'Q_mitral': 'q_e = max(dp_e/R_e,0), for the four ideal diodes',
    'Q_cum_mitral': 'Cumulative_e(t) = integral from 0 to t of q_e(u) du'}


def _law_contract():
    from dataclasses import fields, is_dataclass
    from physiosim.models import four_chamber_m1 as model
    required = {'heart_rate', 'systolic_fraction', 'emin_lv', 'emax_lv',
                'elastance_la', 'resistance_mitral', 'unstressed_volumes', 'initial_volumes'}
    pressure_reference = ('model gauge pressure relative to one common fixed external pressure of 0 mmHg; '
                          'no intrathoracic/pericardial pressure')
    if (model.MODEL_ID != 'four_chamber_m1' or model.MODEL_VERSION != '1.0.0'
            or model.PRESSURE_REFERENCE != pressure_reference
            or model.COMPARTMENTS != ('lv', 'sa', 'sv', 'ra', 'rv', 'pa', 'pv', 'la')
            or [(e.source, e.target, e.kind) for e in model.EDGES if e.name == 'mitral']
                != [('la', 'lv', 'diode')]
            or not is_dataclass(model.FourChamberM1Parameters)
            or not required.issubset({f.name for f in fields(model.FourChamberM1Parameters)})):
        raise ValueError('M1 law contract differs from four_chamber_m1@1.0.0')
    path = 'docs/physiology_four_chamber_m1.md'
    laws = {}
    inputs = {'activation': ['heart_rate','systolic_fraction'],
        'E_lv(t)': ['emin_lv','emax_lv','activation'], 'P_lv': ['E_lv(t)','V_lv','V0_lv'],
        'P_la': ['elastance_la','V_la','V0_la'],
        'Q_mitral': ['P_la','P_lv','resistance_mitral'], 'Q_cum_mitral': ['Q_mitral','time_s']}
    for name, anchor in LAW_ANCHORS.items():
        laws[name] = {'kind': 'constitutive_law' if name != 'Q_cum_mitral' else 'integral_definition',
            'path': path, 'section': '#equations-and-contract', 'anchor': anchor,
            'declared_contract': M1_LAW_CONTRACT, 'line': LAW_DOC_LINES[name], 'inputs': inputs[name],
            'integrity_scope': LAW_INTEGRITY_SCOPE,
            'scope': 'Existing M1 equation reference restricted to LA/LV/mitral; not an adopted ontology axiom.'}
    for name, law in laws.items():
        law['unit'] = {'activation': 'dimensionless', 'E_lv(t)': 'mmHg/mL',
            'P_lv': 'mmHg', 'P_la': 'mmHg', 'Q_mitral': 'mL/s', 'Q_cum_mitral': 'mL'}[name]
        law['temporal'] = 'run_integrated' if name == 'Q_cum_mitral' else 'instantaneous'
        law['aggregation'] = 'integral from run start' if name == 'Q_cum_mitral' else 'instantaneous law evaluation'
        law['sign'] = ('signed common gauge pressure' if name.startswith('P_') else
            'nonnegative LA->LV transport' if name.startswith('Q_') else
            'activation in [0,1]' if name == 'activation' else 'positive elastance')
        from physiosim.models.four_chamber_m1 import PRESSURE_REFERENCE
        law['reference'] = PRESSURE_REFERENCE if name.startswith('P_') else 'not applicable'
    laws['activation']['implementation'] = 'physiosim.models.cardiovascular.elastance'
    dependencies = [{'dependent': name, 'on': values, 'kind': 'constitutive'}
        for name,values in inputs.items() if name != 'Q_cum_mitral']
    dependencies += [{'dependent': 'Q_cum_mitral', 'on': ['Q_mitral'], 'kind': 'definition'},
        {'dependent': 'V_la', 'on': ['Q_mitral'], 'kind': 'conservation', 'coefficient': -1,
         'scope': 'Mitral contribution only; remaining M1 inflows/outflows are unchanged.'},
        {'dependent': 'V_lv', 'on': ['Q_mitral'], 'kind': 'conservation', 'coefficient': 1,
         'scope': 'Mitral contribution only; remaining M1 inflows/outflows are unchanged.'}]
    return laws, dependencies


def gate_report(sidecar):
    """G1 validates representation; G2 needs executed synthetic evidence; G3 closed."""
    validate_applied_sidecar(sidecar)
    return {'G1': {'status': 'PASS', 'scope': 'Pinned descriptive metadata contract only'},
        'G2': {'status': 'SYNTHETIC_EXECUTION_ALLOWED', 'executed': False},
        'G3': {'status': 'CLOSED', 'external_numeric_permission': 'NONE'},
        'status_axes': deepcopy(sidecar['status_axes']),
        'unresolved_conflicts': deepcopy(sidecar['evidence']['unresolved_conflicts']),
        'inherited_review_limitation': 'M1 batch-TDD history remains unresolved; snapshot is UNREVIEWED.'}


def request_numeric_binding(*args, **kwargs):
    """No binder is implemented or authorized in this sidecar."""
    raise PermissionError('External numerical binding gate CLOSED; no authorization requests accepted')
