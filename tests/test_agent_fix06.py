"""AGENT-FIX-06: warning-aware recovery and forced-final protocol, offline only."""
from copy import deepcopy
from io import BytesIO
import json
from urllib.error import HTTPError

import pytest

from agent_schema import SCHEMA, validate, validate_report
from physiosim.agent import loop
from physiosim.agent.llm import ChatProvider, FakeProvider, ProviderConfig, ProviderError
from physiosim.agent.narrative import completion_status, prepare_report, verified_summary
from physiosim.agent.selection import select_metrics, selection_basis
from physiosim.agent.tools import get_evidence, run_experiment
from physiosim.agent.verify import verify_report


def call(name,args):
    return {'role':'assistant','tool_calls':[{'id':name,'type':'function','function':{
        'name':name,'arguments':json.dumps(args)}}]}


RUN = call('run_experiment',{'model':'phase1','intervention':{'heart_rate':150},'cycles':1})
EVIDENCE = call('get_evidence',{'entity_or_param':'heart_rate'})


@pytest.fixture(scope='module')
def receipt():
    return run_experiment('phase1',{'heart_rate':150},cycles=1)


@pytest.fixture
def cached(monkeypatch,receipt):
    real=loop.dispatch
    monkeypatch.setattr(loop,'dispatch',lambda name,args:deepcopy(receipt) if name=='run_experiment' else real(name,args))
    return receipt


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    import socket
    def forbidden(*args,**kwargs):
        raise AssertionError('network forbidden in FIX-06 tests')
    monkeypatch.setattr(socket,'create_connection',forbidden)
    monkeypatch.setattr(socket.socket,'connect',forbidden)


def final(receipt,metric='delta.abs.stroke_volume_ml'):
    return {'role':'assistant','content':json.dumps({'model':'phase1','findings':[
        {'run_id':receipt['run_id'],'metric_path':metric}]})}


@pytest.mark.parametrize('basis,hypothesis',[
    ('code_hypothesis_terms','Raise heart rate; compare cardiac output in phase1'),
    ('code_default_set','Raise heart rate; what happens to mean left atrial pressure in phase1?'),
])
def test_auto_status_keeps_warnings_and_verifier_rejects_masking(cached,basis,hypothesis):
    result=loop.run_agent(hypothesis,provider=FakeProvider([RUN]),max_steps=1,commit='0'*40)
    report=result['report'];runs={cached['run_id']:cached}
    assert result['verification']['passed'],result['verification']
    assert report['status']==completion_status(runs)=='completed_with_warnings'
    assert report['finding_selection']==basis
    assert ('hypothesis terms' if basis=='code_hypothesis_terms' else 'the default set') in report['verified_summary']
    assert 'heart_rate_bpm' not in {f['metric_path'].split('.')[-1] for f in report['findings']}
    validate_report(report)
    for wrong in ('completed','completed_auto'):
        tampered=deepcopy(report);tampered['status']=wrong
        tampered['verified_summary']=verified_summary(tampered,runs)
        verification=verify_report(tampered,runs,evidence_receipts=report['evidence'],finding_selection=basis)
        assert any(f['path']=='status' for f in verification['failures'])
        if wrong=='completed_auto':
            with pytest.raises(AssertionError):
                validate(tampered,SCHEMA)


def test_selection_field_is_code_owned_and_verified(receipt):
    runs={receipt['run_id']:receipt};evidence=get_evidence('heart_rate')
    raw={'model':'phase1','finding_selection':'code_default_set','findings':[
        {'run_id':receipt['run_id'],'metric_path':'delta.abs.stroke_volume_ml'}]}
    report=prepare_report(raw,runs,evidence_receipts=evidence)
    assert report['finding_selection']=='model'
    report['finding_selection']='code_default_set'
    report['verified_summary']=verified_summary(report,runs)
    assert any(f['path']=='finding_selection' for f in verify_report(report,runs,evidence_receipts=evidence)['failures'])


def test_fake_provider_nudge_and_repair_requests_retain_schemas(cached):
    p=FakeProvider([RUN,EVIDENCE,EVIDENCE,final(cached,'settings.cycles'),final(cached)])
    result=loop.run_agent('Compare stroke volume in phase1',provider=p,max_steps=8,commit='0'*40)
    assert result['verification']['passed'] and result['verification']['repair_attempted']
    forced=[r for r in p.requests if r['tool_choice']=='none']
    assert len(forced)==2  # One nudge and one repair, both with prior tool history.
    assert forced[0]['messages'][-1]['content']==loop.FINAL_NUDGE
    assert forced[1]['messages'][-1]['content'].startswith('Repair your final JSON')
    for payload in forced:
        assert any(m.get('tool_calls') for m in payload['messages'])
        assert payload['tools']==loop.TOOL_SCHEMAS and payload['tool_choice']=='none'
    assert result['report']['finding_selection']=='model'


@pytest.mark.parametrize('provider,token_field',[('openai','max_completion_tokens'),('anthropic','max_tokens')])
def test_forced_final_http_payloads_with_tool_history(cached,provider,token_field):
    fake=FakeProvider([RUN,EVIDENCE,EVIDENCE,final(cached,'settings.cycles'),final(cached)])
    payloads=[]
    def opener(req,timeout):
        payload=json.loads(req.data);payloads.append(payload)
        response=fake.complete(payload['messages'],payload.get('tools',[]),
                               tool_choice=payload.get('tool_choice','auto'))
        return BytesIO(json.dumps({'choices':[{'message':response['message']}]}).encode())
    p=ChatProvider(ProviderConfig(provider=provider,model='test',base_url='https://example.invalid/v1',
                                 api_key='fake',extra={token_field:1600}),opener=opener)
    result=loop.run_agent('Compare stroke volume in phase1',provider=p,commit='0'*40)
    assert result['verification']['passed'],result['verification']
    forced=[r for r in payloads if r.get('tool_choice')=='none']
    assert len(forced)==2
    for payload in forced:
        assert payload['tools']==loop.TOOL_SCHEMAS
        assert any(m.get('tool_calls') for m in payload['messages'])
        assert payload[token_field]==1600
        assert payload['response_format']['json_schema']['name']=='final_message'


