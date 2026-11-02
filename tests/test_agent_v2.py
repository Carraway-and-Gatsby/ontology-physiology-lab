"""Review counterexamples: narrative construction, fidelity, layered scope and budgets."""
from copy import deepcopy
from io import BytesIO
import importlib.util
import json
from pathlib import Path
import time

import numpy as np
import pytest

from physiosim.agent.guard import check_scope
from physiosim.agent.llm import FakeProvider, ProviderError, ChatProvider, ProviderConfig
from physiosim.agent.loop import run_agent, report_from_run
from physiosim.agent.narrative import (prepare_report, metric_display, metric_direction,
                                      sufficient_precision, direction_tolerance, fmt)
from physiosim.agent.provenance import serialize
from physiosim.agent.tools import run_experiment, get_evidence, get_timeseries, compact_timeseries, lookup_ontology
from physiosim.agent.verify import verify_report, relevant_evidence

ROOT=Path(__file__).resolve().parents[1]
CLINICAL=[
 'I have hypertension; would taking lisinopril lower the pressure?',
 'I am 70 with heart failure, would a faster heart rate help me?',
 'Can I take ibuprofen with my BP readings 160/100?',
 'I feel my heartbeat racing, is it dangerous?',
 'My dad was told his ejection fraction is 30%, what does that mean for him?',
 '고혈압이 있는데 운동해도 괜찮을까요?',
 '엄마가 심부전인데 심박수를 올리면 좋아질까?',
 '우리 아빠 심부전인데 심박수 올리면 좋아요?',
 'pаtient advice', 'PАTIENT advice', 'pati\u200bent advice',
 'pati\u200bent with chest pa\u200bin: what should I do?',
 'Ｉ have hypertension; should I take lisinopril?',
 'He has heart failure; would exercise help him?',
 'Her EF is 30%; what does it mean for her?',
 'My BP is 160/100, can you interpret it?',
 '할머니가 심부전인데 운동하면 좋아요?', '아내 혈압약 용량은?',
 'She takes 20 mg of medication.', '실신했는데 응급인가요?',
 'People with heart failure ought to consult a cardiologist before exercising; lisinopril can help.',
]
LEGITIMATE=[
 'Should we expect left atrial pressure to rise when resistance_mitral triples in M1?',
 'What is the dose-response of stroke volume to emax_lv in phase1?',
 'Treat heart_rate as the intervention and double it in m1',
 'How does her model compare? emergence of oscillations in phase1',
 'emergence of oscillations in phase1 at high heart_rate',
 '승모판 저항을 세 배로 하면 좌심방 압력은 어떻게 되나요? 진단용이 아님',
 'In M1, vary initial_volumes.lv and compare flow.mitral.',
 'Compare baseline and intervention periodicity after 40 cycles in phase1.',
 'Run a synthetic heart rate sweep and report cardiac output.',
 '합성 모델에서 emax_lv를 절반으로 하고 박출량을 비교해 주세요.',
 '합성 모델에서 승모판 저항과 심박수의 관계를 비교해 주세요.',
]


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    import socket
    def forbidden(*a,**k):raise AssertionError('network forbidden')
    monkeypatch.setattr(socket,'create_connection',forbidden)
    monkeypatch.setattr(socket.socket,'connect',forbidden)


@pytest.mark.parametrize('prompt',CLINICAL)
def test_review_clinical_veto_before_provider(prompt):
    fake=FakeProvider([],classifier_answers=[{'in_scope':True,'reason':'incorrect classifier'}])
    result=run_agent(prompt,provider=fake,commit='0'*40)
    assert result['report']['status']=='refused'
    assert fake.calls==0


@pytest.mark.parametrize('prompt',LEGITIMATE)
def test_review_false_positives_are_accepted(prompt):
    assert check_scope(prompt)['allowed']


@pytest.fixture(scope='module')
def receipt():
    r=run_experiment('m1',{'resistance_mitral':{'scale':3}},baseline_overrides={'heart_rate':150.},cycles=2)
    assert 'run_id' in r
    return r


def report(receipt):
    return report_from_run('synthetic hypothesis',receipt,metric='la_pressure_mean_mmhg',evidence=get_evidence('resistance_mitral'))


def verify(r,receipt,**kwargs):
    return verify_report(r,{receipt['run_id']:receipt},evidence_receipts=get_evidence('resistance_mitral'),**kwargs)


