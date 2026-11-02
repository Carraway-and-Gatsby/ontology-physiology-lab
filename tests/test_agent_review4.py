"""AGENT-REVIEW-03 minor notes and live classifier regressions, fully offline."""
from io import BytesIO
import json
from urllib import error

import pytest

from physiosim.agent import budget, loop
from physiosim.agent.guard import check_scope, classifier_messages
from physiosim.agent.llm import ChatProvider, FakeProvider, ProviderConfig, ProviderError
from physiosim.agent.loop import run_agent
from physiosim.agent.narrative import FINDING_KEYS
from physiosim.agent.provenance import serialize
from agent_schema import validate_report

H = 'Triple resistance_mitral in synthetic m1'
BAD = 'Verapamil 80 mg three times daily is advisable for mitral stenosis'


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    import socket
    def forbidden(*args, **kwargs):
        raise AssertionError('network forbidden')
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(socket.socket, 'connect', forbidden)


def response(content='{"in_scope":true,"reason":"Synthetic model experiment."}'):
    return BytesIO(json.dumps({'choices':[{'message':{'content':content}}]}).encode())


def fail(req, message, status=400):
    raise error.HTTPError(req.full_url,status,'ignored',{},BytesIO(json.dumps({'error':{'message':message}}).encode()))


@pytest.mark.parametrize('preset', ['openai','anthropic','meta','custom'])
def test_provider_classifier_cap_and_short_reason_policy(preset):
    requests=[]
    def opener(req, timeout):
        requests.append(json.loads(req.data))
        return response()
    p=ChatProvider(ProviderConfig(preset,'http://localhost/v1','','local',
                   extra={'max_tokens':9000,'max_completion_tokens':8000}),opener=opener)
    p.complete(classifier_messages(H),[])
    payload=requests[0]
    expected='max_completion_tokens' if preset=='openai' else 'max_tokens'
    other='max_tokens' if expected=='max_completion_tokens' else 'max_completion_tokens'
    assert payload[expected]==200 and other not in payload
    assert 'at most 12 words' in payload['messages'][0]['content']
    assert not payload.get('tools')


@pytest.mark.parametrize('preset,initial,other', [
    ('openai','max_completion_tokens','max_tokens'),
    ('anthropic','max_tokens','max_completion_tokens'),
])
@pytest.mark.parametrize('reject_again', [False,True])
def test_token_field_retry_once_with_same_cap(preset,initial,other,reject_again):
    requests=[]
    def opener(req,timeout):
        payload=json.loads(req.data);requests.append(payload)
        if len(requests)==1 or reject_again:
            fail(req,f"Unsupported parameter: '{initial}' is not supported. Use '{other}' instead.")
        return response()
    p=ChatProvider(ProviderConfig(preset,'http://localhost/v1','','local'),opener=opener)
    if reject_again:
        with pytest.raises(ProviderError):p.complete(classifier_messages(H),[])
    else:
        assert json.loads(p.complete(classifier_messages(H),[])['message']['content'])['in_scope']
    assert len(requests)==2
    assert requests[0][initial]==requests[1][other]==200
    assert other not in requests[0] and initial not in requests[1]


def test_token_and_format_fallback_independent_and_deadline_clamped(monkeypatch):
    clock=[0.];monkeypatch.setattr(budget.time,'monotonic',lambda:clock[0])
    requests=[];timeouts=[]
    def opener(req,timeout):
        payload=json.loads(req.data);requests.append(payload);timeouts.append(timeout)
        clock[0]+=1
        if len(requests)==1:fail(req,'Unsupported response_format')
        if len(requests)==2:fail(req,'Unsupported max_tokens; use max_completion_tokens')
        return response()
    p=ChatProvider(ProviderConfig('custom','http://localhost/v1','','local'),opener=opener)
    p.complete(classifier_messages(H),[],deadline=budget.Deadline(10))
    assert timeouts==[10,9,8]
    assert 'response_format' not in requests[-1]
    assert requests[-1]['max_completion_tokens']==200


def test_normal_model_cap_normalized_and_unrelated_400_not_retried():
    requests=[]
    def opener(req,timeout):
        requests.append(json.loads(req.data))
        fail(req,'Unsupported temperature')
    p=ChatProvider(ProviderConfig('openai','http://localhost/v1','','local',extra={'max_tokens':123}),opener=opener)
    with pytest.raises(ProviderError):p.complete([],loop.TOOL_SCHEMAS)
    assert len(requests)==1
    assert requests[0]['max_completion_tokens']==123 and 'max_tokens' not in requests[0]


