"""ONTO-R1: executable inventories are measured from the active worktree."""
from pathlib import Path
import json
import physiosim

ROOT = Path(__file__).resolve().parents[1]


def test_acceptance_matrix_and_worktree_import():
    assert Path(physiosim.__file__).resolve().is_relative_to(ROOT / 'src')
    from physiosim.ontology.contracts import acceptance_matrix
    matrix = acceptance_matrix()
    categories = {'physical_state', 'auxiliary_state', 'algebraic_output', 'parameter',
                  'parameter_component', 'scalar_parameter_port', 'metric', 'cumulative_metric',
                  'diagnostic_metric', 'agent_metric', 'independent_variable', 'derived_timing',
                  'internal_law_quantity', 'derivative', 'binding_observable'}
    for model in ('phase1', 'four_chamber_m1'):
        assert categories <= set(matrix['models'][model]['categories'])
        for decision in matrix['models'][model]['categories'].values():
            assert decision['disposition'] in ('included', 'excluded')
            assert decision['reason']
    assert matrix['exclusions']['clinical_validation']['reason']
    assert matrix['applied_sidecar']['scope'] == 'LEFT-side partial'
    assert matrix['ontology_versions']['OPB'] == '1.07'
    entry = (ROOT / 'docs/decisions.md').read_text().split('## 2026-11-02 — ONTO-R1 owner decisions')[-1]
    for quote in ('모두 그렇게 해라', '혈관 구획을 해부학 노드에 연결하고',
                  "심실 수축 성질은 '구조'가 아니니까 좀 다른 차원에서 얘기를 해야할 것 같고",
                  '저항을 지닌 것은 "흐름 경로"로 가자.', '다만 저항이 유독 심한 곳은 좀 더 자세히 들여다 봐야겠다'):
        assert quote in entry
    for gap in ('A07', 'A12', 'A13', 'A14', 'A15', 'A18', 'A21', 'A26', 'G1', 'G2', 'G3', 'G4', 'G6'):
        assert gap in entry


def schema_fixture():
    from physiosim.ontology.contracts import AnatomyContext, QuantityContract, ModelContract, ContractBundle
    def model(mid):
        quantity = QuantityContract(model_id=mid, model_version='test-1', name='P_lv',
            kind='algebraic_output', property_id='http://bhi.washington.edu/OPB#OPB_00509',
            classification=None, aggregation='instantaneous', unit='mmHg',
            bearer=mid+':blood:lv', process_context=('circulation',),
            anatomy=(AnatomyContext('lv_cavity', 'blood_contained_in', 'used'),),
            evidence=('docs/physiology.md',), reference='model_gauge_fixed_external_zero')
        return ModelContract(mid, 'test-1', (quantity,), {'algebraic_output': ('P_lv',)})
    return ContractBundle((model('phase1'), model('four_chamber_m1')))


def test_typed_schema_roundtrip_and_scoped_homonyms():
    from dataclasses import replace
    from physiosim.ontology.contracts import AnatomyContext, ContractBundle
    bundle = schema_fixture()
    assert len({m.quantity('P_lv').id for m in bundle.models}) == 2
    q=bundle.models[0].quantity('P_lv')
    for status in ('unknown', 'proposed', 'local'):
        q=replace(q, anatomy=q.anatomy+(AnatomyContext('local:candidate_'+status, 'model_context', status),))
    m=replace(bundle.models[0], quantities=(q,))
    bundle=replace(bundle,models=(m,bundle.models[1]))
    assert ContractBundle.from_json(bundle.to_json()) == bundle
    assert json.loads(bundle.to_json())['models'][0]['quantities'][0]['anatomy'][-1]['status']=='local'


def test_typed_schema_rejects_invalid_contracts():
    from dataclasses import replace
    import pytest
    from physiosim.ontology.contracts import AnatomyContext, ContractBundle
    b=schema_fixture(); m=b.models[0]; q=m.quantity('P_lv')
    for change in ({'unit':''}, {'property_id':None}, {'unit':'mL'}, {'kind':'wall'},
                   {'aggregation':''}, {'bearer':'four_chamber_m1:blood:lv'},
                   {'reference':'atmospheric'},
                   {'evidence':()}):
        with pytest.raises(ValueError):
            replace(q, **change)
    with pytest.raises(ValueError): AnatomyContext('lv_cavity','sameAs','used')
    with pytest.raises(ValueError): AnatomyContext('local:candidate','model_context','used')
    with pytest.raises(ValueError): ContractBundle((m,m))
    with pytest.raises(ValueError): replace(m,quantities=(q,q))
    with pytest.raises(ValueError): replace(m,inventory={'algebraic_output':('missing',)})