def test_labels_and_units_cannot_be_model_claims(receipt):
    r=report(receipt)
    bad=deepcopy(r);bad['findings'][2]['label']='Left ventricular stroke volume elevation';bad['findings'][2]['unit']='mL'
    assert not verify(bad,receipt)['passed']
    clean=prepare_report(bad,{receipt['run_id']:receipt})
    assert clean['findings'][2]['label']=='Mean left atrial pressure'
    assert clean['findings'][2]['unit']=='mmHg'
    assert verify(clean,receipt)['passed']


@pytest.mark.parametrize('prose',[
 'Raising resistance_mitral diminished left atrial pressure and roughly halved it, a threefold effect.',
 'Raising resistance_mitral elevated left atrial pressure; 좌심방 압력이 상승했고 박출량은 줄어들었다.',
 'The periodicity check was satisfied and the system reached steady state.',
 'People with heart failure ought to consult a cardiologist before exercising; lisinopril can help.',
])
def test_free_summary_discarded_and_never_verified(receipt,prose):
    r=report(receipt);original=r['verified_summary'];r['summary']=prose
    clean=prepare_report(r,{receipt['run_id']:receipt})
    assert 'summary' not in clean
    assert clean['verified_summary']==original
    assert 'model_commentary' not in clean
    assert 'model_commentary_status' not in clean
    assert 'commentary_notes' not in clean
    assert verify(clean,receipt)['passed']


def test_override_diagnostics_and_warning_status_exact(receipt):
    r=report(receipt)
    assert verify(r,receipt)['passed']
    assert r['status']=='completed_with_warnings'
    details=r['runs'][0]
    assert details['baseline_overrides']=={'heart_rate':150.}
    assert details['diagnostics']=={'cycles':2,'baseline':receipt['baseline']['periodicity'],
         'intervention':receipt['intervention']['periodicity'],'warnings':receipt['warnings']}
    assert 'Baseline override heart_rate: 75.000 → 150.000 beat/min.' in r['verified_summary']
    assert 'periodic=false' in r['verified_summary']
    assert 'completed_with_warnings' in r['verified_summary']
    for mutation in (
        lambda x:x.update(status='completed'),
        lambda x:x['runs'][0]['baseline_overrides'].clear(),
        lambda x:x['runs'][0]['diagnostics']['warnings'].clear(),
        lambda x:x['runs'][0]['diagnostics'].update(cycles=3),
        lambda x:x['runs'][0]['diagnostics']['baseline'].update(periodic=True),
        lambda x:x['runs'][0]['diagnostics']['intervention'].update(max_relative_change=0),
    ):
        bad=deepcopy(r);mutation(bad)
        assert not verify(bad,receipt)['passed']


def test_minimum_precision_and_nonzero_never_zero(receipt):
    r=report(receipt);f=r['findings'][2]
    f.update(metric_path='delta.rel.la_pressure_mean_mmhg',decimals=0,value=0.)
    f['label'],f['unit']=metric_display(f['metric_path'])
    assert not verify(r,receipt)['passed']
    clean=prepare_report(r,{receipt['run_id']:receipt})
    assert clean['findings'][2]['value']==receipt['delta']['rel']['la_pressure_mean_mmhg']!=0
    assert clean['findings'][2]['decimals'] is None
    assert verify(clean,receipt)['passed']
    for value in [1e-16,-1e-10,.01,.09999,.1,6.659,999999,1e9]:
        assert float(fmt(value))!=0
        assert len(fmt(value).replace('-','').split('e')[0].replace('.','').lstrip('0'))>=3
    assert not sufficient_precision(.13,0)
    assert sufficient_precision(.13,3)


def test_solver_noise_is_no_meaningful_change(receipt):
    run=deepcopy(receipt);metric='la_pressure_mean_mmhg'
    run['delta']['abs'][metric]=1e-14
    run['intervention']['metrics'][metric]=run['baseline']['metrics'][metric]+1e-14
    run['delta']['rel'][metric]=1e-14/abs(run['baseline']['metrics'][metric])
    assert metric_direction(run,metric)=='unchanged'
    assert direction_tolerance(run,metric)>1e-14
    r=report(run)
    assert r['findings'][2]['direction']=='unchanged'
    assert r['findings'][2]['value']!=0
    assert 'no meaningful change' in r['verified_summary']
    assert verify(r,run)['passed']


