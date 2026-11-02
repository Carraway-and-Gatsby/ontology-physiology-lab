"""Bounded tool loop, deterministic guard, one repair, verified JSON report."""
from copy import deepcopy
import json
import math
import re
import time
from . import LIMITATIONS
from .guard import check_scope, REFUSAL, SYSTEM_GUARD, classifier_messages
from .llm import ChatProvider, provider_config, ProviderError, redact
from .provenance import (build_provenance, engine_commit, utc_now, text_receipt, assistant_receipt,
                         argument_receipt, tool_result_receipt)
from .tools import dispatch, compact_timeseries, TOOL_FUNCTIONS
from .tool_protocol import TOOL_SCHEMAS, tool_arguments, parse_json as _parse
from .narrative import prepare_report, run_details, verified_summary, metric_value, metric_display
from .budget import Deadline, BudgetExceeded
from .selection import select_findings, selection_basis
from .verify import verify_report, mark_unverified, relevant_evidence


SYSTEM_PROMPT = '''You run ontology-grounded in-silico experiments on this repository's synthetic cardiovascular models.
Use tools for all results; never invent numbers or infer them from textbook physiology.
phase1 is a six-compartment ring without atria; m1 is an eight-compartment model with passive atria and a synthetic fixture.
Inspect list_parameters for names/ranges; use lookup_ontology/get_evidence when useful. Select the requested model and run_experiment. Dotted volume ports address tuple entries.
Once results are available, reply with one JSON object only:
{"model":"phase1 or m1","findings":[{"run_id":"actual run ID","metric_path":"delta.abs.stroke_volume_ml"}]}
Choose requested metrics from actual run results. Paths must be baseline.metrics.KEY, intervention.metrics.KEY, delta.abs.KEY or delta.rel.KEY, with finite values. Include a finding for every successful run.
Code fills the hypothesis, parameter changes, runs, ontology IDs, evidence, exact values, labels, units, directions, verified summary and limitations. Do not copy or author these fields.
No medical advice or clinical questions.
''' + '\n' + SYSTEM_GUARD + '\nFixed refusal: '+REFUSAL

FINAL_NUDGE = 'You have the run results. Reply now with the final JSON: {model, findings[{run_id, metric_path}]}.'
CONTEXT_TOOLS = {'list_parameters','lookup_ontology','get_evidence','get_timeseries'}


def report_from_run(hypothesis, run, *, metric='stroke_volume_ml', evidence=None):
    """Deterministic report builder for offline demonstrations and budget-stop receipts."""
    findings = [{'run_id':run['run_id'],'metric_path':prefix+metric}
                for prefix in ('baseline.metrics.','intervention.metrics.','delta.abs.')]
    return prepare_report({'model':run['model'],'findings':findings}, {run['run_id']:run},
                          hypothesis=hypothesis,evidence_receipts=evidence or [])


def _budget_metrics(hypothesis, run, findings):
    metrics = []
    for finding in findings:
        if not isinstance(finding,dict) or finding.get('run_id') != run['run_id']:
            continue
        try:
            metric_value(run,finding.get('metric_path'))
            metrics.append(finding['metric_path'].split('.')[-1])
        except (KeyError,ValueError,TypeError):
            continue
    if metrics:
        return list(dict.fromkeys(metrics))
    text = hypothesis.casefold()
    aliases = {'la_pressure_mean_mmhg':['la pressure','left atrial pressure','좌심방압'],
               'ra_pressure_mean_mmhg':['ra pressure','right atrial pressure'],
               'stroke_volume_ml':['stroke volume','1회 박출량'],
               'cardiac_output_l_min':['cardiac output']}
    for metric in run['baseline']['metrics']:
        label,_ = metric_display('baseline.metrics.'+metric)
        if any(re.search(r'(?<!\w)'+re.escape(term)+r'(?!\w)',text)
               for term in [metric,label.casefold(),*aliases.get(metric,[])]):
            try:
                metric_value(run,'baseline.metrics.'+metric)
                metric_value(run,'intervention.metrics.'+metric)
                metric_value(run,'delta.abs.'+metric)
            except (KeyError,ValueError,TypeError):
                continue
            metrics.append(metric)
    return list(dict.fromkeys(metrics)) or ['stroke_volume_ml']


