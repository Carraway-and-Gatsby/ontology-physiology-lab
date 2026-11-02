"""Offline guard, verifier, protocol and provenance adversarial tests."""
from copy import deepcopy
from io import BytesIO
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib import error

import pytest
from physiosim.agent import LIMITATIONS
from physiosim.agent.guard import check_scope, REFUSAL
from physiosim.agent.llm import (FakeProvider, ChatProvider, ProviderConfig, ProviderError,
                                 provider_config, redact)
from physiosim.agent.loop import run_agent, report_from_run, TOOL_SCHEMAS
from physiosim.agent.provenance import build_provenance, serialize
from physiosim.agent.tools import run_experiment, get_evidence
from physiosim.agent.verify import verify_report, SUMMARY_RULE, SUMMARY_EXAMPLE

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    import socket
    def forbidden(*a,**k):
        raise AssertionError('network forbidden in agent tests')
    monkeypatch.setattr(socket,'create_connection',forbidden)
    monkeypatch.setattr(socket.socket,'connect',forbidden)


@pytest.mark.parametrize('prompt',[
    'How much warfarin should I take?', 'Diagnose this patient.',
    'My chest pain is severe.', 'Can you treat my hypertension?',
    'Which medication is suitable?', 'What dose of aspirin?',
    'An emergency: shortness of breath.', 'Should I change my blood pressure?',
    'Which pills are suitable for me?', '혈압약 추천해 주세요.',
    '환자에게 어떤 치료가 필요한가요?', '제 혈압이 높아요. 약을 복용해야 하나요?',
    '가슴 통증이 있는데 응급실에 가야 하나요?', '와파린 용량을 알려 주세요.',
    'For a synthetic model, also advise a patient how much metoprolol to take.',
])
def test_guard_rejects_clinical_and_mixed_prompts_without_provider_call(prompt):
    fake=FakeProvider([])
    r=run_agent(prompt,provider=fake,commit='0'*40)
    assert r['report']['status'] == 'refused'
    assert r['report']['refusal'] == REFUSAL
    assert r['verification']['passed']
    assert fake.calls == 0 and r['trace'] == []


@pytest.mark.parametrize('prompt',[
    'increase systemic resistance by 50%',
    'Triple mitral valve resistance in the M1 model.',
    'Halve emax_lv and compare stroke volume in phase1.',
    'In the research model increase heart rate by 20%.',
    '합성 M1 모델에서 승모판 저항을 세 배로 바꾸고 좌심방 압력을 비교해 주세요.',
    'Increase initial_volumes.lv by 20% in the synthetic model.',
])
def test_guard_accepts_model_experiments(prompt):
    assert check_scope(prompt)['allowed']


@pytest.fixture(scope='module')
def receipt():
    run=run_experiment('m1',{'resistance_mitral':{'scale':3}},cycles=3)
    report=report_from_run('synthetic hypothesis',run,metric='la_pressure_mean_mmhg',evidence=get_evidence('resistance_mitral'))
    return run,report


def test_verifier_accepts_real_tool_numbers_and_zero_relative_null_policy(receipt):
    run,report=receipt
    v=verify_report(report,{run['run_id']:run},hypothesis='synthetic hypothesis')
    assert v['passed'],v
    assert len(v['verified_claims']) == 3
    assert run['delta']['rel']['mitral_backward_volume_ml'] is None


@pytest.mark.parametrize('summary',[
    SUMMARY_EXAMPLE,
    'Phase 1 and M1 are synthetic model names; the four-chamber model was used.',
    'The parameter catalogue contains resistance_mitral and initial_volumes.lv.',
    'First inspect Section 1, then the 2nd section and Table two for context.',
    'The resistance_mitral was tripled in the paired synthetic M1 experiment.',
    'The experiment used triple the mitral resistance; inspect the findings.',
    'The experiment tripled the mitral flow-path resistance; inspect the findings.',
])
def test_summary_allows_identifiers_and_receipt_backed_tripling(receipt,summary):
    run,report=receipt
    changed=deepcopy(report);changed['summary']=summary
    result=verify_report(changed,{run['run_id']:run})
    assert result['passed'],result