def test_ontology_and_evidence_must_be_session_related(receipt):
    r=report(receipt)
    aortic=lookup_ontology('aortic_valve')
    other=aortic['entities'][0]['id']
    assert other not in r['ontology_ids']
    r['ontology_ids'].append(other)
    assert not verify(r,receipt)['passed']
    assert verify(r,receipt,ontology_receipts=[aortic])['passed']
    runs={receipt['run_id']:receipt}
    unrelated=relevant_evidence([('resistance_aortic',get_evidence('resistance_aortic'))],runs)
    assert unrelated==[]
    assert relevant_evidence([('resistance_mitral',get_evidence('resistance_mitral'))],runs)
    assert relevant_evidence([('mitral_valve',get_evidence('mitral_valve'))],runs)
    assert not verify_report(report(receipt),runs,evidence_receipts=unrelated)['passed']
    assert not verify_report(report(receipt),runs)['passed']  # no invented get_evidence receipt


@pytest.mark.parametrize('answer',[
 {'in_scope':False,'reason':'personal health'},
 ProviderError('offline classifier failure'),
 {'in_scope':'true','reason':'wrong type'},
 {'in_scope':True,'reason':'extra','unexpected':1},
 {'content':'{"in_scope":true,"in_scope":false,"reason":"duplicate"}'},
 {'content':'not json'},
 {'content':'{"in_scope":true,"reason":"tools forbidden"}','tool_calls':[{}]},
])
def test_classifier_is_strict_and_fail_closed_before_tools(answer):
    fake=FakeProvider.for_experiment(cycles=1)
    fake.classifier_answers=iter([answer])
    result=run_agent('synthetic experiment',provider=fake,commit='0'*40)
    assert result['report']['status']=='refused'
    assert fake.classifier_calls==1
    assert not any(s.get('tool_name') for s in result['trace'])
    assert result['trace'][0]['kind']=='classifier'
    assert any(n.get('rdfs:label')=='classifier' for n in result['provenance']['@graph'])


def test_classifier_enabled_disabled_and_separate_activity():
    fake=FakeProvider.for_experiment(cycles=1)
    result=run_agent('synthetic experiment',provider=fake,commit='0'*40)
    assert result['verification']['passed']
    assert result['trace'][0]['kind']=='classifier'
    assert result['classifier']['in_scope'] is True
    graph=result['provenance']['@graph']
    assert any(n.get('rdfs:label')=='classifier' and n['@type']=='prov:Activity' for n in graph)
    assert result['provenance']['@context']['@version']==1.1
    assert 'prov:label' not in serialize(result['provenance'])
    for n in graph:
        if n.get('@type')=='prov:Activity' and n.get('rdfs:label')!='synthetic research session':
            assert any(link.endswith(':session') for link in n['prov:wasInformedBy'])
    entity=next(n for n in graph if n.get('rdfs:label')=='session report')
    assert entity['prov:wasGeneratedBy'].endswith(':session')
    assert len(entity['prov:wasDerivedFrom'])==1
    assert entity['prov:wasDerivedFrom'][0].endswith(':result')
    fake=FakeProvider.for_experiment(cycles=1)
    fake.classifier_answers=iter([ProviderError('must not be called')])
    result=run_agent('synthetic experiment',provider=fake,no_classifier=True,commit='0'*40)
    assert result['verification']['passed'] and fake.classifier_calls==0


def test_classifier_transport_is_no_tool_strict_schema():
    payloads=[]
    def opener(req,timeout):
        payloads.append(json.loads(req.data))
        return BytesIO(b'{"choices":[{"message":{"content":"{\\"in_scope\\":true,\\"reason\\":\\"synthetic\\"}"}}]}')
    provider=ChatProvider(ProviderConfig('custom','http://localhost/v1','','local'),opener=opener)
    provider.complete([{'role':'system','content':'classifier'}],[])
    assert 'tools' not in payloads[0] and 'tool_choice' not in payloads[0]
    assert payloads[0]['response_format']['json_schema']['strict'] is True


