"""M1 topology and laws; bounds preregistered in physiology_four_chamber_m1.md."""
from dataclasses import replace, fields
import numpy as np
import pytest
from physiosim.models import four_chamber_m1 as m
from physiosim.models.cardiovascular import elastance


def fixture():
    # Every number is an explicit test-design input, not literature physiology.
    return m.FourChamberM1Parameters(
        heart_rate=75., systolic_fraction=.4, emin_lv=.06, emax_lv=2.5,
        emin_rv=.03, emax_rv=.8, elastance_la=.15, elastance_ra=.1,
        compliance_sa=1.5, compliance_sv=100., compliance_pa=5., compliance_pv=20.,
        resistance_aortic=.01, resistance_systemic=1., resistance_venous_return=.05,
        resistance_tricuspid=.01, resistance_pulmonary_valve=.01, resistance_pulmonary=.1,
        resistance_pulmonary_venous=.05, resistance_mitral=.01,
        unstressed_volumes=(10.,700.,2500.,20.,10.,100.,400.,20.),
        initial_volumes=(140.,850.,3200.,60.,140.,180.,490.,60.))


def test_topology_and_mutation():
    assert m.COMPARTMENTS == ('lv','sa','sv','ra','rv','pa','pv','la')
    expected = [('aortic','lv','sa','diode'),('systemic','sa','sv','resistor'),
                ('venous_return','sv','ra','resistor'),('tricuspid','ra','rv','diode'),
                ('pulmonary_valve','rv','pa','diode'),('pulmonary','pa','pv','resistor'),
                ('pulmonary_venous','pv','la','resistor'),('mitral','la','lv','diode')]
    assert [(e.name,e.source,e.target,e.kind) for e in m.EDGES] == expected
    literal = np.array([[-1,0,0,0,0,0,0,1],[1,-1,0,0,0,0,0,0],
        [0,1,-1,0,0,0,0,0],[0,0,1,-1,0,0,0,0],[0,0,0,1,-1,0,0,0],
        [0,0,0,0,1,-1,0,0],[0,0,0,0,0,1,-1,0],[0,0,0,0,0,0,1,-1]])
    np.testing.assert_array_equal(m.INCIDENCE, literal)
    np.testing.assert_array_equal(np.ones(8) @ m.INCIDENCE, 0)
    edges = list(m.EDGES)
    edges[-1] = replace(edges[-1], source='lv', target='la')
    with pytest.raises(ValueError): m.validate_topology(m.COMPARTMENTS, edges)
    # Mass conservation alone would not reject a swapped but still conservative edge.
    edges = list(m.EDGES)
    edges[1] = replace(edges[1], target='ra')
    edges[2] = replace(edges[2], target='sv')
    with pytest.raises(ValueError): m.validate_topology(m.COMPARTMENTS, edges)
    broken = literal.copy(); broken[0,0] = 1
    with pytest.raises(ValueError): m.validate_incidence(broken)


def test_parameter_and_shape_validation():
    with pytest.raises(TypeError): m.FourChamberM1Parameters()
    p = fixture()
    for f in fields(p):
        if f.name.endswith('volumes'):
            for value in [(1.,)*7, (float('nan'),)*8, (True,)*8, (-1.,)*8]:
                with pytest.raises(ValueError): replace(p, **{f.name:value})
        else:
            for value in [True, '1', 0., -1., float('nan'), float('inf')]:
                with pytest.raises(ValueError): replace(p, **{f.name:value})
    for changes in [dict(emax_lv=.01),dict(emax_rv=.01),dict(systolic_fraction=1.)]:
        with pytest.raises(ValueError): replace(p, **changes)
    for v in [np.zeros(7), np.zeros((1,8)), [float('nan')]*8]:
        with pytest.raises(ValueError): m.pressures(0, v, p)
        with pytest.raises(ValueError): m.edge_flows(v, p)
    with pytest.raises(ValueError): m.pressures(float('nan'), p.initial_volumes, p)
    # Freeze caller-owned mutable inputs, not just the dataclass attributes.
    values = list(p.initial_volumes); q = replace(p, initial_volumes=values)
    values[0] = 999
    assert q.initial_volumes[0] == 140


def test_pressure_and_flow_laws():
    p = fixture(); v = np.array(p.initial_volumes)
    for t in [0.,.1,.3,.6]:
        pr = m.pressures(t,v,p); el, er = elastance(t,p)
        assert pr[0] == el*(v[0]-p.unstressed_volumes[0])
        assert pr[4] == er*(v[4]-p.unstressed_volumes[4])
        assert pr[3] == p.elastance_ra*40
        assert pr[7] == p.elastance_la*40
    assert 'common fixed external pressure of 0 mmHg' in m.PRESSURE_REFERENCE
    for pr in [np.arange(8.), np.arange(8.)[::-1]]:
        q = m.edge_flows(pr,p)
        for i,e in enumerate(m.EDGES):
            dp = pr[m.COMPARTMENTS.index(e.source)]-pr[m.COMPARTMENTS.index(e.target)]
            expected = dp/getattr(p,'resistance_'+e.name)
            assert q[i] == (max(expected,0.) if e.kind == 'diode' else expected)
        np.testing.assert_array_equal(m.rhs(0,v,p), m.INCIDENCE@m.edge_flows(m.pressures(0,v,p),p))
    assert m.edge_flows(np.arange(8.),p)[1] < 0


def test_mixed_boolean_volume_is_not_a_numeric_input():
    p=fixture()
    for field in ['initial_volumes','unstressed_volumes']:
        values=list(getattr(p,field)); values[0]=True
        with pytest.raises(ValueError): replace(p,**{field:values})