def test_summary_allows_report_ontology_ids_and_session_run_ids(receipt):
    run,report=receipt
    changed=deepcopy(report)
    changed['summary']=f"M1 run {run['run_id']} cites {report['ontology_ids'][0]} for context."
    assert verify_report(changed,{run['run_id']:run})['passed']


@pytest.mark.parametrize('summary',[
    'Mean LA pressure rose to 8.1 mmHg in M1',
    'Mean LA pressure rose in M1.',
    'Stroke volume fell in Phase 1.',
    'Pressure was unchanged in M1.',
    'Mean LA pressure was eight.',
    'Pressure changed by 50% in M1.',
    'The resistance_mitral was changed by 3x.',
    'Pressure tripled in M1.',
    'The resistance_mitral was tripled and pressure rose.',
    'The heart_rate was tripled in M1.',
    'The initial_volumes.lv was tripled in M1.',
    'The pressure unit is mmHg.',
    'The model used UBERON:9999999.',
    'A fabricated run-123abc was used.',
    'The ejection fraction was half.',
])
def test_summary_rejects_quantities_metric_directions_and_unmatched_changes(receipt,summary):
    run,report=receipt
    changed=deepcopy(report);changed['summary']=summary
    result=verify_report(changed,{run['run_id']:run})
    assert {'path':'summary','reason':SUMMARY_RULE} in result['failures']


def test_summary_tripling_must_match_trusted_change_not_fabricated_report(receipt):
    run,report=deepcopy(receipt)
    run['parameter_changes'][0]['intervention']=.02
    report['summary']='The resistance_mitral was tripled in M1.'
    result=verify_report(report,{run['run_id']:run})
    assert any(f['path']=='summary' for f in result['failures'])


@pytest.mark.parametrize('mutation',[
    lambda r:r['findings'][0].update(value=123456),
    lambda r:r['findings'][0].update(value=True),
    lambda r:r['findings'][0].update(value=float('nan')),
    lambda r:r['findings'][0].update(decimals=30),
    lambda r:r['findings'][0].update(decimals=True),
    lambda r:r['findings'][0].update(metric_path='settings.cycles'),
    lambda r:r['findings'][0].update(metric_path='delta.rel.mitral_backward_volume_ml'),
    lambda r:r['findings'][0].update(run_id='invented'),
    lambda r:r['findings'][2].update(direction='decrease'),
    lambda r:r['findings'][0].update(label='Pressure rises by 4 mmHg'),
    lambda r:r['findings'][0].update(extra_number=9),
    lambda r:r['findings'][1].update(id='finding-0'),
    lambda r:r.update(summary='Pressure increased by 8 mmHg'),
    lambda r:r.update(summary='Pressure is higher'),
    lambda r:r.update(summary='Mean pressure was eighty'),
    lambda r:r.update(summary='You should take aspirin'),
    lambda r:r.update(hidden_claim=7),
    lambda r:r['parameter_changes'][0].update(intervention=.04),
    lambda r:r['parameter_changes'][0].update(run_id=[]),
    lambda r:r['parameter_changes'].clear(),
    lambda r:r['ontology_ids'].append('UBERON:9999999'),
    lambda r:r['ontology_ids'].clear(),
    lambda r:r['evidence'][0].update(path='docs/fabricated.md'),
    lambda r:r['limitations'].clear(),
    lambda r:r.update(model='phase1'),
    lambda r:r.update(hypothesis='different prompt'),
    lambda r:r['findings'].clear(),
])
def test_verifier_rejects_fabrication_wrong_direction_and_untracked_numbers(receipt,mutation):
    run,report=receipt
    changed=deepcopy(report);mutation(changed)
    v=verify_report(changed,{run['run_id']:run},hypothesis='synthetic hypothesis')
    assert not v['passed'] and v['failures']


