"""M1 validates its own contract against offline v2, without changing v1."""
from copy import deepcopy
import pytest
from physiosim.ontology import cardiovascular_registry
from physiosim.ontology import four_chamber_m1_manifest as a
from physiosim.models.four_chamber_m1 import PRESSURE_REFERENCE


def test_manifest_identifiers_and_variable_contract():
    before=cardiovascular_registry()
    nodes=a.load_anatomy_v2()
    manifest=a.build_m1_manifest(nodes)
    a.validate_m1_manifest(manifest,nodes)
    assert cardiovascular_registry()==before
    assert manifest['compartments']['la']['anatomy']['primary_id']=='UBERON:0016513'
    assert manifest['compartments']['ra']['anatomy']['primary_id']=='UBERON:0016522'
    assert manifest['compartments']['pv']['anatomy']['primary_id']=='FMA:52455'
    assert manifest['compartments']['pv']['anatomy']['uberon_relation']=='related_structure'
    assert manifest['edges']['mitral']['source']=='la' and manifest['edges']['mitral']['target']=='lv'
    assert manifest['variables']['P_la']['reference']==PRESSURE_REFERENCE
    assert manifest['variables']['P_la']['kind']=='chamber_pressure'
    assert manifest['variables']['Q_cum_mitral']['temporal']=='run_integrated'
    assert manifest['variables']['SV_rv']['temporal']=='beat_integrated'
    assert manifest['variables']['CO_rv']['temporal']=='beat_mean'
    assert manifest['unresolved_conflicts']
    assert manifest['source']['ontology_versions']==nodes['ontology_versions']
    with pytest.raises(FileNotFoundError): a.load_anatomy_v2('/nonexistent/m1/anatomy.json')


@pytest.mark.parametrize('mutation',[
    lambda x:x['edges']['mitral'].update(source='lv',target='la'),
    lambda x:x['edges']['aortic'].update(anatomy=x['edges']['mitral']['anatomy']),
    lambda x:x['variables']['P_la'].update(unit='mL'),
    lambda x:x['variables']['P_la'].pop('reference'),
    lambda x:x['variables']['Q_mitral'].update(direction=['lv','la']),
    lambda x:x['variables']['V_la'].update(direction=['la','lv']),
    lambda x:x['variables']['P_la'].update(property='unknown'),
    lambda x:x['variables']['SV_lv'].update(temporal='instantaneous'),
    lambda x:x['variables']['Q_cum_mitral'].update(temporal='beat_integrated'),
    lambda x:x['compartments']['la']['anatomy'].update(uberon='UBERON:9999999'),
    lambda x:x['compartments']['la']['anatomy'].update(fma='FMA:9466'),
    lambda x:x['compartments']['sa'].update(relation='identity'),
    lambda x:x['compartments'].pop('la'),
    lambda x:x['variables'].pop('Q_venous_return'),
    lambda x:x.update(model_version='0.0.0'),
])
def test_semantic_negatives(mutation):
    nodes=a.load_anatomy_v2(); manifest=deepcopy(a.build_m1_manifest(nodes))
    mutation(manifest)
    with pytest.raises(ValueError): a.validate_m1_manifest(manifest,nodes)


def test_parameter_units_are_explicit_in_machine_contract():
    manifest=a.build_m1_manifest()
    assert manifest['parameter_contract']['elastance_la']['unit']=='mmHg/mL'
    assert manifest['parameter_contract']['resistance_venous_return']['unit']=='mmHg*s/mL'
    assert manifest['parameter_contract']['initial_volumes']['order']==['lv','sa','sv','ra','rv','pa','pv','la']
    assert manifest['parameter_contract']['initial_volumes']['unit']=='mL'
    assert 'explicit caller input' in manifest['parameter_contract']['elastance_ra']['provenance']
    bad=deepcopy(manifest); bad['parameter_contract']['elastance_ra']['unit']='mL/mmHg'
    with pytest.raises(ValueError): a.validate_m1_manifest(bad)


@pytest.mark.parametrize('unit', ['mL', 'Pa', 'not_a_unit', None])
def test_unit_changes_rejected_by_exact_manifest_contract(unit):
    from physiosim.ontology.four_chamber_m1_manifest import build_m1_manifest, validate_m1_manifest
    manifest = build_m1_manifest()
    manifest['variables']['P_la']['unit'] = unit
    with pytest.raises(ValueError, match='M1 semantic contract mismatch: variables'):
        validate_m1_manifest(manifest)
