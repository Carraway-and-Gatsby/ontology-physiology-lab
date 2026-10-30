"""Bindings from the implemented engine to annotations, with checked rescaling.

This exposes model output ports. It does not dynamically assemble ODE topology.
"""
import numpy as np
from physiosim.models.cardiovascular import elastance
from physiosim.ontology import cardiovascular_registry, validate_connection


def observations(result):
    p = result.parameters
    bound = {}
    for i, compartment in enumerate(result.compartment_names):
        bound['V_' + compartment] = result.volumes[:, i]
        bound['P_' + compartment] = result.pressures[:, i]
        if compartment not in ('lv', 'rv'):
            bound['C_' + compartment] = getattr(p, 'compliance_' + compartment)
    e = np.array([elastance(t, p) for t in result.time])
    bound['E_lv'], bound['E_rv'] = e[:, 0], e[:, 1]
    for i, edge in enumerate(result.flow_names):
        bound['Q_' + edge] = result.flows[:, i]
        bound['R_' + edge] = getattr(p, 'resistance_' + edge)
    metrics = result.metrics()
    bound.update(HR=p.heart_rate, CO=metrics['cardiac_output_l_min'] * 1000 / 60,
                 SV=metrics['stroke_volume_ml'], V_total=result.volumes.sum(axis=1))
    return bound


def connect_value(result, source_name, target_annotation, *, conversion=None):
    """Validate a producer-to-consumer equivalence before transferring a value."""
    source = cardiovascular_registry()[source_name]
    connection = validate_connection(source, target_annotation, conversion=conversion)
    return connection.convert(observations(result)[source_name])
