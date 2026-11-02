"""Real-engine agent boundary tests. No live provider or network requests."""
from copy import deepcopy
from dataclasses import asdict, replace
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest
from scipy.integrate import trapezoid
from physiosim.agent import catalog, tools
from physiosim.models.cardiovascular import Parameters
from physiosim.simulation import simulate
from physiosim.simulation.four_chamber_m1 import simulate_m1, SolverSettings

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    import socket
    def forbidden(*a,**k):
        raise AssertionError('network forbidden in agent tests')
    monkeypatch.setattr(socket,'create_connection',forbidden)
    monkeypatch.setattr(socket.socket,'connect',forbidden)


def test_fixture_matches_real_demo_exactly():
    from physiosim.experiments.four_chamber_m1_demo import synthetic_fixture
    assert catalog.synthetic_fixture() == synthetic_fixture()


@pytest.mark.parametrize('model',['phase1','m1'])
def test_catalogue_covers_every_engine_default_and_endpoints(model):
    p = catalog.default_parameters(model)
    flat = catalog.flatten(p,model)
    ports = catalog.catalogue(model)
    assert {x['name']:x['default'] for x in ports} == flat
    assert len(ports) == (28 if model == 'phase1' else 36)
    ids = catalog.known_ids()
    for entry in ports:
        assert entry['models'] == [model]
        assert entry['unit'] and entry['description']
        lo,hi = entry['allowed']
        assert lo <= entry['default'] <= hi
        for value in (lo,hi):
            updated,_ = catalog.apply_values(p,model,{entry['name']:value},allow_scale=False)
            assert catalog.flatten(updated,model)[entry['name']] == value
        if entry['binding']:
            for ident in entry['binding']['ids']:
                assert ident['id'] in ids
                assert ident['iri'] is None or ident['iri'] in ids
        else:
            assert 'No anatomical' in entry['binding_note']
    # Every CURIE literally occurs in the real anatomy/source data, not a new ID.
    original = (ROOT/'src/physiosim/ontology/anatomy_nodes_v2.json').read_text()
    for entry in ports:
        if entry['binding']:
            assert all(ident['id'] in original for ident in entry['binding']['ids'])


def test_bundled_knowledge_and_evidence_are_real_repository_records():
    data = catalog.knowledge()
    assert data['anatomy'] == json.loads((ROOT/'src/physiosim/ontology/anatomy_nodes_v2.json').read_text())
    assert data['source'] == json.loads((ROOT/'src/physiosim/ontology/applied_la_mitral_lv_source_v1.json').read_text())
    for path,digest in data['source_sha256'].items():
        assert sha256((ROOT/path).read_bytes()).hexdigest() == digest
    for item in data['evidence']:
        assert (ROOT/item['path']).read_text().splitlines()[item['line']-1] == item['excerpt']
    assert tools.get_evidence('not-a-real-parameter') == []
    assert tools.get_evidence('resistance_mitral')
    assert tools.get_evidence('UBERON:0002135')


def test_lookup_preserves_source_relations_and_null_bindings():
    entities = tools.lookup_ontology('mitral')['entities']
    valve = next(e for e in entities if e['id'] == 'UBERON:0002135')
    assert {'model':'m1','parameter':'resistance_mitral'} in valve['related_parameters']
    assert any(r['label'] == 'part_of' for r in valve['relations'])
    blood = tools.lookup_ontology('blood')['entities']
    assert any(r['label'] == 'located_in' for e in blood for r in e['relations'])
    phase1 = {p['name']:p for p in catalog.catalogue('phase1')}
    assert phase1['compliance_sa']['binding'] is None
    assert phase1['resistance_systemic']['binding'] is None
    assert phase1['resistance_mitral']['binding']['primary_id'] == 'UBERON:0002135'


@pytest.mark.parametrize('args',[
    {'model':'other','intervention':{}},
    {'model':'m1','intervention':{'unknown':2}},
    {'model':'m1','intervention':{'heart_rate':True}},
    {'model':'phase1','intervention':{'heart_rate':float('nan')}},
    {'model':'m1','intervention':{'heart_rate':{'scale':float('inf')}}},
    {'model':'m1','intervention':{'heart_rate':{'scale':False}}},
    {'model':'m1','intervention':{'heart_rate':{'scale':-1}}},
    {'model':'m1','intervention':{'heart_rate':{'scale':2,'other':4}}},
    {'model':'phase1','intervention':{'systolic_fraction':1}},
    {'model':'m1','intervention':{'heart_rate':10000}},
    {'model':'m1','intervention':{'emin_lv':.3,'emax_lv':.25}},
    {'model':'m1','intervention':{},'cycles':True},
    {'model':'m1','intervention':{},'cycles':0},
    {'model':'m1','intervention':{},'cycles':81},
    {'model':'m1','intervention':{},'baseline_overrides':{'heart_rate':{'scale':2}}},
    {'model':'m1','intervention':[]},
])
def test_invalid_requests_are_structured_json_errors(args):
    result = tools.run_experiment(**args)
    assert result['error']['code'] == 'invalid_request'
    json.dumps(result,allow_nan=False)