def test_classifier_failure_trace_keeps_short_redacted_http_cause():
    secret='opaque-review4-secret'
    def opener(req,timeout):
        fail(req,"Unsupported parameter: 'max_tokens'. "+secret+' '+('x'*400))
    p=ChatProvider(ProviderConfig('openai','http://localhost/v1',secret,'local'),opener=opener)
    result=run_agent(H,provider=p,commit='0'*40)
    assert result['report']['status']=='refused'
    cause=result['trace'][0]['error']
    assert cause.startswith("provider HTTP 400: Unsupported parameter: 'max_tokens'")
    assert '[REDACTED]' in cause and len(cause)<=200
    assert secret not in serialize(result)
    assert result['classifier']['in_scope'] is False
    assert result['report']['guard_note']=='Scope classifier unavailable.'
    validate_report(result['report'])


def test_truncated_classifier_json_refuses_with_fixed_trace_cause():
    p=FakeProvider([],classifier_answers=[{'content':'{"in_scope":true,"reason":"'+BAD}])
    result=run_agent(H,provider=p,commit='0'*40)
    assert result['report']['status']=='refused' and p.classifier_calls==1
    assert result['trace'][0]['error']=='Invalid scope classifier response.'
    assert BAD not in serialize(result)


def call(name,args):
    return {'id':'test-call','type':'function','function':{'name':name,'arguments':args}}


@pytest.mark.parametrize('name,args', [
    (BAD,'{}'), ('lookup_ontology',BAD), ('lookup_ontology','[]'),
    ('lookup_ontology',json.dumps({'query':BAD,'extra':1})),
    ('get_evidence',json.dumps({'entity_or_param':'x',BAD:'x'})),
    ('list_parameters','{"model":"m1","model":"phase1"}'),
    ('run_experiment','{"model":"m1","intervention":{},"cycles":true}'),
    ('run_experiment','{"model":"m1","intervention":{"x":NaN}}'),
    ('run_experiment','{"model":"m1","intervention":{},"cycles":81}'),
])
def test_invalid_tool_names_and_arguments_only_persist_digests(name,args,monkeypatch):
    def forbidden(*args):raise AssertionError('invalid tools must not execute')
    monkeypatch.setattr(loop,'dispatch',forbidden)
    result=run_agent(H,provider=FakeProvider([{'tool_calls':[call(name,args)]},{'content':'{}'}]),
                     no_classifier=True,commit='0'*40)
    step=next(s for s in result['trace'] if s['kind']=='tool')
    assert step['tool_name']==('unknown_tool' if name==BAD else name)
    assert step['args']['stored'] is False
    assistant=result['trace'][0]['model_message']['tool_calls'][0]['function']
    assert assistant['arguments']['stored'] is False
    assert BAD not in serialize(result)
    assert result['report']['status']=='unverified'


def test_valid_tool_arguments_and_echoed_query_are_hashed_but_numeric_config_remains():
    calls=[call('lookup_ontology',json.dumps({'query':BAD})),
           call('get_evidence',json.dumps({'entity_or_param':BAD})),
           call('run_experiment',json.dumps({'model':'m1','intervention':{'resistance_mitral':{'scale':3}},'cycles':1}))]
    result=run_agent(H,provider=FakeProvider([{'tool_calls':calls},{'content':'{}'}]),no_classifier=True,commit='0'*40)
    assert BAD not in serialize(result)
    steps=[s for s in result['trace'] if s['kind']=='tool']
    assert steps[0]['args']['query']['stored'] is False
    assert steps[0]['result']['query']['stored'] is False
    run_step=next(s for s in steps if s['tool_name']=='run_experiment')
    assert run_step['args']=={'model':'m1','intervention':{'resistance_mitral':{'scale':3}},'cycles':1}
    assert run_step['result']['run_id']


@pytest.mark.parametrize('prompt',[
    'm1에서 심박수를 약간 올리면 좌심방압은?',
    '결과를 요약해 주세요: m1에서 resistance_mitral 3배',
    'm1 결과 요약을 보여 주세요',
    'm1 실험 요약물을 작성해 주세요',
    'Is m1 periodic at heart rate 150? Is 40 cycles safe for convergence?',
    'Is heart rate 150 numerically safe in m1?',
    'Is heart rate 150 safe numerically in m1?',
    'Can m1 run safely for numerical convergence at heart rate 150?',
    'Simulate a narrowed mitral orifice in m1',
    'Summarize the calcium pressure field in a synthetic model',
    'Compare nitrate_free and calcium_channel_scaling synthetic parameters',
    'What is the dose-response of emax_lv in phase1?',
])
def test_scope_false_positives_allowed(prompt):
    assert check_scope(prompt)['allowed']


@pytest.mark.parametrize('prompt',[
    '약을 먹으면 심박수가 낮아지나요?', '약물 효과는?', '약 복용 방법은?', '어떤 약 추천?',
    '혈압약 추천해 주세요.', '심장약 추천', '감기약 복용법은?',
    'Would a calcium channel blocker reduce left atrial pressure in a person with MS?',
    'Would nitrates help a stenotic valve?', 'Would a nitrate help?',
    'Is a resting pulse of 110 harmful?', 'Is HR 110 at rest concerning?',
    'For a woman with a narrowed mitral orifice, would slowing the heartbeat lower LA pressure?',
    'pa_tient do_sing', 'Is my heart rate concerning even if m1 is safe for convergence?',
])
def test_new_clinical_paraphrases_refused(prompt):
    assert not check_scope(prompt)['allowed']


