"""Integration contracts must describe the actual numerical observable."""
from physiosim.ontology import cardiovascular_registry


def test_stroke_volume_annotation_matches_forward_flow_metric():
    annotation = cardiovascular_registry()['SV']
    assert annotation.equation == 'SV = integral(Q_aortic, complete_beat)'
    # ONTO-R2: sampled complete-beat definition also resolves time and beat selection.
    assert annotation.depends_on == ('Q_aortic', 'time', 'solver.samples_per_cycle')
    assert annotation.bearer == 'flow process'


def test_all_annotations_bind_to_real_values_and_conversion_is_applied():
    import importlib.util
    import numpy as np
    from dataclasses import replace
    from physiosim.models import Parameters
    from physiosim.simulation import simulate
    from physiosim.ontology import UnitConversion
    assert importlib.util.find_spec('physiosim.ontology.bindings') is not None, 'Missing executable binding'
    from physiosim.ontology.bindings import observations, connect_value
    result = simulate(Parameters(), cycles=2, samples_per_cycle=20)
    bound = observations(result)
    registry = cardiovascular_registry()
    assert set(bound) == set(registry)
    np.testing.assert_array_equal(bound['V_lv'], result.volumes[:, 0])
    np.testing.assert_array_equal(bound['P_sa'], result.pressures[:, 1])
    assert bound['CO'] == result.metrics()['cardiac_output_l_min'] * 1000 / 60
    target = replace(registry['CO'], name='consumer_CO', unit='L/min')
    value = connect_value(result, 'CO', target, conversion=UnitConversion('mL/s', 'L/min'))
    np.testing.assert_allclose(value, result.metrics()['cardiac_output_l_min'], rtol=1e-14)


def test_registry_has_model_source_and_scenario_contexts():
    registry = cardiovascular_registry()
    for value in registry.values():
        assert value.source_document == 'docs/physiology.md'
        assert 'reduced_contractility' in value.applicable_contexts
        assert 'partial_contractility_restoration' in value.applicable_contexts
    assert registry['V_lv'].reference == 'not applicable'
    assert 'gauge' in registry['P_lv'].reference


def test_paired_incomplete_descriptors_fail_closed():
    from dataclasses import replace
    import pytest
    from physiosim.ontology import validate_connection, SemanticConnectionError
    r = cardiovascular_registry()
    p = r['P_lv']
    incomplete = [replace(p, reference=''), replace(p, anatomy=replace(p.anatomy, uri='')),
                  replace(p, unit=' '), replace(p, temporal_context=''),
                  replace(p, biological_context=()), replace(p, source_context=''),
                  replace(r['Q_aortic'], orientation=None)]
    for bad in incomplete:
        with pytest.raises(SemanticConnectionError, match='incomplete'):
            validate_connection(bad, bad)