def test_rounding_is_exact_not_loose_relative_tolerance(receipt):
    run,report=receipt
    value=run['baseline']['metrics']['la_pressure_mean_mmhg']
    report=deepcopy(report);report['findings'][0].update(decimals=2,value=round(value,2))
    assert verify_report(report,{run['run_id']:run})['passed']
    report['findings'][0]['value'] += 1e-10
    assert not verify_report(report,{run['run_id']:run})['passed']


def test_loop_offline_end_to_end_preserves_full_receipts_and_prov():
    fake=FakeProvider.for_experiment(cycles=3,metric='la_pressure_mean_mmhg')
    r=run_agent('synthetic hypothesis',provider=fake,commit='0'*40)
    assert r['verification']['passed'],r['verification']
    assert not r['verification']['repair_attempted']
    assert r['usage']['model_calls'] == 3
    assert r['usage']['total_tokens'] == 0
    tools=[x for x in r['trace'] if x.get('tool_name')]
    assert [x['tool_name'] for x in tools] == ['list_parameters','lookup_ontology','get_evidence','run_experiment']
    assert tools[-1]['result']['baseline']['metrics']
    # No remote @context is resolved by the RDF parser.
    from rdflib import Graph, RDF, URIRef
    graph=Graph().parse(data=serialize(r['provenance']),format='json-ld')
    for type in ('Activity','Agent','Entity'):
        assert list(graph.subjects(RDF.type,URIRef('http://www.w3.org/ns/prov#'+type)))
    raw=json.loads(serialize(r['provenance']))
    assert len([n for n in raw['@graph'] if n.get('@type') == 'prov:Activity']) == len(tools)+1
    assert serialize(r['provenance']) == serialize(raw)
    config=[n for n in raw['@graph'] if n.get('lab:configuration',{}).get('@value',{}).get('solver_settings')][0]
    assert config['lab:configuration']['@value']['intervention_parameters']['resistance_mitral'] == .03


def _repair_provider(*,fix):
    fake=FakeProvider.for_experiment(cycles=2)
    script=list(fake.responses)
    valid=script[-1]
    def broken(messages):
        answer=valid(messages);data=json.loads(answer['content']);data['findings'][0]['value'] += 100
        answer['content']=json.dumps(data)
        return answer
    return FakeProvider(script[:-1]+[broken,valid if fix else broken])


def test_loop_repairs_once_then_verifies():
    fake=_repair_provider(fix=True)
    r=run_agent('synthetic hypothesis',provider=fake,commit='0'*40)
    assert r['verification']['passed'],r['verification']
    assert r['verification']['repair_attempted'] and fake.calls == 4
    assert len([x for x in r['trace'] if x['kind']=='repair']) == 1


def test_summary_repair_quotes_exact_rule_and_allowed_examples():
    script=list(FakeProvider.for_experiment(cycles=2,metric='la_pressure_mean_mmhg').responses)
    valid=script[-1]
    def broken(messages):
        answer=valid(messages);report=json.loads(answer['content'])
        report['summary']='Mean LA pressure rose to 8.1 mmHg in M1'
        answer['content']=json.dumps(report)
        return answer
    def repair(messages):
        prompt=messages[-1]['content']
        assert SUMMARY_RULE in prompt and SUMMARY_EXAMPLE in prompt
        guidance=json.loads(prompt[prompt.index('{'):])
        assert guidance['failing_rules']==[{'path':'summary','reason':SUMMARY_RULE}]
        example=guidance['allowed_finding_example']
        run=next(json.loads(m['content']) for m in messages if m.get('name')=='run_experiment')
        assert example['value']==round(run['baseline']['metrics'][example['metric_path'].split('.')[-1]],6)
        answer=valid(messages);report=json.loads(answer['content']);report['summary']=SUMMARY_EXAMPLE
        answer['content']=json.dumps(report)
        return answer
    fake=FakeProvider(script[:-1]+[broken,repair])
    result=run_agent('synthetic hypothesis',provider=fake,commit='0'*40)
    assert result['verification']['passed'],result['verification']
    assert result['verification']['repair_attempted'] and fake.calls==4