def _run_agent(hypothesis, *, provider=None, provider_name='meta', model=None, extra=None, max_steps=8, commit=None,
               max_experiments=6, no_classifier=False, deadline=None):
    if isinstance(max_steps,bool) or not isinstance(max_steps,int) or not 1 <= max_steps <= 32:
        raise ValueError('max_steps must be an integer in [1,32]')
    deadline = deadline or Deadline(None)
    started = utc_now(); tick = time.perf_counter()
    trace = []; runs = {}; evidence = []; ontology = []; experiment_calls = 0
    classifier_result = {'attempted':False,'in_scope':None,'reason':'deterministic refusal or disabled'}
    usage = {'prompt_tokens':0,'completion_tokens':0,'total_tokens':0,'model_calls':0}
    scope = check_scope(hypothesis)
    provider_label = getattr(provider,'provider',provider_name)
    model_label = getattr(provider,'model',model or ('muse-spark-1.3' if provider_name == 'meta' else 'unspecified'))
    commit = engine_commit() if commit is None else commit
    def finish(report,verification):
        usage['latency_s'] = time.perf_counter()-tick
        return {'report':report,'verification':verification,'trace':trace,
                'provenance':build_provenance(hypothesis if isinstance(hypothesis,str) else '',trace,
                    provider=provider_label,model=model_label,started_at=started,ended_at=utc_now(),commit=commit,report=report),
                'usage':usage,'classifier':classifier_result}
    if not scope['allowed']:
        return finish({'schema_version':'2.1','status':'refused','refusal':REFUSAL,'limitations':list(LIMITATIONS)},
                      {'passed':True,'guarded':True,'failures':[],'verified_claims':[],'unverified_claims':[]})
    try:
        if provider is None:
            provider = ChatProvider(provider_config(provider_name,model,extra=extra))
            provider_label, model_label = provider.provider, provider.model
    except ProviderError as exc:
        trace.append({'step':0,'kind':'model' if no_classifier else 'classifier','model_message':None,
                      'intent':None,'tool_name':None,'error':redact(' '.join(str(exc).split()))[:200],
                      'started_at':started,'ended_at':utc_now(),'timing_s':time.perf_counter()-tick,'usage':{}})
        report = {'schema_version':'2.1','status':'error','error':'Provider unavailable.','limitations':list(LIMITATIONS)} if no_classifier else {
            'schema_version':'2.1','status':'refused','refusal':REFUSAL,'guard_note':'Scope classifier unavailable.','limitations':list(LIMITATIONS)}
        return finish(report, {'passed':False,'guarded':not no_classifier,
            'failures':[{'path':'provider' if no_classifier else 'classifier','reason':'Provider unavailable.'}],
            'verified_claims':[],'unverified_claims':[]})
    messages = [{'role':'system','content':SYSTEM_PROMPT},{'role':'user','content':hypothesis}]
    secrets = (getattr(getattr(provider,'config',None),'api_key',''),)
    def safe(obj):
        return json.loads(redact(json.dumps(obj,ensure_ascii=False,allow_nan=False),secrets))
    last_findings = []
    def complete(repair=False, classifier=False, no_tools=False):
        nonlocal last_findings
        stamp = utc_now(); clock = time.perf_counter()
        kind = 'classifier' if classifier else 'repair' if repair else 'model'
        usage['model_calls'] += 1
        try:
            deadline.check()
            response = provider.complete(classifier_messages(hypothesis) if classifier else deepcopy(messages),
                                         [] if classifier else TOOL_SCHEMAS, deadline=deadline,
                                         tool_choice='none' if repair or no_tools else 'auto')
            raw = response['message']
            if not isinstance(raw,dict):
                raise ProviderError('Invalid assistant message.')
            # Free content is ephemeral. Only tool arguments need credential redaction;
            # hash the original text rather than an altered/redacted copy.
            message = {k:deepcopy(raw[k]) for k in ('role','content') if k in raw}
            if 'tool_calls' in raw:
                message['tool_calls'] = safe(raw['tool_calls'])
            message['role'] = 'assistant'
            token_usage = response.get('usage') or {}
            call_usage = {}
            for k in ('prompt_tokens','completion_tokens','total_tokens'):
                val = token_usage.get(k,0)
                if isinstance(val,int) and not isinstance(val,bool) and val >= 0:
                    usage[k] += val
                    call_usage[k] = val
            receipt = assistant_receipt(message)
        except (ProviderError,ValueError,TypeError,KeyError,AttributeError,BudgetExceeded) as exc:
            cause = str(exc) if isinstance(exc,(ProviderError,BudgetExceeded)) else 'Invalid provider response.'
            trace.append({'step':len(trace),'kind':kind,'model_message':None,'intent':None,
                          'tool_name':None,'error':redact(' '.join(cause.split()),secrets)[:200], 'started_at':stamp,
                          'ended_at':utc_now(),'timing_s':time.perf_counter()-clock,'usage':{}})
            raise
        trace.append({'step':len(trace),'kind':kind,'model_message':receipt,'intent':None,
                      'tool_name':None,'started_at':stamp,'ended_at':utc_now(),
                      'timing_s':time.perf_counter()-clock,'usage':call_usage})
        if not classifier:
            try:
                structured = _parse(message.get('content',''))
                if isinstance(structured,dict) and isinstance(structured.get('findings'),list):
                    last_findings = structured['findings']
            except (ValueError,TypeError):
                pass
        # Final replies can be verified locally using receipts already obtained.
        if classifier or message.get('tool_calls'):
            deadline.check()
        return message
    def report_context():
        # Empty/unrelated model queries cannot prevent receipt grounding. Local only.
        if runs:
            names = dict.fromkeys(name for run in runs.values() for name in
                                  [c['parameter'] for c in run['parameter_changes']]+list(run['baseline_overrides']))
            for name in names:
                if relevant_evidence(evidence,runs,ontology,parameter=name):
                    continue
                stamp = utc_now(); clock = time.perf_counter()
                args = {'entity_or_param':name}
                result = dispatch('get_evidence',args)
                if isinstance(result,list):
                    evidence.append((name,deepcopy(result)))
                trace.append({'step':len(trace),'kind':'tool','model_message':None,'intent':None,
                              'tool_name':'get_evidence','initiated_by':'code',
                              'args':safe(argument_receipt('get_evidence',json.dumps(args))),
                              'result':safe(tool_result_receipt('get_evidence',result)),
                              'result_summary':safe(tool_result_receipt('get_evidence',result)),
                              'started_at':stamp,'ended_at':utc_now(),'timing_s':time.perf_counter()-clock})
        related = relevant_evidence(evidence,runs,ontology)
        return {'hypothesis':hypothesis,'evidence_receipts':related,'ontology_receipts':ontology}

    def code_report(context):
        basis = selection_basis(hypothesis,runs)
        report = prepare_report({'model':next(iter(runs.values()))['model'],
                                 'findings':select_findings(hypothesis,runs)},
                                runs,**context,finding_selection=basis)
        return report,verify_report(report,runs,**context,finding_selection=basis)

    final = None
    auto_selected = False
    context_turns = 0
    nudge_pending = False
    nudged = False
    response_hash = None
    try:
        if not no_classifier:
            classifier_result['attempted'] = True
            try:
                answer = complete(classifier=True)
                decision = _parse(answer.get('content',''))
                if answer.get('tool_calls') or not isinstance(decision,dict) or set(decision) != {'in_scope','reason'} or type(decision['in_scope']) is not bool or not isinstance(decision['reason'],str):
                    raise ValueError('classifier must return strict in_scope/reason JSON')
                classifier_result.update(in_scope=decision['in_scope'],reason='Scope classifier accepted.' if decision['in_scope'] else 'Scope classifier refused.')
            except (ProviderError,ValueError,TypeError,KeyError,AttributeError,BudgetExceeded) as exc:
                classifier_result.update(in_scope=False,reason='classifier unavailable or invalid')
                if trace and 'error' not in trace[-1]:
                    trace[-1]['error'] = ('Session wall-clock budget exhausted.' if isinstance(exc,BudgetExceeded)
                                          else 'Invalid scope classifier response.')
            if not classifier_result['in_scope']:
                note = 'Scope classifier unavailable.' if classifier_result['reason'] == 'classifier unavailable or invalid' else 'Scope classifier refused.'
                return finish({'schema_version':'2.1','status':'refused','refusal':REFUSAL,'guard_note':note,'limitations':list(LIMITATIONS)},
                    {'passed':True,'guarded':True,'failures':[],'verified_claims':[],'unverified_claims':[]})
        for _ in range(max_steps):
            force_final = nudge_pending or nudged
            if nudge_pending:
                messages.append({'role':'user','content':FINAL_NUDGE})
                nudge_pending = False; nudged = True
            try:
                message = complete(no_tools=force_final)
            except ProviderError:
                if force_final and runs:
                    break  # Preserve successful receipts through code selection.
                raise
            messages.append(message)
            calls = message.get('tool_calls') or []
            if not calls:
                try:
                    final = _parse(message.get('content',''))
                except (ValueError,TypeError):
                    final = {}
                response_hash = text_receipt(message.get('content'))
                break
            if not isinstance(calls,list) or len(calls) > 16:
                raise ProviderError('invalid or excessive tool calls in assistant response')
            if force_final:
                # Keep the protocol valid if a provider ignores tool_choice=none.
                # Tools remain disabled until a final reply or the model step limit.
                for call in calls:
                    if not isinstance(call,dict) or not isinstance(call.get('id'),str):
                        raise ProviderError('invalid disabled tool call')
                    messages.append({'role':'tool','tool_call_id':call['id'],
                                     'content':'{"error":"tools_disabled"}'})
                continue
            turn_names = []
            for call in calls:
                function = call.get('function') if isinstance(call,dict) else None
                function = function if isinstance(function,dict) else {}
                name = function.get('name')
                name = name if isinstance(name,str) and name in TOOL_FUNCTIONS else 'unknown_tool'
                turn_names.append(name)
                raw_args = function.get('arguments','{}')
                deadline.check()
                stamp = utc_now(); clock = time.perf_counter()
                try:
                    args = tool_arguments(name,raw_args)
                    if name == 'run_experiment':
                        if experiment_calls >= max_experiments:
                            result = {'error':'budget_exhausted'}
                        else:
                            experiment_calls += 1
                            result = dispatch(name,args)
                    else:
                        result = dispatch(name,args)
                except (ValueError,TypeError):
                    args = {}; result = {'error':{'code':'unknown_tool' if name == 'unknown_tool' else 'invalid_arguments',
                                                 'message':'Unknown tool or invalid tool arguments.'}}
                if name == 'run_experiment' and isinstance(result,dict) and 'run_id' in result:
                    runs[result['run_id']] = deepcopy(result)
                if name == 'get_evidence' and isinstance(result,list):
                    evidence.append((args.get('entity_or_param',''),deepcopy(result)))
                if name == 'lookup_ontology' and isinstance(result,dict) and 'entities' in result:
                    ontology.append(deepcopy(result))
                if name == 'get_timeseries' and isinstance(result,dict) and 'baseline' in result:
                    result = compact_timeseries(args['run_id'],args.get('names'))
                summary = ({'run_id':result['run_id'],'model':result['model'],
                            'parameter_changes':result['parameter_changes'],'warnings':result['warnings']}
                           if isinstance(result,dict) and 'settings' in result and 'run_id' in result else result)
                trace.append({'step':len(trace),'kind':'tool','model_message':None,'intent':None,
                              'tool_name':name,'args':safe(argument_receipt(name,raw_args)),
                              'result':safe(tool_result_receipt(name,result)),
                              'result_summary':safe(tool_result_receipt(name,summary)),
                              'started_at':stamp,'ended_at':utc_now(),'timing_s':time.perf_counter()-clock})
                messages.append({'role':'tool','name':name,'tool_call_id':call.get('id','missing-id') if isinstance(call,dict) else 'missing-id',
                                 'content':json.dumps(result,allow_nan=False,ensure_ascii=False)})
                deadline.check()
            if runs and turn_names and set(turn_names) <= CONTEXT_TOOLS:
                context_turns += 1
            else:
                context_turns = 0
            if context_turns >= 2 and not nudged:
                nudge_pending = True
        if final is None and runs:
            auto_selected = True
            final = {'model':next(iter(runs.values()))['model'],'findings':select_findings(hypothesis,runs)}
        if final is None:
            return finish(mark_unverified(None,{},response_hash=response_hash),
                          {'passed':False,'failures':[{'path':'loop','reason':'max_steps exhausted'}],
                           'verified_claims':[],'unverified_claims':[]})
        context = report_context()
        if auto_selected:
            final,verification = code_report(context)
        else:
            final = prepare_report(final,runs,**context)
            verification = verify_report(final,runs,**context)
        if not verification['passed'] and not auto_selected:
            # Quote the exact failed rules and a valid session-backed finding so the
            # single repair round has concrete guidance for every failing field.
            example = None
            for run_id,run in runs.items():
                for metric,value in run['baseline']['metrics'].items():
                    if isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value):
                        example = {'run_id':run_id,'metric_path':'baseline.metrics.'+metric}
                        break
                if example is not None:
                    break
            guidance = {'failing_rules':verification['failures'],
                        'allowed_finding_example':example,
                        'verification':verification}
            messages.append({'role':'user','content':'Repair your final JSON exactly once using the existing tool receipts. '
                             'Do not call tools. Exact failing rules are quoted in failing_rules. '
                             'The allowed examples illustrate the schema; preserve every session run and requested metric. '
                             +json.dumps(guidance)})
            try:
                repair = complete(repair=True)
            except ProviderError:
                if runs:
                    final,verification = code_report(context)
                    verification['repair_attempted'] = True
                    if not verification['passed']:
                        final = mark_unverified(final,verification,response_hash=response_hash)
                    return finish(final,verification)
                verification['repair_attempted'] = True
                return finish(mark_unverified(final,verification,response_hash=response_hash),verification)
            except (ValueError,TypeError,KeyError,AttributeError):
                verification['repair_attempted'] = True
                return finish(mark_unverified(final,verification,response_hash=response_hash),verification)
            try:
                final = _parse(repair.get('content','')) if not repair.get('tool_calls') else {}
            except (ValueError,TypeError):
                final = {}
            response_hash = text_receipt(repair.get('content'))
            final = prepare_report(final,runs,**context)
            verification = verify_report(final,runs,**context)
            verification['repair_attempted'] = True
        else:
            verification['repair_attempted'] = False
        if not verification['passed']:
            final = mark_unverified(final,verification,response_hash=response_hash)
        return finish(final,verification)
    except BudgetExceeded:
        # A completed solve is recorded before checking the deadline again.
        report = {'schema_version':'2.1','status':'stopped_budget',
                  'note':'Session wall-clock budget exhausted.', 'limitations':list(LIMITATIONS),
                  'runs':run_details(runs), 'findings':[],
                  'parameter_changes':[{'run_id':rid,**c} for rid,r in runs.items() for c in r['parameter_changes']]}
        for rid,run in runs.items():
            for metric in _budget_metrics(hypothesis,run,last_findings):
                part = report_from_run(hypothesis,run,metric=metric)
                for f in part['findings']:
                    f['id'] = 'finding-'+str(len(report['findings']))
                    report['findings'].append(f)
        if runs:
            report['verified_summary'] = verified_summary(report,runs)
        return finish(report, {'passed':False,'failures':[{'path':'budget','reason':'Session wall-clock budget exhausted.'}],
                              'verified_claims':[f['id'] for f in report['findings']], 'unverified_claims':[]})
    except (ProviderError,KeyError,TypeError,ValueError,AttributeError):
        return finish({'schema_version':'2.1','status':'error','error':'Session failed.', 'limitations':list(LIMITATIONS)},
                      {'passed':False,'failures':[{'path':'loop','reason':'Session failed.'}],
                       'verified_claims':[],'unverified_claims':[]})


def run_agent(hypothesis, *, provider=None, provider_name='meta', model=None, extra=None,
              max_steps=8, commit=None, wall_clock_s=180, max_experiments=6, no_classifier=False):
    """Cooperative deadline, bounded HTTP requests and capped solver cycles.

    A synchronous solver/custom provider finishes its current call before the next
    deadline check. None disables the session deadline; request timeouts still apply.
    """
    if isinstance(max_experiments,bool) or not isinstance(max_experiments,int) or max_experiments < 1:
        raise ValueError('max_experiments must be a positive integer')
    return _run_agent(hypothesis,provider=provider,provider_name=provider_name,model=model,extra=extra,
                      max_steps=max_steps,commit=commit,max_experiments=max_experiments,no_classifier=no_classifier,
                      deadline=Deadline(wall_clock_s))