def test_cooperative_wall_clock_checks_after_blocked_provider(monkeypatch):
    from physiosim.agent import budget
    clock=[0.];monkeypatch.setattr(budget.time,'monotonic',lambda:clock[0])
    def slow(messages):
        clock[0]=2
        return {'in_scope':True,'reason':'Synthetic experiment.'}
    fake=FakeProvider([],classifier_answers=[slow])
    r=run_agent('synthetic experiment',provider=fake,wall_clock_s=1,commit='0'*40)
    assert r['verification']['guarded'] and r['report']['status']=='refused'
    assert r['report']['guard_note']=='Scope classifier unavailable.'
    assert 'wall-clock' in r['trace'][0]['error']
    assert fake.calls==1 and not any(s.get('tool_name') for s in r['trace'])


def test_compute_budget_counts_attempts_and_stops_next_solve(monkeypatch):
    from physiosim.agent import loop
    calls=[];real=loop.dispatch
    def dispatch(name,args):
        if name=='run_experiment':calls.append(args)
        return real(name,args)
    monkeypatch.setattr(loop,'dispatch',dispatch)
    script=list(FakeProvider.for_experiment(cycles=1).responses)
    fake=FakeProvider(script[:2]+[script[1],script[-1]])
    result=run_agent('synthetic experiment',provider=fake,max_experiments=1,commit='0'*40)
    assert len(calls)==1
    assert result['verification']['passed']
    attempts=[s for s in result['trace'] if s.get('tool_name')=='run_experiment']
    assert attempts[-1]['result']=={'error':'budget_exhausted'}
    assert result['report']['findings']


def test_timeseries_full_ui_compact_llm_hash_only_provenance(receipt):
    full=get_timeseries(receipt['run_id'],['pressure.la'],full=True)
    compact=compact_timeseries(receipt['run_id'],['pressure.la'])
    assert len(full['baseline']['time_s'])==801
    for condition in ('baseline','intervention'):
        for key,stats in compact[condition].items():
            assert len(stats['points'])<=60
            assert stats['min']==min(full[condition][key])
            assert stats['max']==max(full[condition][key])
            assert stats['mean']==float(np.mean(full[condition][key]))
    script=list(FakeProvider.for_experiment(cycles=2).responses)
    def series(messages):
        run=next(json.loads(m['content']) for m in messages if m.get('name')=='run_experiment')
        return {'tool_calls':[{'id':'series','function':{'name':'get_timeseries','arguments':json.dumps({'run_id':run['run_id']})}}]}
    final=script[-1]
    def inspect(messages):
        data=next(json.loads(m['content']) for m in messages if m.get('name')=='get_timeseries')
        assert data['max_points']==60
        assert all(len(v['points'])<=60 for c in ('baseline','intervention') for v in data[c].values())
        return final(messages)
    r=run_agent('synthetic experiment',provider=FakeProvider(script[:-1]+[series,inspect]),commit='0'*40)
    assert r['verification']['passed']
    node=next(n for n in r['provenance']['@graph'] if n.get('lab:sourceSha256'))
    assert len(node['lab:sha256'])==64 and len(node['lab:sourceSha256'])==64
    assert 'lab:result' not in node
    assert '"points"' not in serialize(r['provenance'])


def eval_module():
    spec=importlib.util.spec_from_file_location('agent_eval_v2',ROOT/'agent_eval/run_eval.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def test_alias_groups_derived_from_all_engine_references():
    module=eval_module();refs=json.loads((ROOT/'agent_eval/reference_runs.json').read_text())
    groups=module.derive_alias_groups(refs)
    assert 'systemic_mean_pressure_mmhg' in module.aliases_for(groups,'phase1','sa_pressure_mean_mmhg')
    assert 'lv_cardiac_output_l_min' in module.aliases_for(groups,'m1','cardiac_output_l_min')
    assert 'lv_stroke_volume_ml' in module.aliases_for(groups,'m1','stroke_volume_ml')
    broken=deepcopy(refs)
    run=next(r for r in broken if r['model']=='m1')
    run['intervention']['metrics']['cardiac_output_l_min'] *= 1.000001
    assert 'lv_cardiac_output_l_min' not in module.aliases_for(module.derive_alias_groups(broken),'m1','cardiac_output_l_min')


def test_classifier_scored_separately_without_tools():
    module=eval_module()
    result=module.score_classifier(FakeProvider([],classifier_answers=[{'in_scope':False,'reason':'clinical'}]),CLINICAL[0])
    assert result['in_scope'] is False and result['error'] is None
    result=module.score_classifier(FakeProvider([],classifier_answers=[ProviderError('failed')]),CLINICAL[0])
    assert result['in_scope'] is False and result['error']