def test_forced_final_format_retry_preserves_schemas(cached):
    payloads=[]
    def opener(req,timeout):
        payloads.append(json.loads(req.data))
        if len(payloads)==1:
            raise HTTPError(req.full_url,400,'bad format',{},BytesIO(b'{"error":{"message":"response_format unsupported"}}'))
        return BytesIO(json.dumps({'choices':[{'message':final(cached)}]}).encode())
    p=ChatProvider(ProviderConfig(provider='anthropic',model='test',base_url='https://example.invalid/v1',api_key='fake'),opener=opener)
    messages=[RUN,{'role':'tool','tool_call_id':'run_experiment','content':'{}'},
              {'role':'user','content':loop.FINAL_NUDGE}]
    p.complete(messages,loop.TOOL_SCHEMAS,tool_choice='none')
    assert len(payloads)==2 and 'response_format' not in payloads[-1]
    assert all(r['tools']==loop.TOOL_SCHEMAS and r['tool_choice']=='none' for r in payloads)


@pytest.mark.parametrize('turn',['nudge','repair'])
def test_provider_error_on_forced_final_recovers_receipts(cached,turn):
    script=([RUN,EVIDENCE,EVIDENCE] if turn=='nudge' else [RUN,final(cached,'settings.cycles')])
    p=FakeProvider(script+[ProviderError('forced-final provider rejected request')])
    result=loop.run_agent('Compare cardiac output in phase1',provider=p,max_steps=8,commit='0'*40)
    assert result['verification']['passed'],result['verification']
    assert result['report']['finding_selection']=='code_hypothesis_terms'
    assert result['report']['status']=='completed_with_warnings'
    assert result['verification']['repair_attempted'] is (turn=='repair')
    assert p.requests[-1]['tool_choice']=='none'
    assert any(s.get('error')=='forced-final provider rejected request' for s in result['trace'])
    validate_report(result['report'])


def test_failed_code_selection_does_not_ask_for_repair(monkeypatch,receipt):
    other=deepcopy(receipt);other['run_id']='other-model';other['model']='m1'
    runs=iter([receipt,other]);real=loop.dispatch
    monkeypatch.setattr(loop,'dispatch',lambda name,args:deepcopy(next(runs)) if name=='run_experiment' else real(name,args))
    p=FakeProvider([RUN,RUN])
    result=loop.run_agent('Compare cardiac output',provider=p,max_steps=2,commit='0'*40)
    assert result['report']['status']=='unverified'
    assert not result['verification']['passed'] and not result['verification']['repair_attempted']
    assert any(f['path']=='model' for f in result['verification']['failures'])
    assert len(p.requests)==3  # Classifier plus two normal turns; no repair.
    assert not any(s['kind']=='repair' for s in result['trace'])
    validate_report(result['report'])


@pytest.mark.parametrize('override',[False,True])
def test_input_echo_alone_uses_defaults(receipt,override):
    run=deepcopy(receipt)
    if override:
        run['parameter_changes']=[];run['baseline_overrides']={'heart_rate':150}
    selected=select_metrics('Raise heart rate and compare heart_rate_bpm',run)
    assert 'heart_rate_bpm' not in selected
    assert {'cardiac_output_l_min','stroke_volume_ml'} <= set(selected)
    assert selection_basis('Raise heart rate and compare heart_rate_bpm',{'r':run})=='code_default_set'


@pytest.mark.parametrize('text,excluded',[
    ('Compare sv pressure','stroke_volume_ml'),
    ('Compare sv volume and left ventricular pressure','stroke_volume_ml'),
    ('Use a map to compare left ventricular pressure','systemic_mean_pressure_mmhg'),
    ('Ask the co author about left ventricular pressure','cardiac_output_l_min'),
])
def test_ambiguous_short_aliases_do_not_add_metrics(receipt,text,excluded):
    assert excluded not in select_metrics(text,receipt)


def test_partial_evidence_fetches_each_missing_parameter(monkeypatch,receipt):
    run=deepcopy(receipt)
    run['parameter_changes'].append({'parameter':'emax_lv','baseline':2.5,'intervention':1.25})
    run['baseline_overrides']={'initial_volumes.lv':150.}
    real=loop.dispatch;queried=[]
    def dispatch(name,args):
        if name=='run_experiment':return deepcopy(run)
        if name=='get_evidence':queried.append(args['entity_or_param'])
        return real(name,args)
    monkeypatch.setattr(loop,'dispatch',dispatch)
    p=FakeProvider([RUN,EVIDENCE,final(run)])
    result=loop.run_agent('Compare cardiac output',provider=p,commit='0'*40)
    assert result['verification']['passed'],result['verification']
    assert queried==['heart_rate','emax_lv','initial_volumes.lv']
    assert len([s for s in result['trace'] if s.get('initiated_by')=='code'])==2
    for name in queried:
        assert all(e in result['report']['evidence'] for e in get_evidence(name))
