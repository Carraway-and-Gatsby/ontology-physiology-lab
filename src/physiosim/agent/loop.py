"""Bounded tool loop, deterministic guard, one repair, verified JSON report."""
from copy import deepcopy
import json
import math
import time
from . import LIMITATIONS
from .catalog import catalogue
from .guard import check_scope, REFUSAL, SYSTEM_GUARD
from .llm import ChatProvider, provider_config, ProviderError, redact
from .provenance import build_provenance, engine_commit, utc_now
from .tools import dispatch, MAX_CYCLES
from .verify import verify_report, mark_unverified, direction_of, SUMMARY_RULE, SUMMARY_EXAMPLE


def _schema(name, description, properties, required):
    return {'type':'function','function':{'name':name,'description':description,
            'parameters':{'type':'object','properties':properties,'required':required,'additionalProperties':False}}}


MODEL = {'type':'string','enum':['phase1','m1']}
OVERRIDES = {'type':'object','additionalProperties':{'type':'number'}}
INTERVENTION = {'type':'object','additionalProperties':{'oneOf':[{'type':'number'},
    {'type':'object','properties':{'scale':{'type':'number','exclusiveMinimum':0}},'required':['scale'],'additionalProperties':False}]}}
TOOL_SCHEMAS = [
    _schema('list_parameters','Inspect exact synthetic defaults, conservative ranges, units and existing ontology contexts before choosing parameters.',{'model':MODEL},['model']),
    _schema('lookup_ontology','Find offline anatomical identifiers and source relation claims; these do not calibrate parameters.',{'query':{'type':'string'}},['query']),
    _schema('run_experiment','Run the actual engine with paired solver settings; all report numbers must cite this output.',
            {'model':MODEL,'intervention':INTERVENTION,'baseline_overrides':OVERRIDES,
             'cycles':{'type':'integer','minimum':1,'maximum':MAX_CYCLES}},['model','intervention']),
    _schema('get_evidence','Retrieve exact local implementation/evidence pointers; returns an empty list when unknown.',
            {'entity_or_param':{'type':'string'}},['entity_or_param']),
    _schema('get_timeseries','Get downsampled final-beat traces from bounded in-memory storage for a UI.',
            {'run_id':{'type':'string'},'names':{'type':'array','items':{'type':'string'}}},['run_id']),
]

SYSTEM_PROMPT = '''You are a research assistant for ontology-grounded in-silico experiments on this repository's specific synthetic cardiovascular models.
Use the actual tools for every number; do not estimate, invent, cite memory or infer a result from textbook physiology.
phase1 is a six-compartment ring without separate atria. m1 is an eight-compartment model with passive atria using the explicit synthetic fixture.
Use list_parameters to inspect valid names/ranges and lookup_ontology/get_evidence for context before run_experiment. Select the model the user requests. Ask no clinical questions. Dotted volume parameters such as initial_volumes.lv address tuple entries.
Every successful engine run must be represented in the report. Copy ALL parameter_changes exactly from run outputs, adding run_id to each. Cite only IDs from tools and copy evidence records verbatim from get_evidence.
Final answer MUST be one JSON object, no Markdown, with EXACTLY these keys:
{"schema_version":"1.0","status":"completed","hypothesis":"exact user hypothesis","model":"phase1 or m1","summary":"qualitative summary following the summary rule below","parameter_changes":[{"run_id":"...","parameter":"...","baseline":0.0,"intervention":0.0}],"ontology_ids":["existing CURIE or IRI"],"evidence":["exact objects returned by get_evidence"],"findings":[{"id":"unique string","label":"qualitative metric label without numbers or direction words","run_id":"...","metric_path":"baseline.metrics.KEY or intervention.metrics.KEY or delta.abs.KEY or delta.rel.KEY","value":0.0,"decimals":6,"direction":null}],"limitations":[]}
Every numeric finding must give a valid run_id and metric_path, and equal Python round(tool_value, decimals), decimals integer 0..12. A relative delta is a fraction, not a percentage. direction is null, increase, decrease or unchanged and must match the unrounded absolute delta for that metric. Finding labels must omit quantities and directions. No extra JSON keys. Repeat the canonical limitations below verbatim in limitations. An ontology ID's presence does not prove a hypothesis was mapped correctly. Admit null bindings and unsteady runs; never claim clinical validity.
Summary rule: ''' + SUMMARY_RULE + '\nAllowed summary example: '+json.dumps(SUMMARY_EXAMPLE)+'''
Canonical limitations: ''' + json.dumps(LIMITATIONS) + '\n' + SYSTEM_GUARD + '\nFixed refusal: '+REFUSAL