def test_phase1_parameters_and_alias_conversions():
    from dataclasses import fields, replace
    import pytest
    from physiosim.models.cardiovascular import Parameters, COMPARTMENTS
    from physiosim.agent import catalog
    from physiosim.ontology.contracts import build_phase1_contract, Alias
    m=build_phase1_contract()
    assert set(m.inventory['parameter']) == {f.name for f in fields(Parameters)}
    assert len(m.inventory['parameter']) == 18
    assert set(m.inventory['scalar_parameter_port']) == set(catalog.flatten(Parameters(),'phase1'))
    assert len(m.inventory['scalar_parameter_port']) == 28
    assert m.quantity('initial_volumes').order == COMPARTMENTS
    assert m.quantity('unstressed_volumes').order == COMPARTMENTS
    assert m.quantity('initial_volumes.lv').aggregation == 'initial'
    assert m.quantity('unstressed_volumes.lv').aggregation == 'constant_parameter'
    assert m.quantity('initial_volumes.lv').bearer == 'phase1:blood:lv'
    assert m.quantity('emin_lv').bearer == 'phase1:organ:lv'
    assert m.quantity('emin_lv').name != 'E_lv'
    assert m.quantity('HR').name == 'heart_rate'
    assert m.convert('HR_per_s',120.) == 2.
    for name in ('C_sa','C_sv','C_pa','C_pv'):
        assert m.quantity(name).name == 'compliance_'+name[2:]
    for edge in m.paths:
        assert m.quantity('R_'+edge).name == 'resistance_'+edge
        assert m.quantity('R_'+edge).bearer == 'phase1:path:'+edge
    with pytest.raises(ValueError): replace(m.quantity('emin_lv'),bearer='phase1:wall:lv')
    with pytest.raises(ValueError): replace(m.quantity('heart_rate'),aliases=(Alias('HR_per_s','1/s',60),))


def test_phase1_runtime_coverage_and_unavailable_diagnostics():
    import numpy as np
    from physiosim.simulation import simulate
    from physiosim.models.cardiovascular import elastance, rhs
    from physiosim.ontology.bindings import observations
    from physiosim.ontology.contracts import build_phase1_contract, diagnostic_values
    plain=simulate(cycles=2,samples_per_cycle=40)
    augmented=simulate(cycles=2,samples_per_cycle=40,cumulative_flows=True)
    m=build_phase1_contract()
    assert set(m.inventory['physical_state']) == {'V_'+c for c in plain.compartment_names}
    assert len(m.inventory['physical_state']) == plain.volumes.shape[1] == 6
    assert set(m.inventory['auxiliary_state']) == {'Q_cum_'+e for e in augmented.flow_names}
    assert len(m.inventory['auxiliary_state']) == augmented.cumulative_flows.shape[1] == 6
    assert plain.cumulative_flows is None
    outputs={'P_'+c for c in plain.compartment_names}|{'Q_'+e for e in plain.flow_names}
    outputs|={'E_'+c for c in ('lv','rv')[:len(elastance(0,plain.parameters))]}
    assert set(m.inventory['algebraic_output']) == outputs
    assert set(m.inventory['metric']) == set(plain.metrics())
    assert set(m.inventory['cumulative_metric']) == set(augmented.cumulative_metrics())
    assert set(m.inventory['diagnostic_metric']) == set(diagnostic_values(augmented)) == {'local_balance_residual_ml'}
    for key in observations(plain): assert m.quantity(key)
    assert set(m.inventory['derivative']) == {'rhs['+c+']' for c,_ in zip(plain.compartment_names,rhs(0,plain.volumes[0],plain.parameters))}
    assert m.quantity('stroke_volume_ml').numerical_policy == 'sampled_trapezoidal'
    assert m.quantity('stroke_volume_cumulative_ml').numerical_policy == 'solver_integrated_difference'
    assert m.quantity('stroke_volume_ml').id != m.quantity('stroke_volume_cumulative_ml').id
    assert m.quantity('final_beat_net_throughput_systemic_ml').numerical_policy == 'solver_integrated_signed_difference'
    assert m.quantity('CO').aggregation == 'beat_mean'
    assert m.quantity('Q_aortic').aggregation == 'instantaneous'
    assert m.quantity('lv_edv_ml').aggregation == 'extremum_max'
    assert m.quantity('lv_esv_ml').aggregation == 'extremum_min'
    assert m.quantity('V_lv').bearer == m.quantity('P_lv').bearer == 'phase1:blood:lv'
    assert m.quantity('Q_mitral').participants == ('phase1:blood:pv','phase1:blood:lv')
    assert m.quantity('E_lv').bearer == m.quantity('emin_lv').bearer
    one=simulate(cycles=1,samples_per_cycle=4)
    assert np.isnan(one.metrics()['final_beat_max_volume_difference_ml'])
    assert m.quantity('final_beat_max_volume_difference_ml').unavailable == 'raw_nan_serialized_null'
    assert diagnostic_values(one)['local_balance_residual_ml'] is None
    json.dumps(diagnostic_values(one),allow_nan=False)
    assert m.convert('cardiac_output_l_min',100) == 6
    assert m.convert('cardiac_output_m3_s',100) == 1e-4 or np.isclose(m.convert('cardiac_output_m3_s',100),1e-4)


