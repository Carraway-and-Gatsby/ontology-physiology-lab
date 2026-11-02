#!/usr/bin/env python3
"""Evaluate a provider; --provider fake is offline infrastructure validation only."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

# The shared venv is installed against a different checkout; use this worktree.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from physiosim.agent.llm import FakeProvider
from physiosim.agent.loop import run_agent
from physiosim.agent.verify import direction_of


def evaluate(cases, *, provider_name='fake', model=None):
    rows = []
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
        guarded = result['report'].get('status') == 'refused'
        in_scope = case['in_scope']
        mapping = bool(runs) and actual_parameters == expected and actual_model == {case.get('model')} if in_scope else not runs
        numeric = result['verification']['passed'] and (bool(runs) if in_scope else guarded)
        sign_ok = None
        actual_sign = None
        if in_scope and runs and case['metric'] in runs[-1]['delta']['abs']:
            actual_sign = direction_of(runs[-1]['delta']['abs'][case['metric']])
            claims = [f for f in result['report'].get('findings',[]) if f.get('metric_path') in (
                'delta.abs.'+case['metric'],'delta.rel.'+case['metric']) and f.get('direction') == case['expected_sign']]
            sign_ok = actual_sign == case['expected_sign'] and bool(claims)
        row = {'id':case['id'],'in_scope':in_scope,'correct_parameter_mapping':mapping,
               'tool_use':bool(runs) if in_scope else not tools,
               'verifier_pass':numeric,'guard_correct':guarded == (not in_scope),
               'expected_sign':case.get('expected_sign'),'actual_sign':actual_sign,'sign_correct':sign_ok,
               'steps':result['usage']['model_calls'], 'tool_calls':len(tools),
               'tokens':result['usage'].get('total_tokens',0),'latency_s':elapsed,
               'actual_parameters':actual_parameters, 'verification_failures':result['verification'].get('failures',[]),
               'result':result}
        row['passed'] = all(row[k] for k in ('correct_parameter_mapping','tool_use','verifier_pass','guard_correct')) and (sign_ok is not False)
        rows.append(row)
    return {'provider':provider_name,'model':model or ('scripted-offline' if provider_name == 'fake' else 'provider configured'),
            'generated_at':datetime.now(timezone.utc).isoformat(),
            'caveat':'FakeProvider receives expected parameters and uses scripted tool calls; a passing fake score verifies plumbing, not LLM interpretation or mapping quality.' if provider_name == 'fake' else 'Tool consistency does not establish physiological or clinical validity.',
            'summary':{'cases':len(rows),'passed':sum(r['passed'] for r in rows),
                       **{k:sum(bool(r[k]) for r in rows) for k in ('correct_parameter_mapping','tool_use','verifier_pass','guard_correct')},
                       'tokens':sum(r['tokens'] for r in rows),'latency_s':sum(r['latency_s'] for r in rows)},
            'cases':rows}


def markdown(result):
    lines = ['# Synthetic experiment agent evaluation','',result['caveat'],'',
             '| Case | Mapping | Tools | Verifier | Guard | Sign | Steps | Tokens | Seconds |',
             '| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: |']
    for row in result['cases']:
        cell = lambda v: '—' if v is None else 'pass' if v else 'FAIL'
        lines.append('| '+row['id']+' | '+' | '.join(cell(row[k]) for k in ('correct_parameter_mapping','tool_use','verifier_pass','guard_correct','sign_correct'))+
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