def report_from_run(hypothesis, run, *, metric='stroke_volume_ml', evidence=None):
    """Deterministic report builder used only by the offline scripted demonstration."""
    findings = []
    for i, path in enumerate(('baseline.metrics.'+metric, 'intervention.metrics.'+metric, 'delta.abs.'+metric)):
        a,b,k = path.split('.')
        findings.append({'id':'finding-'+str(i),'label':metric.replace('_',' '),'run_id':run['run_id'],
                         'metric_path':path,'value':round(run[a][b][k],6),'decimals':6,
                         'direction':direction_of(run['delta']['abs'][metric]) if a == 'delta' else None})
    ids = []
    for change in run['parameter_changes']:
        p = next(p for p in catalogue(run['model']) if p['name'] == change['parameter'])
        if p['binding'] and p['binding']['primary_id'] not in ids:
            ids.append(p['binding']['primary_id'])
    return {'schema_version':'1.0','status':'completed','hypothesis':hypothesis,'model':run['model'],
            'summary':'The paired synthetic experiment completed; inspect the cited metrics and settling warnings.',
            'parameter_changes':[{'run_id':run['run_id'],**c} for c in run['parameter_changes']],
            'ontology_ids':ids,'evidence':evidence or [],'findings':findings,'limitations':list(LIMITATIONS)}


def _parse(content):
    # Reject non-standard NaN/Infinity and duplicate object keys.
    def pairs(items):
        result = {}
        for k,v in items:
            if k in result:
                raise ValueError('duplicate JSON key')
            result[k] = v
        return result
    def constant(value):
        raise ValueError('nonfinite JSON constant')
    return json.loads(content,object_pairs_hook=pairs,parse_constant=constant)


