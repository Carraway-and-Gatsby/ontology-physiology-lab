#!/usr/bin/env python3
"""Evaluate a provider; --provider fake is offline infrastructure validation only."""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
import time

# The shared venv is installed against a different checkout; use this worktree.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from physiosim.agent.llm import FakeProvider, ChatProvider, provider_config, ProviderError
from physiosim.agent.guard import classifier_messages
from physiosim.agent.loop import _parse
from physiosim.agent.loop import run_agent
from physiosim.agent.verify import direction_of


def derive_alias_groups(reference_runs):
    """Same model, all reference conditions, 1e-12 relative; no hand-coded aliases."""
    groups = {}
    for model in sorted({r['model'] for r in reference_runs}):
        vectors = [r[c]['metrics'] for r in reference_runs if r['model']==model for c in ('baseline','intervention')]
        keys = sorted(set.intersection(*(set(v) for v in vectors)))
        def equal(a,b):
            return all(type(v[a]) in (int,float) and type(v[b]) in (int,float) and
                       math.isfinite(v[a]) and math.isfinite(v[b]) and
                       math.isclose(v[a],v[b],rel_tol=1e-12,abs_tol=0) for v in vectors)
        partitions = []
        for key in keys:
            group = next((g for g in partitions if all(equal(key,other) for other in g)),None)
            if group is None:
                partitions.append([key])
            else:
                group.append(key)
        groups[model] = [g for g in partitions if len(g)>1]
    return groups


def aliases_for(groups,model,metric):
    return next((set(g) for g in groups.get(model,[]) if metric in g),{metric})


def score_classifier(provider,hypothesis):
    """Standalone score even when the deterministic veto short-circuited the agent."""
    try:
        response = provider.complete(classifier_messages(hypothesis),[])
        message = response['message']; decision = _parse(message.get('content',''))
        if message.get('tool_calls') or not isinstance(decision,dict) or set(decision) != {'in_scope','reason'} or type(decision['in_scope']) is not bool or not isinstance(decision['reason'],str):
            raise ValueError('invalid classifier JSON')
        return {'in_scope':decision['in_scope'],'reason':'Scope classifier accepted.' if decision['in_scope'] else 'Scope classifier refused.',
                'error':None,'usage':response.get('usage',{})}
    except (ProviderError,ValueError,KeyError,TypeError) as exc:
        return {'in_scope':False,'reason':'classifier failed closed','error':str(exc),'usage':{}}