def test_m1_manifest_runtime_and_diagnostic_coverage():
    from dataclasses import fields, replace
    import pytest
    from physiosim.models.four_chamber_m1 import FourChamberM1Parameters, COMPARTMENTS, rhs
    from physiosim.agent.catalog import synthetic_fixture, flatten
    from physiosim.simulation.four_chamber_m1 import simulate_m1
    from physiosim.ontology.four_chamber_m1_manifest import build_m1_manifest
    from physiosim.ontology.contracts import build_m1_contract, diagnostic_values, ContractBundle
    p=synthetic_fixture(); result=simulate_m1(p,cycles=2,samples_per_cycle=40)
    m=build_m1_contract(); manifest=build_m1_manifest()
    assert len(manifest['variables']) == len(m.inventory['manifest_variable']) == 62
    assert set(m.inventory['manifest_variable']) == set(manifest['variables'])
    assert set(m.inventory['parameter']) == {f.name for f in fields(FourChamberM1Parameters)} == set(manifest['parameter_contract'])
    assert len(m.inventory['parameter']) == 22
    assert set(m.inventory['scalar_parameter_port']) == set(flatten(p,'m1'))
    assert len(m.inventory['scalar_parameter_port']) == 36
    for name,record in manifest['variables'].items():
        q=m.quantity(name)
        assert m.unit(name) == record['unit']
        if not record['property'].startswith('https://example.org/'):
            assert q.property_id == record['property']
    assert tuple(m.inventory['physical_state']) == tuple('V_'+c for c in result.compartment_names)
    assert tuple(m.inventory['auxiliary_state']) == tuple('Q_cum_'+e for e in result.edge_names)
    assert len(m.inventory['physical_state']) == result.volumes.shape[1] == 8
    assert len(m.inventory['auxiliary_state']) == result.cumulative_flows.shape[1] == 8
    assert set(m.inventory['algebraic_output']) == {'P_'+c for c in result.compartment_names}|{'Q_'+e for e in result.edge_names}|{'E_lv','E_rv'}
    assert set(m.inventory['metric']) == set(result.metrics())
    assert len(m.inventory['metric']) == 30
    assert set(m.inventory['diagnostic_metric']) == set(diagnostic_values(result))
    assert len(m.inventory['diagnostic_metric']) == 12
    assert m.quantity('initial_volumes').order == COMPARTMENTS
    assert set(m.inventory['derivative']) == {'rhs['+c+']' for c,_ in zip(COMPARTMENTS,rhs(0,p.initial_volumes,p))}
    for alias,target in manifest['metric_aliases'].items(): assert m.quantity(alias) == m.quantity(target)
    assert m.quantity('lv_stroke_volume_ml').numerical_policy == 'solver_integrated_difference'
    one=simulate_m1(p,cycles=1,samples_per_cycle=4)
    assert diagnostic_values(one)['periodicity.max_difference_ml'] is None
    assert all(v is None for k,v in diagnostic_values(one).items() if k.startswith('periodicity.'))
    json.dumps(diagnostic_values(one),allow_nan=False)
    with pytest.raises(ValueError): replace(m,quantities=tuple(q for q in m.quantities if q.name!='Q_mitral'))
    assert ContractBundle.from_json(ContractBundle((m,)).to_json()).models == (m,)


