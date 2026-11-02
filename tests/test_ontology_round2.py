"""ONTO-R2 acceptance: local identities, shared blood/gauge, laws and evidence."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import json
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]


def models():
    from physiosim.ontology.contracts import build_contract_bundle
    return build_contract_bundle().models


def test_anatomical_contexts_and_identity_negatives():
    from physiosim.ontology.contracts import AnatomyContext
    from physiosim.ontology import cardiovascular_registry
    vessels = dict(sa='systemic_arterial_lumen', sv='systemic_venous_lumen',
                   pa='pulmonary_arterial_lumen', pv='pulmonary_venous_lumen')
    for m in models():
        assert len(m.anatomy_usage) == 31
        for c, key in vessels.items():
            q = m.quantity('V_'+c)
            assert q.bearer == m.model_id+':blood:'+c
            assert [(a.key,a.relation) for a in q.anatomy] == [(key,'lumped_compartment_context')]
            assert m.anatomy_usage[key] == 'context'
            if m.model_id == 'phase1' and c in ('sv','pv'):
                assert 'atrial filling is lumped' in q.note
            for relation in ('blood_contained_in','organ_bearer','model_context'):
                with pytest.raises(ValueError):
                    replace(q,anatomy=(AnatomyContext('la_cavity',relation,'context'),))
            with pytest.raises(ValueError):
                replace(q,bearer=m.model_id+':anatomy:'+key)
        for relation in ('owl:sameAs','owl:equivalentClass','identity'):
            with pytest.raises(ValueError): AnatomyContext(vessels['sv'],relation,'context')
        if m.model_id == 'phase1':
            assert not any(q.compartment in ('la','ra') for q in m.quantities)
        else:
            assert m.quantity('V_la').bearer != m.quantity('V_pv').bearer
    r=cardiovascular_registry()
    assert r['V_sv'].anatomy.local
    assert r['V_sv'].anatomy_context['key'] == vessels['sv']


def test_shared_blood_gauge_and_negative_fixtures():
    from physiosim.ontology.representation import pressure_reference, validate_representation
    from physiosim.ontology import cardiovascular_registry, build_graph, BASE
    from rdflib import URIRef
    for m in models():
        validate_representation(m)
        assert m.policies['pressure_reference'] == pressure_reference()
        assert 'mathematical zero' in pressure_reference()['label']
        assert pressure_reference()['atmosphere_relation'] == 'UNKNOWN'
        assert len(m.blood_entities) == len(m.inventory['physical_state'])
        for c, blood in m.blood_entities.items():
            assert blood['id'] == m.quantity('V_'+c).bearer == m.quantity('P_'+c).bearer
            assert m.quantity('V_'+c).id != m.quantity('P_'+c).id
            d=m.pressure_differentials['P_'+c]
            assert d['source'] == blood['id']
            assert d['sink'] == pressure_reference()['sink']
        for e,p in m.paths.items():
            assert p['participants'] == [m.blood_entities[c]['id'] for c in (p['source'],p['target'])]
        for field,value in [('source',''),('source',m.model_id+':blood:wrong'),('sink',''),
                            ('sink','atmosphere'),('reference','absolute')]:
            bad=deepcopy(m.pressure_differentials);bad['P_lv'][field]=value
            with pytest.raises(ValueError): replace(m,pressure_differentials=bad)
        for reference in ('','atmospheric','absolute'):
            with pytest.raises(ValueError): replace(m.quantity('P_lv'),reference=reference)
    r=cardiovascular_registry(); ds=build_graph(); g=ds.graph(URIRef(BASE+'graph/model-assertions'))
    prop=URIRef(BASE+'propertyOf'); blood=URIRef(BASE+'phase1/blood/lv')
    assert (URIRef(r['V_lv'].uri),prop,blood) in g
    assert (URIRef(r['P_lv'].uri),prop,blood) in g
    assert (URIRef(BASE+'bearer/Q_mitral'),URIRef(BASE+'hasTargetParticipant'),blood) in g
    for forbidden in ('http://www.w3.org/2002/07/owl#sameAs','http://www.w3.org/2002/07/owl#equivalentClass'):
        assert not list(g.triples((None,URIRef(forbidden),None)))


def law_for(m, output, kind=None):
    laws=[l for l in m.dependency_graph['laws'] if output in l['outputs'] and (kind is None or l['kind']==kind)]
    assert len(laws)==1,(output,laws)
    return laws[0]


@pytest.mark.parametrize('index',[0,1])
def test_complete_laws_topology_and_metric_definitions(index):
    from physiosim.ontology.dependencies import validate_dependency_graph
    from physiosim.models import cardiovascular as p1, four_chamber_m1 as m1
    m=models()[index]; g=m.dependency_graph
    validate_dependency_graph(m,g)
    engine=p1 if index==0 else m1
    assert g['compartments']==list(engine.COMPARTMENTS)
    if index:
        assert g['edges']==[dict(name=e.name,source=e.source,target=e.target,kind=e.kind) for e in engine.EDGES]
        np.testing.assert_array_equal(g['incidence'],engine.INCIDENCE)
    else:
        q=np.arange(1.,7.)
        np.testing.assert_array_equal(np.array(g['incidence'])@q,np.roll(q,1)-q)
        assert [e['name'] for e in g['edges']]==list(engine.FLOW_NAMES)
        assert [i for i,e in enumerate(g['edges']) if e['kind']=='diode']==list(engine.VALVE_INDICES)
    assert sum(e['kind']=='diode' for e in g['edges'])==4
    assert sum(e['kind']=='resistor' for e in g['edges'])==(2 if index==0 else 4)
    np.testing.assert_array_equal(np.array(g['incidence']).sum(axis=0),0)
    for c in engine.COMPARTMENTS:
        assert 'unstressed_volumes.'+c in law_for(m,'P_'+c)['inputs']
        assert law_for(m,'V_'+c,'initialization')['inputs']==['initial_volumes.'+c]
        balance=law_for(m,'rhs['+c+']')
        assert balance['coefficients']=={'Q_'+e['name']:int(g['incidence'][list(engine.COMPARTMENTS).index(c)][j])
                                        for j,e in enumerate(g['edges']) if g['incidence'][list(engine.COMPARTMENTS).index(c)][j]}
    assert set(law_for(m,'activation')['inputs'])=={'time','period','systolic_fraction'}
    for c in ('lv','rv'):
        assert set(law_for(m,'E_'+c)['inputs'])=={'activation','emin_'+c,'emax_'+c}
    for e in g['edges']:
        assert set(law_for(m,'Q_'+e['name'])['inputs'])=={'P_'+e['source'],'P_'+e['target'],'resistance_'+e['name']}
        assert law_for(m,'Q_cum_'+e['name'])['inputs']==['Q_'+e['name'],'time']
    expected={m.quantity(n).name for cat in ('metric','cumulative_metric','agent_metric','diagnostic_metric') for n in m.inventory.get(cat,())}
    assert expected <= {o for l in g['laws'] for o in l['outputs']}
    for l in g['laws']:
        assert l['equation'] and l['evidence'] and l['temporal']
        for name in l['inputs']+l['outputs']: assert m.quantity(name)
    ef=law_for(m,'lv_ejection_fraction' if index==0 else 'lv_ejection_fraction_sample')
    assert set(ef['inputs'])==({'lv_edv_ml','lv_esv_ml'} if index==0 else {'lv_edv_sample_ml','lv_esv_sample_ml'})
    for output, omitted in [('P_lv','unstressed_volumes.lv'),('E_lv','emax_lv'),('activation','systolic_fraction')]:
        bad=deepcopy(g); l=next(l for l in bad['laws'] if output in l['outputs']);l['inputs'].remove(omitted)
        with pytest.raises(ValueError):validate_dependency_graph(m,bad)
    bad=deepcopy(g);bad['edges'][0]['source'],bad['edges'][0]['target']=bad['edges'][0]['target'],bad['edges'][0]['source']
    # Still mass balanced; named endpoint contract must reject it.
    bad['incidence']=(-np.array(bad['incidence'])).tolist()
    with pytest.raises(ValueError):validate_dependency_graph(m,bad)


def test_resistance_segments_notes_and_evidence():
    from physiosim.ontology.resistance import resistance_details
    details=resistance_details()
    assert set(details)=={'systemic','pulmonary'}
    ledger=json.loads((ROOT/'docs/evidence/resistance/sources.json').read_text())
    terms=json.loads((ROOT/'docs/evidence/resistance/terms.json').read_text())
    sources={s['source_id']:s for s in ledger['sources']}
    notes=json.loads((ROOT/'docs/evidence/resistance/approved_notes.json').read_text())
    citations=json.loads((ROOT/'docs/evidence/b_citations.json').read_text())['sources']
    ontology_sources=json.loads((ROOT/'docs/ontology_sources.json').read_text())
    for bed,d in details.items():
        assert d['note']==notes[bed]
        assert d['numeric_binding']=='NONE' and d['relation']=='traverses'
        assert len(d['segments'])==6 if bed=='systemic' else len(d['segments'])==5
        for seg in d['segments']:
            if seg['term_id'] is None:
                assert seg['key']=='local:small_arteries' and seg['status']=='unknown'
            else:
                t=terms[seg['term_id']]
                assert (seg['label'],seg['iri'],seg['fma_xrefs'])==(t['label'],t['iri'],t['fma_xrefs'])
        for pointer in d['evidence']:
            s=sources[pointer['source_id']]
            assert (pointer['url'],pointer['sha256'])==(s['url'],s['sha256'])
            assert (ROOT/pointer['excerpt_file']).is_file()
            assert any(c['url']==s['url'] for c in citations)
        for m in models():
            assert m.paths[bed]['resistance_detail']==d
            assert m.quantity('resistance_'+bed).bearer==m.paths[bed]['id']
    assert len(terms)==13
    assert 'resistance_evidence' in ontology_sources
    assert not list((ROOT/'docs/evidence/resistance').rglob('*.html'))
    assert not (ROOT/'docs/evidence/resistance/raw').exists()
    assert '46/34/20%' in details['pulmonary']['note']
    assert 'sum 86%' in details['pulmonary']['note']
    assert 'equal flow' in details['systemic']['note']


def test_adapters_resolve_canonical_laws_and_common_reference():
    from physiosim.ontology import cardiovascular_registry, build_graph, BASE
    from physiosim.ontology.four_chamber_m1_manifest import build_m1_manifest
    from physiosim.ontology.representation import pressure_reference
    from rdflib import URIRef
    p,m=models();r=cardiovascular_registry()
    assert set(r['P_lv'].depends_on)=={'V_lv','unstressed_volumes.lv','E_lv'}
    assert set(r['E_lv'].depends_on)=={'activation','emin_lv','emax_lv'}
    assert r['E_lv'].bearer=='organ'
    manifest=build_m1_manifest()
    assert manifest['pressure_reference_contract']==pressure_reference()
    assert manifest['variables']['P_la']['pressure_differential']['source']==m.quantity('V_la').bearer
    assert manifest['variables']['P_la']['reference_id']==r['P_lv'].reference
    g=build_graph().graph(URIRef(BASE+'graph/model-assertions'))
    assert (URIRef(r['P_lv'].uri),URIRef(BASE+'dependsOn'),URIRef(BASE+'phase1/quantity/unstressed_volumes.lv')) in g
    for l in p.dependency_graph['laws']:
        uri=URIRef(BASE+l['id'].replace(':','/'))
        assert (uri,URIRef(BASE+'lawKind'),None) in g
    for term in (URIRef(BASE+'phase1/quantity/'+n) for n in r['P_lv'].depends_on):
        assert (term,None,None) in g
    for field in ('blood_entities','pressure_differentials','dependency_graph'):
        with pytest.raises(ValueError):replace(p,**{field:{}})


def test_legacy_reference_negatives_and_path_adapter():
    from physiosim.ontology import cardiovascular_registry, validate_connection, SemanticConnectionError
    from physiosim.ontology.four_chamber_m1_manifest import build_m1_manifest
    r=cardiovascular_registry();p=r['P_lv']
    for change in ({'pressure_differential':None},{'blood_entity':'phase1:blood:rv'},
                   {'pressure_differential':{'source':'phase1:blood:rv','sink':'atmosphere','reference':p.reference}}):
        bad=replace(p,**change)
        with pytest.raises(SemanticConnectionError):validate_connection(bad,bad)
    m=build_m1_manifest()
    for e in ('systemic','pulmonary'):
        param=m['parameter_contract']['resistance_'+e]
        assert param['bearer']=='four_chamber_m1:path:'+e
        assert param['resistance_detail']['numeric_binding']=='NONE'
