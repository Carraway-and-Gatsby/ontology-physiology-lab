from importlib import import_module


def test_registry_has_complete_semantic_metadata():
    import importlib.util
    assert importlib.util.find_spec('physiosim.ontology') is not None, 'ontology module missing'
    api = import_module('physiosim.ontology')
    registry = api.cardiovascular_registry()
    assert len(registry) >= 30
    for variable in registry.values():
        assert all((variable.name, variable.anatomy, variable.property, variable.unit,
                    variable.equation, variable.source_context, variable.role))
    assert registry['P_lv'].property.label == 'Fluid pressure'
    assert registry['V_lv'].anatomy.label == 'Left ventricle'
    assert registry['Q_aortic'].orientation == ('lv', 'sa')
    assert {'HR', 'CO', 'SV', 'V_total'} <= registry.keys()


def test_connections_reject_semantic_mismatches_and_require_conversion_contract():
    from dataclasses import replace
    import pytest
    api = import_module('physiosim.ontology')
    assert hasattr(api, 'validate_connection'), 'connection validator missing'
    r = api.cardiovascular_registry()
    p = r['P_lv']
    assert api.validate_connection(p, p).convert(120) == 120
    for altered, reason in [(replace(p, anatomy=r['P_rv'].anatomy), 'anatomy'),
                            (replace(p, property=r['V_lv'].property), 'property'),
                            (replace(p, unit='mL'), 'units'),
                            (replace(p, reference='absolute'), 'reference'),
                            (replace(p, temporal_context='mean'), 'temporal')]:
        with pytest.raises(api.SemanticConnectionError, match=reason):
            api.validate_connection(p, altered)
    pa = replace(p, unit='Pa')
    with pytest.raises(api.SemanticConnectionError, match='explicit'):
        api.validate_connection(p, pa)
    contract = api.UnitConversion('mmHg', 'Pa')
    connection = api.validate_connection(p, pa, conversion=contract)
    assert connection.convert(1) == pytest.approx(133.322387415)
    with pytest.raises(api.SemanticConnectionError, match='contract'):
        api.validate_connection(p, pa, conversion=api.UnitConversion('Pa', 'mmHg'))
    q = r['Q_aortic']
    with pytest.raises(api.SemanticConnectionError, match='orientation'):
        api.validate_connection(q, replace(q, orientation=('sa', 'lv')))
    with pytest.raises(api.SemanticConnectionError, match='orientation'):
        api.validate_connection(q, replace(q, orientation=None))
    hr = r['HR']
    assert api.validate_connection(hr, replace(hr, unit='1/s'),
        conversion=api.UnitConversion('1/min', '1/s')).convert(60) == pytest.approx(1)


def test_graph_preserves_provenance_without_asserting_ontology_entailments():
    from rdflib import Dataset, URIRef
    from rdflib.namespace import RDF, RDFS, OWL
    api = import_module('physiosim.ontology')
    assert hasattr(api, 'build_graph'), 'RDF graph builder missing'
    r = api.cardiovascular_registry()
    ds = api.build_graph(r)
    model = ds.graph(URIRef(api.BASE + 'graph/model-assertions'))
    evidence = ds.graph(URIRef(api.BASE + 'graph/verified-labels'))
    assert len(model) > len(r)
    assert (URIRef(r['P_lv'].property.uri), RDFS.label, None) in evidence
    assert (URIRef(r['P_lv'].uri), URIRef(api.BASE + 'physicalProperty'),
            URIRef(r['P_lv'].property.uri)) in model
    assert not list(model.triples((None, RDFS.subClassOf, None)))
    assert not list(model.triples((None, OWL.sameAs, None)))
    assert not list(evidence.triples((None, URIRef(api.BASE + 'dependsOn'), None)))
    serialized = api.export_graph(r, format='trig')
    loaded = Dataset()
    loaded.parse(data=serialized, format='trig')
    assert len(loaded) == len(ds)
    assert 'model-assertions' in serialized


def test_identical_wrong_units_are_not_a_valid_pressure_connection():
    from dataclasses import replace
    import pytest
    api = import_module('physiosim.ontology')
    bad = replace(api.cardiovascular_registry()['P_lv'], unit='mL')
    with pytest.raises(api.SemanticConnectionError, match='property.*units'):
        api.validate_connection(bad, bad)


def test_every_external_concept_label_matches_saved_source_evidence():
    import json
    from pathlib import Path
    import xml.etree.ElementTree as ET
    api = import_module('physiosim.ontology')
    root = Path(__file__).resolve().parents[1]
    ols = json.loads((root / 'docs/evidence/b_ols_terms.json').read_text())
    evidence = {d['iri']: d['label'] for q in ols for d in q['records']}
    for q in ols:
        assert q['provenance']['sha256'] and q['provenance']['retrieved_at']
    opb = json.loads((root / 'docs/evidence/b_opb_excerpt.json').read_text())
    for text in opb['class_xml']:
        element = ET.fromstring(text)
        evidence[element.attrib['{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about']] = element.find('{http://www.w3.org/2000/01/rdf-schema#}label').text
    for concept in (*api.PROPERTIES.values(), *api.ANATOMY.values(), api.BLOOD, *api.CONTEXTS.values()):
        if concept.local:
            assert concept.uri.startswith(api.BASE)
        else:
            assert evidence[concept.uri] == concept.label


def test_unit_contract_other_quantities_and_serialization_limits():
    from dataclasses import replace
    import pytest
    api = import_module('physiosim.ontology')
    r = api.cardiovascular_registry()
    for name, target_unit, expected in [('V_lv', 'L', .001), ('CO', 'L/min', .06),
                                        ('R_systemic', 'Pa*s/mL', 133.322387415),
                                        ('C_sa', 'mL/Pa', 1/133.322387415)]:
        source = r[name]
        target = replace(source, unit=target_unit)
        c = api.validate_connection(source, target, conversion=api.UnitConversion(source.unit, target_unit))
        assert c.convert(1) == pytest.approx(expected)
    with pytest.raises(ValueError, match='preserve'):
        api.export_graph(format='turtle')
    with pytest.raises(api.SemanticConnectionError, match='property'):
        api.validate_connection(r['CO'], replace(r['Q_aortic'], anatomy=r['CO'].anatomy))
