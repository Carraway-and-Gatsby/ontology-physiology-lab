"""Synthetic fault injection, not a human productivity experiment."""
from dataclasses import replace
import pint
from physiosim.ontology import (cardiovascular_registry, validate_connection,
                               SemanticConnectionError, UnitConversion)


def run_benchmark(result=None):
    r = cardiovascular_registry()
    p, q = r['P_lv'], r['Q_aortic']
    # Truth is explicitly assigned, not computed by the validator under test.
    cases = [
        ('same_pressure', p, replace(p, name='consumer_pressure'), None, True),
        ('same_flow', q, replace(q, name='consumer_flow'), None, True),
        ('explicit_conversion', p, replace(p, unit='Pa'), UnitConversion('mmHg', 'Pa'), True),
        ('wrong_anatomy', p, r['P_rv'], None, False),
        ('wrong_property', p, r['V_lv'], None, False),
        ('reversed_flow', q, replace(q, orientation=('sa', 'lv')), None, False),
        ('wrong_reference', p, replace(p, reference='absolute pressure'), None, False),
        ('wrong_temporal_context', p, replace(p, temporal_context='complete-beat mean'), None, False),
        ('wrong_dimensions', p, replace(p, unit='mL'), None, False),
        ('missing_conversion', p, replace(p, unit='Pa'), None, False),
        ('wrong_bearer', p, replace(p, bearer='compartment wall'), None, False),
        ('misannotated_payload', p, replace(p, name='RV_data_falsely_labeled_LV'), None, False),
    ]
    units = pint.UnitRegistry()
    rows = []
    for key, source, target, conversion, truth in cases:
        try:
            factor = units.Quantity(1, source.unit).to(target.unit).magnitude
            unit_ok = source.unit == target.unit or conversion is not None
        except pint.PintError:
            factor, unit_ok = None, False
        try:
            validate_connection(source, target, conversion=conversion)
            semantic, reason = True, 'accepted descriptor equivalence'
        except SemanticConnectionError as exc:
            semantic, reason = False, str(exc)
        if key == 'misannotated_payload':
            reason += '; UNSAFE: fixture describes RV data falsely labeled LV; metadata-only check cannot detect this'
        rows.append({'id': key, 'truth': truth, 'manual': True, 'units_only': unit_ok,
                     'semantic': semantic, 'reason': reason, 'unit_factor': factor})
    counts = {}
    for method in ('manual', 'units_only', 'semantic'):
        counts[method] = {
            'true_accept': sum(row[method] and row['truth'] for row in rows),
            'true_reject': sum(not row[method] and not row['truth'] for row in rows),
            'false_accept': sum(row[method] and not row['truth'] for row in rows),
            'false_reject': sum(not row[method] and row['truth'] for row in rows),
        }
    payload_evidence = None
    if result is not None:
        import numpy as np
        lv, rv = result.compartment_names.index('lv'), result.compartment_names.index('rv')
        misleading_descriptor = replace(p, name='RV_data_falsely_labeled_LV')
        connection = validate_connection(misleading_descriptor, p)
        received = connection.convert(result.pressures[:, rv])
        payload_evidence = {
            'actual_payload': 'computed RV pressure array',
            'advertised_quantity': 'LV pressure',
            'validator_accepted': True,
            'mislabeled_pressure_max_error_mmhg': float(np.max(np.abs(received - result.pressures[:, lv]))),
            'scope': 'unsafe output-port binding, not an altered ODE topology',
        }
    return {'kind': 'synthetic fault-injection benchmark', 'fixture_count': len(rows),
            'payload_evidence': payload_evidence,
            'fixtures': rows, 'counts': counts, 'human_integration_effort': 'not measured',
            'limitations': 'Hand-designed descriptors, not independent held-out tasks. Manual is a scripted unguarded baseline. No clinical or general model-composition validity established.'}