def run_agent(hypothesis, *, provider=None, provider_name='meta', model=None, extra=None, max_steps=8, commit=None):
    if isinstance(max_steps,bool) or not isinstance(max_steps,int) or not 1 <= max_steps <= 32:
        raise ValueError('max_steps must be an integer in [1,32]')
    started = utc_now(); tick = time.perf_counter()
    trace = []; runs = {}; evidence = []
    usage = {'prompt_tokens':0,'completion_tokens':0,'total_tokens':0,'model_calls':0}
    scope = check_scope(hypothesis)
    provider_label = getattr(provider,'provider',provider_name)
    model_label = getattr(provider,'model',model or ('muse-spark-1.3' if provider_name == 'meta' else 'unspecified'))
    commit = engine_commit() if commit is None else commit
    def finish(report,verification):
        usage['latency_s'] = time.perf_counter()-tick
        return {'report':report,'verification':verification,'trace':trace,
                'provenance':build_provenance(hypothesis if isinstance(hypothesis,str) else '',trace,
                    provider=provider_label,model=model_label,started_at=started,ended_at=utc_now(),commit=commit),
                'usage':usage}
    if not scope['allowed']:
        return finish({'schema_version':'1.0','status':'refused','refusal':REFUSAL,'limitations':list(LIMITATIONS)},
                      {'passed':True,'guarded':True,'failures':[],'verified_claims':[],'unverified_claims':[]})
    try:
        if provider is None:
            provider = ChatProvider(provider_config(provider_name,model,extra=extra))
            provider_label, model_label = provider.provider, provider.model
    except ProviderError as exc:
        return finish({'status':'error','error':str(exc)}, {'passed':False,'failures':[{'path':'provider','reason':str(exc)}],
                      'verified_claims':[],'unverified_claims':[]})
    messages = [{'role':'system','content':SYSTEM_PROMPT},{'role':'user','content':hypothesis}]
    secrets = (getattr(getattr(provider,'config',None),'api_key',''),)
    def safe(obj):
        return json.loads(redact(json.dumps(obj,ensure_ascii=False,allow_nan=False),secrets))
    def complete(repair=False):
        stamp = utc_now(); clock = time.perf_counter()
        response = provider.complete(deepcopy(messages),TOOL_SCHEMAS)
        # Keep only protocol fields; never echo arbitrary vendor response metadata.
        raw = response['message']
        message = safe({k:raw[k] for k in ('role','content','tool_calls') if k in raw})
        message['role'] = 'assistant'
        token_usage = response.get('usage') or {}
        for k in ('prompt_tokens','completion_tokens','total_tokens'):
            val = token_usage.get(k,0)
            if isinstance(val,int) and not isinstance(val,bool) and val >= 0:
                usage[k] += val
        usage['model_calls'] += 1
        trace.append({'step':len(trace),'kind':'repair' if repair else 'model','model_message':message,
                      'intent':message.get('content'),'tool_name':None,'started_at':stamp,'ended_at':utc_now(),
                      'timing_s':time.perf_counter()-clock, 'usage':{k:token_usage.get(k,0) for k in ('prompt_tokens','completion_tokens','total_tokens')}})
        return message
    final = None
    try:
        for _ in range(max_steps):
            message = complete(); messages.append(message)
            calls = message.get('tool_calls') or []
            if not calls:
                try:
                    final = _parse(message.get('content',''))
                except (ValueError,TypeError):
                    final = {'invalid_response':message.get('content')}
                break
            if not isinstance(calls,list) or len(calls) > 16:
                raise ProviderError('invalid or excessive tool calls in assistant response')
            for call in calls:
                function = call.get('function',{})
                name = function.get('name','')
                stamp = utc_now(); clock = time.perf_counter()
                try:
                    args = _parse(function.get('arguments','{}'))
                    result = dispatch(name,args)
                except (ValueError,TypeError):
                    args = {}; result = {'error':{'code':'invalid_arguments','message':'arguments must be valid JSON'}}
                if name == 'run_experiment' and isinstance(result,dict) and 'run_id' in result:
                    runs[result['run_id']] = deepcopy(result)
                if name == 'get_evidence' and isinstance(result,list):
                    for item in result:
                        if item not in evidence:
                            evidence.append(deepcopy(item))
                summary = ({'run_id':result['run_id'],'model':result['model'],
                            'parameter_changes':result['parameter_changes'],'warnings':result['warnings']}
                           if isinstance(result,dict) and 'settings' in result and 'run_id' in result else result)
                trace.append({'step':len(trace),'kind':'tool','model_message':None,'intent':message.get('content'),
                              'tool_name':name,'args':safe(args),'result':safe(result),'result_summary':safe(summary),
                              'started_at':stamp,'ended_at':utc_now(),'timing_s':time.perf_counter()-clock})
                messages.append({'role':'tool','name':name,'tool_call_id':call.get('id','missing-id'),
                                 'content':json.dumps(result,allow_nan=False,ensure_ascii=False)})
        if final is None:
            return finish({'status':'unverified','error':'maximum model steps reached without a final JSON report'},
                          {'passed':False,'failures':[{'path':'loop','reason':'max_steps exhausted'}],
                           'verified_claims':[],'unverified_claims':[]})
        verification = verify_report(final,runs,hypothesis=hypothesis,evidence_receipts=evidence)
        if not verification['passed']:
            # Quote the exact failed rules and a valid session-backed finding so the
            # single repair round has concrete guidance for every failing field.
            example = None
            for run_id,run in runs.items():
                for metric,value in run['baseline']['metrics'].items():
                    if isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value):
                        example = {'id':'example-finding','label':'Baseline metric','run_id':run_id,
                                   'metric_path':'baseline.metrics.'+metric,'value':round(value,6),
                                   'decimals':6,'direction':None}
                        break
                if example is not None:
                    break
            guidance = {'failing_rules':verification['failures'],
                        'allowed_summary_example':SUMMARY_EXAMPLE,'allowed_finding_example':example,
                        'verification':verification}
            messages.append({'role':'user','content':'Repair your final JSON exactly once using the existing tool receipts. '
                             'Do not call tools. Exact failing rules are quoted in failing_rules. '
                             'The allowed examples illustrate the schema; preserve every session run and requested metric. '
                             +json.dumps(guidance)})
            repair = complete(repair=True)
            try:
                final = _parse(repair.get('content','')) if not repair.get('tool_calls') else {'invalid_response':'repair attempted tools'}
            except (ValueError,TypeError):
                final = {'invalid_response':repair.get('content')}
            verification = verify_report(final,runs,hypothesis=hypothesis,evidence_receipts=evidence)
            verification['repair_attempted'] = True
        else:
            verification['repair_attempted'] = False
        if not verification['passed']:
            final = mark_unverified(final,verification)
        return finish(final,verification)
    except (ProviderError,KeyError,TypeError,ValueError,AttributeError) as exc:
        reason = redact(str(exc),secrets)
        return finish({'status':'error','error':reason}, {'passed':False,'failures':[{'path':'loop','reason':reason}],
                      'verified_claims':[],'unverified_claims':[]})