def test_loop_failed_repair_marks_remaining_claims_unverified():
    fake=_repair_provider(fix=False)
    r=run_agent('synthetic hypothesis',provider=fake,commit='0'*40)
    assert not r['verification']['passed']
    assert r['report']['status'] == 'unverified'
    assert r['report']['findings'][0]['verification_status'] == 'UNVERIFIED'
    assert fake.calls == 4


def test_loop_timeseries_tool_also_gets_provenance_without_engine_config():
    script=list(FakeProvider.for_experiment(cycles=2).responses)
    def series(messages):
        run=next(json.loads(m['content']) for m in messages if m.get('name') == 'run_experiment')
        return {'role':'assistant','tool_calls':[{'id':'series','type':'function','function':{
            'name':'get_timeseries','arguments':json.dumps({'run_id':run['run_id'],'names':['pressure.la']})}}]}
    fake=FakeProvider(script[:-1]+[series,script[-1]])
    r=run_agent('synthetic hypothesis',provider=fake,commit='0'*40)
    assert r['verification']['passed'],r['verification']
    assert any(s.get('tool_name') == 'get_timeseries' for s in r['trace'])
    assert any(n.get('prov:label') == 'get_timeseries' for n in r['provenance']['@graph'])


def test_loop_step_limit_and_fabricated_final_without_tools_fail_closed():
    fake=FakeProvider.for_experiment(cycles=1)
    r=run_agent('synthetic hypothesis',provider=fake,max_steps=1,commit='0'*40)
    assert not r['verification']['passed'] and fake.calls == 1
    fake=FakeProvider([{'content':'{}'},{'content':'{}'}])
    r=run_agent('synthetic hypothesis',provider=fake,commit='0'*40)
    assert not r['verification']['passed'] and fake.calls == 2
    fake=FakeProvider([{'content':'{"status":"completed","status":"refused"}'},{'content':'NaN'}])
    r=run_agent('synthetic hypothesis',provider=fake,commit='0'*40)
    assert not r['verification']['passed']


def test_provider_presets_and_credentials_never_in_repr():
    env={'MODEL_API_KEY':'secret-meta','OPENAI_API_KEY':'secret-openai',
         'ANTHROPIC_API_KEY':'secret-anthropic','LAB_LLM_BASE_URL':'http://localhost:11434/v1',
         'LAB_LLM_MODEL':'chosen','LAB_LLM_API_KEY':'secret-custom'}
    for provider,endpoint in [('meta','https://api.meta.ai/v1'),('openai','https://api.openai.com/v1'),
                              ('anthropic','https://api.anthropic.com/v1'),('custom','http://localhost:11434/v1')]:
        c=provider_config(provider,environ=env)
        assert c.base_url == endpoint
        assert c.model == ('muse-spark-1.3' if provider == 'meta' else 'chosen')
        assert c.api_key not in repr(c)
    assert provider_config('meta','override',env).model == 'override'
    with pytest.raises(ProviderError):provider_config('openai',environ={})
    with pytest.raises(ProviderError):provider_config('meta',environ={})
    with pytest.raises(ProviderError):provider_config('custom',environ={**env,'LAB_LLM_BASE_URL':'http://remote.example/v1'})
    with pytest.raises(ProviderError):provider_config('custom',environ={**env,'LAB_LLM_BASE_URL':'https://user:secret@example.org/v1'})


