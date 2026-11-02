"""Owner decisions 3/4: shared mathematical gauge and model-scoped blood.

These are model assertions. No atmospheric, pericardial or transmural claim.
Pressure variables remain properties of blood; an explicit differential adapter
records that blood as source and the shared mathematical zero as sink.
"""
GAUGE = 'model_gauge_fixed_external_zero'


def pressure_reference():
    return {'id': GAUGE, 'label': 'model gauge (mathematical zero), fixed external pressure zero',
            'sink': 'shared:fixed_external_pressure_zero', 'external_pressure_mmhg': 0.,
            'atmosphere_relation': 'UNKNOWN'}


def build_representation(model):
    from dataclasses import asdict
    blood = {q.compartment: {'id': q.bearer, 'compartment': q.compartment,
             'entity_type': 'blood', 'anatomy': [asdict(a) for a in q.anatomy]}
             for q in model.quantities if q.name.startswith('V_') and q.compartment}
    pressure = {q.name: {'id': model.model_id+':pressure_differential:'+q.name,
                'quantity': q.id, 'source': blood[q.compartment]['id'],
                'sink': pressure_reference()['sink'], 'reference': GAUGE}
                for q in model.quantities if q.reference == GAUGE}
    return blood, pressure


def validate_representation(model):
    expected_blood, expected_pressure = build_representation(model)
    if model.policies.get('pressure_reference') != pressure_reference():
        raise ValueError('missing/wrong common mathematical pressure reference')
    if model.blood_entities != expected_blood or model.pressure_differentials != expected_pressure:
        raise ValueError('missing/wrong blood or pressure source/sink/reference')
    for q in model.quantities:
        if q.compartment and q.name.startswith(('V_', 'P_')):
            if q.bearer != model.blood_entities[q.compartment]['id']:
                raise ValueError('pressure/volume must share compartment blood')
    for path in model.paths.values():
        if path['participants'] != [model.blood_entities[c]['id'] for c in (path['source'],path['target'])]:
            raise ValueError('flow participants must share compartment blood')