def test_agent_metric_keys_policies_and_semantic_negatives():
    import pytest
    from physiosim.agent import tools, catalog
    from physiosim.simulation import simulate
    from physiosim.simulation.four_chamber_m1 import simulate_m1
    from physiosim.validation import periodicity_report
    from physiosim.ontology.contracts import build_phase1_contract, build_m1_contract, validate_quantity_connection
    for model,builder in [('phase1',build_phase1_contract),('m1',build_m1_contract)]:
        r=simulate(cycles=2,samples_per_cycle=40) if model=='phase1' else simulate_m1(catalog.synthetic_fixture(),cycles=2,samples_per_cycle=40)
        m=builder()
        actual=tools._metrics(r,model)
        assert set(m.inventory['agent_metric']) == set(actual)
        assert len(actual) == (68 if model=='phase1' else 87)
        assert set(m.inventory['agent_added_metric']) == set(actual)-set(r.metrics())
        for key in actual: assert m.quantity(key)
        assert set(m.inventory['agent_periodicity']) == {'agent_periodicity.'+k for k in tools._periodicity(r,2)}
        strict=periodicity_report(r.volumes,40)
        assert set(m.inventory['strict_periodicity']) == {'strict_periodicity.'+k for k in strict}
        assert m.policies['agent_periodicity']['threshold'] == tools.PERIODICITY_THRESHOLD
        assert m.policies['strict_periodicity']['tolerance_ml'] == strict['tolerance_ml']
        assert m.quantity('agent_periodicity.max_relative_change').unit == 'dimensionless'
        assert m.quantity('strict_periodicity.max_residual_ml').unit == 'mL'
        assert m.quantity('systemic_forward_volume_ml').numerical_policy == 'sampled_positive_trapezoidal'
        assert m.quantity('systemic_backward_volume_ml').numerical_policy == 'sampled_negative_magnitude_trapezoidal'
        assert m.quantity('systemic_mean_flow_ml_s').aggregation == 'beat_mean'
        for a,b in [('systemic_mean_flow_ml_s','Q_systemic'),
                    ('systemic_forward_volume_ml','Q_cum_systemic'),
                    ('agent_periodicity.max_relative_change','strict_periodicity.max_residual_ml')]:
            with pytest.raises(ValueError): validate_quantity_connection(m.quantity(a),m.quantity(b))
    p=build_phase1_contract(); m=build_m1_contract()
    with pytest.raises(ValueError): validate_quantity_connection(p.quantity('P_lv'),m.quantity('P_lv'))
    with pytest.raises(ValueError): validate_quantity_connection(p.quantity('stroke_volume_ml'),p.quantity('stroke_volume_cumulative_ml'))
    with pytest.raises(ValueError): validate_quantity_connection(p.quantity('systemic_forward_volume_ml'),p.quantity('final_beat_net_throughput_systemic_ml'))
    validate_quantity_connection(p.quantity('P_lv'),p.quantity('P_lv'))