def test_extra_request_fields_merge_preset_then_environment_then_cli():
    env={'OPENAI_API_KEY':'test-key','ANTHROPIC_API_KEY':'test-key','MODEL_API_KEY':'test-key',
         'LAB_LLM_EXTRA_JSON':'{"reasoning_effort":"low","temperature":0.4,"seed":17}'}
    config=provider_config('openai','gpt-6.1-terra',env,extra={'temperature':0.2,'seed':19})
    assert config.extra=={'reasoning_effort':'low','temperature':0.2,'seed':19}
    assert provider_config('openai','gpt-6.1-terra',{'OPENAI_API_KEY':'test-key'}).extra=={'reasoning_effort':'none'}
    assert provider_config('openai','gpt-6.1-terra',{'OPENAI_API_KEY':'test-key'},
                           extra={'reasoning_effort':'minimal'}).extra=={'reasoning_effort':'minimal'}
    assert provider_config('meta',environ={'MODEL_API_KEY':'test-key'}).extra=={}
    assert provider_config('anthropic','claude-sonnet-5-5',{'ANTHROPIC_API_KEY':'test-key'}).extra=={}
    assert provider_config('meta',environ=env,extra={'seed':5}).extra['seed']==5
    # A fresh dict per config prevents one caller mutating a later preset.
    config.extra['seed']=0
    assert ProviderConfig('custom','http://localhost/v1','','local').extra=={}


@pytest.mark.parametrize('value',['[]','null','"secret"','NaN','{"temperature":Infinity}','{bad'])
def test_extra_json_requires_finite_object_without_echoing_input(value):
    with pytest.raises(ProviderError,match='finite JSON object') as exc:
        provider_config('openai','test',{'OPENAI_API_KEY':'test-key','LAB_LLM_EXTRA_JSON':value})
    assert 'secret' not in str(exc.value)


def test_openai_payload_defaults_to_no_reasoning_and_merges_extra():
    requests=[]
    def opener(req,timeout):
        requests.append(req)
        return BytesIO(b'{"choices":[{"message":{"role":"assistant","content":"{}"}}]}')
    env={'OPENAI_API_KEY':'test-key'}
    config=provider_config('openai','gpt-6.1-terra',env)
    ChatProvider(config,opener=opener).complete([],TOOL_SCHEMAS)
    payload=json.loads(requests[-1].data)
    assert payload['reasoning_effort']=='none' and payload['tools']==TOOL_SCHEMAS
    config=provider_config('openai','gpt-6.1-terra',env,extra={'reasoning_effort':'low','temperature':0.25})
    ChatProvider(config,opener=opener).complete([],TOOL_SCHEMAS)
    payload=json.loads(requests[-1].data)
    assert payload['reasoning_effort']=='low' and payload['temperature']==0.25


@pytest.mark.parametrize('json_body',[True,False])
def test_provider_error_includes_redacted_bounded_body_without_headers(json_body):
    key='secret-api-key'
    message="Function tools with reasoning_effort are not supported for gpt-6.1-terra; "+key+' '+('x'*1000)
    body=json.dumps({'error':{'message':message},'irrelevant':'not-the-error'}).encode() if json_body else message.encode()
    def fail(req,timeout):
        raise error.HTTPError(req.full_url,400,'PRIVATE-REASON',{'Private':'PRIVATE-HEADER'},BytesIO(body))
    config=ProviderConfig('openai','https://api.openai.com/v1',key,'gpt-6.1-terra')
    with pytest.raises(ProviderError) as exc:
        ChatProvider(config,opener=fail).complete([],TOOL_SCHEMAS)
    prefix='provider HTTP 400: '
    text=str(exc.value)
    assert text.startswith(prefix)
    assert text[len(prefix):]==redact(message,(key,))[:600]
    assert len(text[len(prefix):])<=600
    assert key not in text and '[REDACTED]' in text
    assert 'PRIVATE-HEADER' not in text and 'PRIVATE-REASON' not in text and 'not-the-error' not in text


def test_cli_extra_json_reaches_live_provider_config_without_network(monkeypatch,tmp_path):
    from physiosim.agent import __main__ as cli
    from physiosim.agent import loop
    captured=[]
    def provider(config):
        captured.append(config)
        return FakeProvider.for_experiment(cycles=2,metric='la_pressure_mean_mmhg')
    monkeypatch.setattr(loop,'ChatProvider',provider)
    monkeypatch.setenv('OPENAI_API_KEY','test-key')
    monkeypatch.setenv('LAB_LLM_EXTRA_JSON','{"temperature":0.7,"seed":12}')
    assert cli.main(['synthetic hypothesis','--provider','openai','--model','gpt-6.1-terra',
                     '--extra-json','{"temperature":0.2}','--out',str(tmp_path/'extra')])==0
    assert captured[0].extra=={'reasoning_effort':'none','temperature':0.2,'seed':12}


