"""v2.1 receipt authorship, context-loop recovery, and separate eval credit."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest

from agent_schema import validate_report
from physiosim.agent import loop
from physiosim.agent.llm import FakeProvider
from physiosim.agent.narrative import prepare_report
from physiosim.agent.selection import select_metrics
from physiosim.agent.tools import run_experiment, get_evidence, lookup_ontology
from physiosim.agent.verify import relevant_evidence, verify_report


def call(name,args):
    return {'role':'assistant','tool_calls':[{'id':name,'type':'function','function':{
        'name':name,'arguments':json.dumps(args)}}]}


@pytest.fixture(scope='module')
def receipt():
    return run_experiment('phase1',{'heart_rate':90},cycles=1)


@pytest.fixture
def cached(monkeypatch,receipt):
    real = loop.dispatch
    monkeypatch.setattr(loop,'dispatch',lambda name,args:deepcopy(receipt) if name=='run_experiment' else real(name,args))
    return receipt


class LoopProvider(FakeProvider):
    def __init__(self, *, obey=True):
        super().__init__([])
        self.obey = obey; self.turns = 0; self.nudges = 0; self.offers = []

    def complete(self,messages,tools,*,deadline=None,tool_choice='auto'):
        if messages[0]['content'].startswith('SCOPE_CLASSIFIER.'):
            return super().complete(messages,tools,deadline=deadline,tool_choice=tool_choice)
        self.turns += 1; self.offers.append(tools)
        if messages[-1].get('content') == loop.FINAL_NUDGE:
            self.nudges += 1
            assert tools == loop.TOOL_SCHEMAS and tool_choice == 'none'
            if self.obey:
                run = next(json.loads(m['content']) for m in messages if m.get('name') == 'run_experiment')
                return {'message':{'content':json.dumps({'model':'phase1','findings':[
                    {'run_id':run['run_id'],'metric_path':'delta.abs.cardiac_output_l_min'}]})}}
        message = (call('run_experiment',{'model':'phase1','intervention':{'heart_rate':90},'cycles':1})
                   if self.turns == 1 else call('get_evidence',{'entity_or_param':'heart_rate'}))
        return {'message':message}


@pytest.mark.parametrize('obey,status',[(True,'completed_with_warnings'),(False,'completed_with_warnings')])
def test_evidence_loop_nudges_once_without_tools_then_finishes(cached,obey,status):
    p=LoopProvider(obey=obey)
    result=loop.run_agent('Compare cardiac output in phase1',provider=p,max_steps=8,commit='0'*40)
    assert result['verification']['passed'],result['verification']
    assert result['report']['status']==status
    assert p.turns==(4 if obey else 8) and p.nudges==1
    assert len([s for s in result['trace'] if s.get('tool_name')=='get_evidence'])==2
    assert ('Findings were selected by code' in result['report']['verified_summary']) is (not obey)
    validate_report(result['report'])


def test_exhaustion_after_run_auto_selects_and_fetches_missing_evidence(cached):
    p=FakeProvider([call('run_experiment',{'model':'phase1','intervention':{'heart_rate':90}})])
    result=loop.run_agent('Compare 심박출량 in phase1',provider=p,max_steps=1,commit='0'*40)
    assert result['report']['status']=='completed_with_warnings'
    assert result['report']['finding_selection']=='code_hypothesis_terms'
    assert result['verification']['passed'],result['verification']
    assert {f['metric_path'].split('.')[-1] for f in result['report']['findings']}=={'cardiac_output_l_min'}
    receipts=[s for s in result['trace'] if s.get('initiated_by')=='code']
    assert len(receipts)==1 and receipts[0]['tool_name']=='get_evidence'
    validate_report(result['report'])


def test_model_authored_receipt_fields_and_values_are_ignored(cached):
    script=list(FakeProvider.for_experiment('phase1',{'heart_rate':90},cycles=1).responses)
    final=script[-1]
    def malicious(messages):
        response=final(messages);r=json.loads(response['content'])
        r.update(hypothesis='invented',schema_version='wrong',status='completed_auto',
                 parameter_changes=[{'invented':True}],ontology_ids=['UBERON:9999999'],
                 evidence=[{'path':'invented'}],runs=[],verified_summary='invented',limitations=[])
        for f in r['findings']:
            f.update(value=999999,decimals=4,label='invented',unit='invented',direction='decrease')
        response['content']=json.dumps(r);return response
    result=loop.run_agent('Compare stroke volume in phase1',provider=FakeProvider(script[:-1]+[malicious]),commit='0'*40)
    report=result['report']
    assert result['verification']['passed'] and not result['verification']['repair_attempted']
    assert report['hypothesis']=='Compare stroke volume in phase1'
    assert report['parameter_changes']==[{'run_id':cached['run_id'],**c} for c in cached['parameter_changes']]
    assert report['evidence']==get_evidence('heart_rate')
    assert 'invented' not in json.dumps(report) and 'UBERON:9999999' not in report['ontology_ids']
    assert all(f['decimals'] is None and f['value']!=999999 for f in report['findings'])
    validate_report(report)


def test_grounding_includes_only_related_lookup_ids_and_all_run_changes(receipt):
    other=deepcopy(receipt);other['run_id']='second-run';other['baseline_overrides']={'emax_lv':2.5}
    runs={r['run_id']:r for r in (receipt,other)}
    lookups=[lookup_ontology('heart'),lookup_ontology('aortic_valve')]
    evidence=relevant_evidence([('heart_rate',get_evidence('heart_rate'))],runs,lookups)
    raw={'model':'phase1','findings':[{'run_id':rid,'metric_path':'delta.abs.stroke_volume_ml'} for rid in runs]}
    report=prepare_report(raw,runs,hypothesis='test',evidence_receipts=evidence,ontology_receipts=lookups)
    assert len(report['parameter_changes'])==2 and len(report['runs'])==2
    assert lookups[0]['entities'][0]['id'] in report['ontology_ids']
    assert lookups[1]['entities'][0]['id'] not in report['ontology_ids']
    assert verify_report(report,runs,hypothesis='test',evidence_receipts=evidence,ontology_receipts=lookups)['passed']
    # Verification rejects a forged code-filled field independently of preparation.
    report['findings'][0]['value']+=1
    assert not verify_report(report,runs,evidence_receipts=evidence,ontology_receipts=lookups)['passed']


@pytest.mark.parametrize('hypothesis,expected',[
    ('cardiac output','cardiac_output_l_min'),('심박출량을 비교','cardiac_output_l_min'),
    ('stroke volume','stroke_volume_ml'),('일회 박출량을 비교','stroke_volume_ml'),
    ('폐동맥 압력 변화','pa_pressure_mean_mmhg'),('left ventricular pressure','lv_pressure_mean_mmhg'),
])
def test_en_ko_metric_alias_selection(receipt,hypothesis,expected):
    assert expected in select_metrics(hypothesis,receipt)


def test_defaults_follow_each_models_valve_topology(receipt):
    run=deepcopy(receipt);run['parameter_changes']=[{'parameter':'resistance_mitral','baseline':.01,'intervention':.03}]
    assert set(select_metrics('unspecified result',run))=={
        'cardiac_output_l_min','stroke_volume_ml','pv_pressure_mean_mmhg','lv_pressure_mean_mmhg'}
    run['model']='m1';run['baseline']['metrics']['la_pressure_mean_mmhg']=1
    run['intervention']['metrics']['la_pressure_mean_mmhg']=2;run['delta']['abs']['la_pressure_mean_mmhg']=1
    assert set(select_metrics('unspecified result',run))=={
        'cardiac_output_l_min','stroke_volume_ml','la_pressure_mean_mmhg','lv_pressure_mean_mmhg'}


def test_auto_completion_gets_only_mapping_tool_verifier_eval_credit(monkeypatch,cached):
    path=Path(__file__).resolve().parents[1]/'agent_eval/run_eval.py'
    spec=importlib.util.spec_from_file_location('eval_v21',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    result=loop.run_agent('Compare cardiac output in phase1',provider=FakeProvider([
        call('run_experiment',{'model':'phase1','intervention':{'heart_rate':90}})]),max_steps=1,commit='0'*40)
    monkeypatch.setattr(module,'run_agent',lambda *args,**kwargs:result)
    case={'id':'auto','in_scope':True,'model':'phase1','intervention':{'heart_rate':90},
          'expected_parameters':['heart_rate'],'metric':'cardiac_output_l_min','expected_sign':'increase',
          'hypothesis':'Compare cardiac output in phase1'}
    scored=module.evaluate([case],reference_runs=[cached]);row=scored['cases'][0]
    assert row['mapping_tool_verifier_pass'] and row['completed_auto']
    assert not row['passed'] and row['sign_correct'] is None
    assert scored['summary']['completed_auto_mapping_tool_verifier_pass']==1


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    import socket
    def forbidden(*args,**kwargs):
        raise AssertionError('network forbidden in v2.1 agent tests')
    monkeypatch.setattr(socket,'create_connection',forbidden)
    monkeypatch.setattr(socket.socket,'connect',forbidden)


@pytest.mark.parametrize('provider,token_field',[('openai','max_completion_tokens'),('anthropic','max_tokens')])
def test_tool_free_final_payload_is_not_scope_classifier(provider,token_field):
    from io import BytesIO
    from physiosim.agent.llm import ChatProvider, ProviderConfig
    payloads=[]
    def opener(req,timeout):
        payloads.append(json.loads(req.data))
        return BytesIO(json.dumps({'choices':[{'message':{'content':'{}'}}]}).encode())
    p=ChatProvider(ProviderConfig(provider=provider,model='test',base_url='https://example.invalid/v1',
                                  api_key='fake',extra={token_field:1600}),opener=opener)
    p.complete([{'role':'system','content':loop.SYSTEM_PROMPT},{'role':'user','content':loop.FINAL_NUDGE}],[])
    payload=payloads[0]
    assert 'tools' not in payload and payload[token_field]==1600
    schema=payload['response_format']['json_schema']
    assert schema['name']=='final_message' and schema['schema']['required']==['model','findings']


def test_context_counter_counts_turns_and_resets_on_run(cached):
    script=[call('get_evidence',{'entity_or_param':'heart_rate'}),
            call('list_parameters',{'model':'phase1'}),
            call('run_experiment',{'model':'phase1','intervention':{'heart_rate':90}}),
            call('get_evidence',{'entity_or_param':'heart_rate'}),
            call('run_experiment',{'model':'phase1','intervention':{'heart_rate':90}})]
    batch=call('get_evidence',{'entity_or_param':'heart_rate'})
    batch['tool_calls']*=2  # Two calls still constitute one model turn.
    script += [batch,call('list_parameters',{'model':'phase1'})]
    def final(messages):
        assert messages[-1]=={'role':'user','content':loop.FINAL_NUDGE}
        assert len([m for m in messages if m.get('content')==loop.FINAL_NUDGE])==1
        return {'content':json.dumps({'model':'phase1','findings':[
            {'run_id':cached['run_id'],'metric_path':'delta.abs.stroke_volume_ml'}]})}
    script.append(final)
    class CheckingProvider(FakeProvider):
        def complete(self,messages,tools,*,deadline=None,tool_choice='auto'):
            if not messages[0]['content'].startswith('SCOPE_CLASSIFIER.'):
                assert tools == loop.TOOL_SCHEMAS
                assert tool_choice == ('none' if messages[-1].get('content')==loop.FINAL_NUDGE else 'auto')
            return super().complete(messages,tools,deadline=deadline,tool_choice=tool_choice)
    result=loop.run_agent('Compare stroke volume',provider=CheckingProvider(script),max_steps=8,commit='0'*40)
    assert result['verification']['passed'] and result['report']['status']=='completed_with_warnings'


def test_evidence_fallback_fetches_each_changed_or_overridden_parameter(monkeypatch,receipt):
    run=deepcopy(receipt)
    run['parameter_changes'].append({'parameter':'emax_lv','baseline':2.5,'intervention':1.25})
    run['baseline_overrides']={'initial_volumes.lv':150.}
    real=loop.dispatch
    monkeypatch.setattr(loop,'dispatch',lambda name,args:deepcopy(run) if name=='run_experiment' else real(name,args))
    result=loop.run_agent('Compare outputs',provider=FakeProvider([
        call('run_experiment',{'model':'phase1','intervention':{'heart_rate':90}})]),max_steps=1,commit='0'*40)
    assert result['verification']['passed'],result['verification']
    code_calls=[s for s in result['trace'] if s.get('initiated_by')=='code']
    assert len(code_calls)==3
    for name in ('heart_rate','emax_lv','initial_volumes.lv'):
        assert all(e in result['report']['evidence'] for e in get_evidence(name))