@pytest.mark.parametrize('model',['phase1','m1'])
def test_tool_metrics_equal_real_engine_methods_and_time_quadrature(model):
    result = tools.run_experiment(model,{'resistance_mitral':{'scale':3}},cycles=3)
    assert 'error' not in result
    settings = result['settings']
    p = catalog.default_parameters(model)
    if model == 'phase1':
        direct = simulate(p,cycles=3,samples_per_cycle=400,**{k:settings[k] for k in ('method','rtol','atol','max_step')})
    else:
        direct = simulate_m1(p,cycles=3,samples_per_cycle=400,settings=SolverSettings(**{k:settings[k] for k in ('method','rtol','atol','max_step')}))
    actual = result['baseline']['metrics']
    for key,value in direct.metrics().items():
        assert actual[key] == value
    beat=direct.final_beat;t=direct.time[beat]
    for i,c in enumerate(direct.compartment_names):
        assert actual[c+'_pressure_mean_mmhg'] == trapezoid(direct.pressures[beat,i],t)/(t[-1]-t[0])
    assert actual['aortic_backward_volume_ml'] == 0
    assert actual['mitral_backward_volume_ml'] == 0
    sv = actual['lv_stroke_volume_ml'] if model == 'm1' else actual['stroke_volume_ml']
    assert actual['cardiac_output_l_min'] == sv/(t[-1]-t[0])*60/1000
    for key,before in actual.items():
        after = result['intervention']['metrics'][key]
        assert result['delta']['abs'][key] == after-before
        assert result['delta']['rel'][key] == ((after-before)/abs(before) if before else None)
    json.dumps(result,allow_nan=False)


def test_hr_pairs_share_identical_explicit_solver_settings(monkeypatch):
    captured = []
    original = tools.simulate_m1
    def run(p,**kw):
        captured.append(kw)
        return original(p,**kw)
    monkeypatch.setattr(tools,'simulate_m1',run)
    result=tools.run_experiment('m1',{'heart_rate':{'scale':1.2}},cycles=2)
    assert captured[0] == captured[1]
    assert result['settings']['max_step'] == (60/90)/200
    assert result['baseline']['duration_s'] != result['intervention']['duration_s']


def test_periodicity_warns_and_one_beat_null_is_strict_json():
    result=tools.run_experiment('phase1',{},cycles=1)
    assert result['baseline']['periodicity']['available'] is False
    assert result['baseline']['metrics']['final_beat_max_volume_difference_ml'] is None
    assert any('threshold' in w for w in result['warnings'])
    json.dumps(result,allow_nan=False)
    p=tools.run_experiment('m1',{},cycles=4)['baseline']['periodicity']
    assert p['comparisons'] == 3
    assert p['periodic'] == (p['max_relative_change'] < p['threshold'])


def test_timeseries_bounded_eviction_copy_and_run_identity(monkeypatch):
    monkeypatch.setattr(tools,'MAX_RUNS',2)
    tools._STORE.clear()
    a=tools.run_experiment('phase1',{},cycles=1)
    b=tools.run_experiment('phase1',{},cycles=2)
    c=tools.run_experiment('phase1',{},cycles=3)
    assert len(tools._STORE) == 2
    assert tools.get_timeseries(a['run_id'])['error']['code'] == 'unknown_run'
    series=tools.get_timeseries(c['run_id'],['pressure.lv','flow.mitral'])
    assert len(series['baseline']['time_s']) <= tools.MAX_SERIES_POINTS
    assert set(series['baseline']) == {'time_s','pressure.lv','flow.mitral'}
    series['baseline']['pressure.lv'][0]=999
    assert tools.get_timeseries(c['run_id'],['pressure.lv'])['baseline']['pressure.lv'][0] != 999
    repeated=tools.run_experiment('phase1',{},cycles=3)
    assert repeated['run_id'] == c['run_id']
    assert repeated['baseline'] == c['baseline']
    assert tools.get_timeseries(c['run_id'],['not-a-series'])['error']
    assert tools.dispatch('unknown',{})['error']
    assert tools.dispatch('run_experiment',{})['error']


def test_engine_failures_never_crash_tool(monkeypatch):
    def fail(*a,**kw):
        raise RuntimeError('deliberate integration failure')
    monkeypatch.setattr(tools,'simulate_m1',fail)
    assert tools.run_experiment('m1',{},cycles=1)['error']['code'] == 'engine_failure'


def test_pyodide_import_and_real_run_with_heavy_modules_blocked():
    code='''import sys, json, socket
sys.modules['rdflib']=None
sys.modules['pint']=None
sys.modules['matplotlib']=None
def forbidden(*a,**k): raise AssertionError('network forbidden')
socket.create_connection=forbidden
socket.socket.connect=forbidden
from physiosim.agent.tools import run_experiment, lookup_ontology, get_evidence
from physiosim.agent import verify, narrative
assert 'physiosim.agent.budget' not in sys.modules
for model in ('phase1','m1'):
 r=run_experiment(model,{'resistance_mitral':{'scale':3}},cycles=2)
 assert 'run_id' in r,r
 json.dumps(r,allow_nan=False)
assert lookup_ontology('mitral')['entities']
assert get_evidence('resistance_mitral')
assert not any(n.startswith(('rdflib.','pint.','matplotlib.')) for n in sys.modules)
print('lightweight import + both real engine runs passed')
'''
    result=subprocess.run([sys.executable,'-B','-c',code],cwd=ROOT,env={**os.environ,'PYTHONPATH':str(ROOT/'src')},capture_output=True,text=True,timeout=30)
    assert result.returncode == 0,result.stdout+result.stderr
    assert 'passed' in result.stdout