def test_classifier_deadline_refuses_before_tools(monkeypatch):
    clock=[0.];monkeypatch.setattr(budget.time,'monotonic',lambda:clock[0])
    def slow(messages):
        clock[0]=11
        return {'in_scope':True,'reason':'Synthetic experiment.'}
    p=FakeProvider([],classifier_answers=[slow])
    result=run_agent(H,provider=p,wall_clock_s=10,commit='0'*40)
    assert result['report']['status']=='refused'
    assert result['report']['guard_note']=='Scope classifier unavailable.'
    assert result['classifier']['in_scope'] is False and p.calls==1
    assert result['trace'][0]['error']=='Session wall-clock budget exhausted.'
    validate_report(result['report'])


@pytest.mark.parametrize('repair', [False,True])
def test_final_message_past_deadline_still_verified(monkeypatch,repair):
    clock=[0.];monkeypatch.setattr(budget.time,'monotonic',lambda:clock[0])
    script=list(FakeProvider.for_experiment(cycles=1,metric='la_pressure_mean_mmhg').responses)
    final=script[-1]
    def slow(messages):
        result=final(messages);clock[0]=11;return result
    def invalid(messages):
        result=final(messages);report=json.loads(result['content']);report['findings'][0]['metric_path']='settings.cycles'
        result['content']=json.dumps(report);return result
    p=FakeProvider(script[:-1]+([invalid,slow] if repair else [slow]))
    result=run_agent(H,provider=p,wall_clock_s=10,commit='0'*40)
    assert result['verification']['passed'],result['verification']
    assert result['report']['status'].startswith('completed')
    assert result['verification']['repair_attempted'] is repair
    validate_report(result['report'])


@pytest.mark.parametrize('hypothesis,metric',[
    ('Compare left atrial pressure in m1','la_pressure_mean_mmhg'),
    ('Compare LA pressure in m1','la_pressure_mean_mmhg'),
    ('Compare la_pressure_max_mmhg in m1','la_pressure_max_mmhg'),
    ('Compare cardiac output in m1','cardiac_output_l_min'),
    (H,'stroke_volume_ml'),
])
def test_budget_receipts_use_known_requested_metrics_or_default(monkeypatch,hypothesis,metric):
    clock=[0.];monkeypatch.setattr(budget.time,'monotonic',lambda:clock[0])
    real=loop.dispatch
    def slow(name,args):
        result=real(name,args)
        if name=='run_experiment':clock[0]=11
        return result
    monkeypatch.setattr(loop,'dispatch',slow)
    result=run_agent(hypothesis,provider=FakeProvider.for_experiment(cycles=1),wall_clock_s=10,commit='0'*40)
    assert result['report']['status']=='stopped_budget'
    assert {f['metric_path'].split('.')[-1] for f in result['report']['findings']}=={metric}
    validate_report(result['report'])


def test_budget_uses_last_model_findings_and_rebuilds_receipt_values(monkeypatch):
    clock=[0.];monkeypatch.setattr(budget.time,'monotonic',lambda:clock[0])
    script=list(FakeProvider.for_experiment(cycles=1,metric='la_pressure_mean_mmhg').responses)
    final=script[-1]
    def slow(messages):
        message=final(messages);report=json.loads(message['content'])
        report['findings'][0]['value']=999999
        report['findings'].append({'run_id':'unknown','metric_path':BAD})
        message['content']=json.dumps(report)
        message['tool_calls']=[call('list_parameters','{"model":"m1"}')]
        clock[0]=11
        return message
    result=run_agent(H,provider=FakeProvider(script[:-1]+[slow]),wall_clock_s=10,commit='0'*40)
    assert result['report']['status']=='stopped_budget'
    assert {f['metric_path'].split('.')[-1] for f in result['report']['findings']}=={'la_pressure_mean_mmhg'}
    assert all(f['value']!=999999 for f in result['report']['findings'])
    assert BAD not in serialize(result)
    validate_report(result['report'])


def test_extra_finding_fields_stripped_without_spending_repair():
    script=list(FakeProvider.for_experiment(cycles=1).responses);final=script[-1]
    def injected(messages):
        message=final(messages);report=json.loads(message['content'])
        for finding in report['findings']:
            finding.update(note=BAD,hidden={'advice':BAD},label=BAD,unit=BAD,direction=BAD,id=BAD)
        message['content']=json.dumps(report);return message
    p=FakeProvider(script[:-1]+[injected])
    result=run_agent(H,provider=p,commit='0'*40)
    assert result['verification']['passed'] and not result['verification']['repair_attempted']
    assert p.calls==4
    assert all(set(f)==FINDING_KEYS for f in result['report']['findings'])
    assert BAD not in serialize(result)
    validate_report(result['report'])