def test_g4_paths_catalogue_and_knowledge_have_one_source():
    from copy import deepcopy
    from physiosim.agent import catalog, tools
    from physiosim.ontology import cardiovascular_registry, build_graph, BASE, BQBIOL
    from physiosim.ontology.contracts import build_phase1_contract, build_m1_contract, agent_path_projection
    from rdflib import URIRef
    nodes={n['key'] for n in catalog.knowledge()['anatomy']['nodes']}
    for agent_model,builder in [('phase1',build_phase1_contract),('m1',build_m1_contract)]:
        m=builder(); expected=agent_path_projection(m)
        assert catalog.knowledge()['flow_paths'][agent_model] == expected
        assert len(m.anatomy_usage) == 31
        assert set(m.anatomy_usage) == nodes
        ports={p['name']:p for p in catalog.catalogue(agent_model)}
        for edge,path in m.paths.items():
            binding=ports['resistance_'+edge]['binding']
            assert binding == expected[edge]
            assert binding['relation'] == 'property_of_flow_path'
            assert binding['primary_id'] is None
            assert all(i['context_relation']=='traverses' for i in binding['ids'])
            assert m.quantity('resistance_'+edge).bearer == path['id'] == binding['key']
            assert binding['source_compartment'] == path['source']
            assert binding['target_compartment'] == path['target']
            assert all(a['key'] in nodes or (a['status'] in ('local','unknown') and a['key'].startswith('local:')) for a in binding['traverses'])
            q=m.quantity('Q_'+edge)
            if path['kind']=='diode':
                assert any(a.key==path['process_location'] and a.relation=='bqbiol:occursIn' for a in q.anatomy)
        keys=[a['key'] for a in expected['mitral']['traverses']]
        assert keys == (['pulmonary_venous_lumen','la','mitral_valve'] if agent_model=='phase1' else ['mitral_valve'])
        assert [a['key'] for a in expected['tricuspid']['traverses']] == (['systemic_venous_lumen','ra','tricuspid_valve'] if agent_model=='phase1' else ['tricuspid_valve'])
        assert agent_path_projection(m) == expected
        changed=deepcopy(expected); changed['mitral']['relation']='flow_location'
        assert changed != agent_path_projection(m)
    r=cardiovascular_registry()
    for edge,path in build_phase1_contract().paths.items():
        assert r['R_'+edge].bearer == 'flow path'
        assert r['R_'+edge].flow_path == path
        assert r['R_'+edge].occurs_in is None
    graph=build_graph().graph(URIRef(BASE+'graph/model-assertions'))
    assert (URIRef(BASE+'bearer/Q_mitral'),URIRef(BQBIOL+'occursIn'),URIRef(r['Q_mitral'].occurs_in.uri)) in graph
    assert {'model':'m1','parameter':'resistance_mitral'} in next(e for e in tools.lookup_ontology('mitral')['entities'] if e['key']=='mitral_valve')['related_parameters']


def test_release_snapshot_controls_and_metadata_only_build(monkeypatch):
    from dataclasses import fields, replace
    import inspect
    import pytest
    import physiosim.simulation as p1_sim
    import physiosim.simulation.four_chamber_m1 as m1_sim
    from physiosim.ontology import CONTEXTS, PROPERTIES
    from physiosim.ontology.contracts import build_contract_bundle, ContractBundle, AnatomyContext
    p1_controls=set(inspect.signature(p1_sim.simulate).parameters)-{'parameters'}
    m1_controls={f.name for f in fields(m1_sim.SolverSettings)}|{'cycles','samples_per_cycle'}
    def forbidden(*args,**kwargs): raise AssertionError('contract generation must not execute solver')
    monkeypatch.setattr(p1_sim,'simulate',forbidden)
    monkeypatch.setattr(m1_sim,'simulate_m1',forbidden)
    bundle=build_contract_bundle()
    assert bundle.to_json() == build_contract_bundle().to_json()
    assert bundle.to_json() == (ROOT/'src/physiosim/ontology/quantity_contracts.json').read_text()
    assert ContractBundle.from_json(bundle.to_json()) == bundle
    for model,controls in zip(bundle.models,(p1_controls,m1_controls)):
        assert set(model.inventory['numerical_control']) == {'solver.'+c for c in controls}
        for name in model.inventory['numerical_control']:
            assert model.quantity(name).classification.startswith('nonphysical:')
        for q in model.quantities:
            for a in q.aliases:
                assert model.quantity(a.name) == q
                assert model.convert(a.name,7) == 7*a.factor
            assert all((ROOT/p.split('#')[0]).is_file() for p in q.evidence)
            if q.property_id:
                assert q.property_id in {p.uri for p in PROPERTIES.values() if not p.local}
            if q.name=='E_lv':
                assert CONTEXTS['contraction'].uri in q.process_context
        with pytest.raises(ValueError):
            replace(model.quantity('V_sv'),anatomy=(AnatomyContext('la_cavity','blood_contained_in','used'),))
        with pytest.raises(ValueError):
            replace(model.quantity('E_lv'),anatomy=(AnatomyContext('lv_wall','organ_bearer','used'),))