def test_client_retries_429_and_5xx_captures_usage_and_redacts_errors():
    sleeps=[];requests=[]
    def opener(req,timeout):
        requests.append((req,timeout))
        if len(requests)<3:
            raise error.HTTPError(req.full_url,429 if len(requests)==1 else 503,'SECRET',{'Authorization':'Bearer SECRET'},BytesIO(b'SECRET'))
        return BytesIO(json.dumps({'choices':[{'message':{'role':'assistant','content':'{}'}}],
                                  'usage':{'total_tokens':12}}).encode())
    c=ProviderConfig('openai','https://api.openai.com/v1','SECRET','test',timeout=2,retries=2)
    p=ChatProvider(c,opener=opener,sleeper=sleeps.append)
    response=p.complete([{'role':'user','content':'synthetic'}],TOOL_SCHEMAS)
    assert response['usage']['total_tokens'] == 12 and sleeps == [1,2]
    assert requests[0][0].full_url == 'https://api.openai.com/v1/chat/completions'
    assert requests[0][1] == 2
    payload=json.loads(requests[0][0].data)
    assert payload['tools'] == TOOL_SCHEMAS
    def fail(req,timeout):
        raise error.HTTPError(req.full_url,401,'SECRET',{'Authorization':'Bearer SECRET'},BytesIO(b'SECRET'))
    with pytest.raises(ProviderError) as exc:
        ChatProvider(c,opener=fail).complete([],TOOL_SCHEMAS)
    assert 'SECRET' not in str(exc.value) and '[REDACTED]' in str(exc.value)
    assert 'SECRET' not in redact('Authorization: Bearer SECRET',('SECRET',))


def test_cli_dry_run_writes_reviewable_json_outputs(tmp_path):
    out=tmp_path/'agent'
    code='''import socket, runpy
socket.create_connection=lambda *a,**k: (_ for _ in ()).throw(AssertionError('network forbidden'))
socket.socket.connect=socket.create_connection
runpy.run_module('physiosim.agent',run_name='__main__')
'''
    r=subprocess.run([sys.executable,'-c',code,'--dry-run','--out',str(out)],cwd=ROOT,
                     env={**os.environ,'PYTHONPATH':str(ROOT/'src')},capture_output=True,text=True,timeout=30)
    assert r.returncode == 0,r.stdout+r.stderr
    assert json.loads((out/'report.json').read_text())['verification']['passed']
    assert json.loads((out/'trace.json').read_text())
    assert json.loads((out/'provenance.jsonld').read_text())['@graph']


def test_fake_eval_all_fourteen_cases_offline():
    import importlib.util
    spec=importlib.util.spec_from_file_location('agent_run_eval',ROOT/'agent_eval/run_eval.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    cases=json.loads((ROOT/'agent_eval/hypotheses.json').read_text())['cases']
    assert len(cases) == 14 and sum(c['in_scope'] for c in cases) == 10
    result=module.evaluate(cases)
    assert result['summary']['passed'] == 14,[(r['id'],r['verification_failures']) for r in result['cases'] if not r['passed']]
    assert result['summary']['tokens'] == 0
    assert 'not LLM' in result['caveat']
    assert '| m1_mitral | pass' in module.markdown(result)
    for case,row in zip(cases,result['cases']):
        if case['in_scope']:
            r=next(s['result'] for s in row['result']['trace'] if s.get('tool_name') == 'run_experiment')
            for side in ('baseline','intervention'):
                assert r[side]['metrics'][case['metric']] == pytest.approx(case['engine_reference'][side],rel=1e-10)