def evaluate(cases, *, provider_name='fake', model=None, reference_runs=None):
    rows = []
    if reference_runs is None:
        reference_runs = json.loads(Path(__file__).with_name('reference_runs.json').read_text())
    alias_groups = derive_alias_groups(reference_runs)
    for case in cases:
        provider = (FakeProvider.for_experiment(case.get('model','m1'),case.get('intervention'),
                    metric=case.get('metric','stroke_volume_ml'),cycles=case.get('cycles'))
                    if provider_name == 'fake' else None)
        started = time.perf_counter()
        result = run_agent(case['hypothesis'],provider=provider,provider_name=provider_name,model=model)
        elapsed = time.perf_counter()-started
        tools = [s for s in result['trace'] if s.get('tool_name')]
        runs = [s['result'] for s in tools if s['tool_name'] == 'run_experiment' and isinstance(s.get('result'),dict) and 'run_id' in s['result']]
        actual_parameters = sorted({c['parameter'] for r in runs for c in r['parameter_changes']})
        actual_model = {r['model'] for r in runs}
        expected = sorted(case.get('expected_parameters',[]))
        status = result['report'].get('status')
        finding_selection = result['report'].get('finding_selection')
        completed_auto = finding_selection in ('code_hypothesis_terms','code_default_set')
        guarded = status == 'refused'
        in_scope = case['in_scope']
        mapping = bool(runs) and actual_parameters == expected and actual_model == {case.get('model')} if in_scope else not runs
        numeric = result['verification']['passed'] and (bool(runs) if in_scope else guarded)
        sign_ok = None
        actual_sign = None
        if in_scope and runs and case['metric'] in runs[-1]['delta']['abs']:
            actual_sign = direction_of(runs[-1]['delta']['abs'][case['metric']])
            accepted_metrics = aliases_for(alias_groups,case['model'],case['metric'])
            claims = [f for f in result['report'].get('findings',[]) if f.get('metric_path') in
                {prefix+metric for metric in accepted_metrics for prefix in ('delta.abs.','delta.rel.')} and f.get('direction') == case['expected_sign']]
            sign_ok = actual_sign == case['expected_sign'] and bool(claims)
        if completed_auto:
            sign_ok = None  # Code selection earns no model-authored sign/interpretation credit.
        classifier = result['classifier']
        if not classifier.get('attempted'):
            try:
                classifier = score_classifier(provider or ChatProvider(provider_config(provider_name,model)),case['hypothesis'])
            except ProviderError as exc:
                classifier = {'in_scope':False,'error':str(exc)}
        classifier_correct = classifier.get('in_scope') == in_scope and not classifier.get('error') and not classifier.get('reason','').startswith('classifier unavailable')
        row = {'status':status,'finding_selection':finding_selection,'completed_auto':completed_auto,'classifier':classifier,'classifier_correct':bool(classifier_correct),'id':case['id'],'in_scope':in_scope,'correct_parameter_mapping':mapping,
               'tool_use':bool(runs) if in_scope else not tools,
               'verifier_pass':numeric,'guard_correct':guarded == (not in_scope),
               'expected_sign':case.get('expected_sign'),'actual_sign':actual_sign,'sign_correct':sign_ok,
               'steps':result['usage']['model_calls'], 'tool_calls':len(tools),
               'tokens':result['usage'].get('total_tokens',0),'latency_s':elapsed,
               'actual_parameters':actual_parameters, 'verification_failures':result['verification'].get('failures',[]),
               'result':result}
        row['mapping_tool_verifier_pass'] = all(row[k] for k in ('correct_parameter_mapping','tool_use','verifier_pass'))
        row['passed'] = not completed_auto and all(row[k] for k in ('correct_parameter_mapping','tool_use','verifier_pass','guard_correct')) and (sign_ok is not False)
        rows.append(row)
    return {'provider':provider_name,'model':model or ('scripted-offline' if provider_name == 'fake' else 'provider configured'),
            'metric_alias_groups':alias_groups,
            'generated_at':datetime.now(timezone.utc).isoformat(),
            'caveat':'FakeProvider receives expected parameters and uses scripted tool calls; a passing fake score verifies plumbing, not LLM interpretation or mapping quality.' if provider_name == 'fake' else 'Tool consistency does not establish physiological or clinical validity.',
            'summary':{'cases':len(rows),'passed':sum(r['passed'] for r in rows),
                       'completed_auto':sum(r['completed_auto'] for r in rows),
                       'completed_auto_mapping_tool_verifier_pass':sum(r['completed_auto'] and r['mapping_tool_verifier_pass'] for r in rows),
                       **{k:sum(bool(r[k]) for r in rows) for k in ('correct_parameter_mapping','tool_use','verifier_pass','guard_correct','classifier_correct')},
                       'tokens':sum(r['tokens'] for r in rows),'latency_s':sum(r['latency_s'] for r in rows)},
            'cases':rows}


def markdown(result):
    lines = ['# Synthetic experiment agent evaluation','',result['caveat'],'',
             '| Case | Status | Selection | Mapping | Tools | Verifier | Guard | Classifier | Sign | Steps | Tokens | Seconds |',
             '| --- | --- | --- | --- | --- | --- | --- | --- | --- | ---: | ---: | ---: |']
    for row in result['cases']:
        cell = lambda v: '—' if v is None else 'pass' if v else 'FAIL'
        lines.append('| '+row['id']+' | '+str(row['status'])+' | '+str(row['finding_selection'] or '—')+' | '+' | '.join(cell(row[k]) for k in ('correct_parameter_mapping','tool_use','verifier_pass','guard_correct','classifier_correct','sign_correct'))+
                     f" | {row['steps']} | {row['tokens']} | {row['latency_s']:.3f} |")
    return '\n'.join(lines)+'\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--provider',choices=('fake','meta','openai','anthropic','custom'),default='fake')
    parser.add_argument('--model')
    parser.add_argument('--cases',type=Path,default=Path(__file__).with_name('hypotheses.json'))
    parser.add_argument('--out',type=Path,default=Path(__file__).with_name('results'))
    args = parser.parse_args(argv)
    cases = json.loads(args.cases.read_text())['cases']
    result = evaluate(cases,provider_name=args.provider,model=args.model)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/'results.json').write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    (args.out/'results.md').write_text(markdown(result))
    print(markdown(result))
    print(json.dumps(result['summary']))
    return 0 if result['summary']['passed'] == len(cases) else 1


if __name__ == '__main__':
    raise SystemExit(main())
