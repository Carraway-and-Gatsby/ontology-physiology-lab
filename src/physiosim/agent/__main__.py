"""python -m physiosim.agent --dry-run (offline real-engine demonstration)."""
import argparse
import json
from pathlib import Path
from .llm import FakeProvider, ProviderError, parse_extra_json
from .loop import run_agent
from .provenance import serialize


def _extra_json(value):
    try:
        return parse_extra_json(value)
    except ProviderError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from None


def main(argv=None):
    parser = argparse.ArgumentParser(description='Synthetic research experiments; no medical advice.')
    parser.add_argument('hypothesis',nargs='?',default='If mitral valve resistance triples, what happens to left atrial pressure in the M1 model?')
    parser.add_argument('--provider',choices=('openai','anthropic','meta','custom'),default='meta')
    parser.add_argument('--model')
    parser.add_argument('--extra-json',type=_extra_json,help='JSON object of request fields; overrides preset defaults and LAB_LLM_EXTRA_JSON.')
    parser.add_argument('--out',type=Path,default=Path('agent_eval/cli-output'))
    parser.add_argument('--dry-run',action='store_true',help='Scripted mapping and local engine; no network calls. Fixed M1 triple mitral experiment.')
    parser.add_argument('--max-steps',type=int,default=8)
    parser.add_argument('--wall-clock-s',type=float,default=180)
    parser.add_argument('--max-experiments',type=int,default=6)
    parser.add_argument('--no-classifier',action='store_true',help='Disable the extra scope classifier; deterministic guard remains active.')
    args = parser.parse_args(argv)
    provider = FakeProvider.for_experiment(metric='la_pressure_mean_mmhg') if args.dry_run else None
    result = run_agent(args.hypothesis,provider=provider,provider_name=args.provider,model=args.model,
                       extra=args.extra_json,max_steps=args.max_steps,wall_clock_s=args.wall_clock_s,
                       max_experiments=args.max_experiments,no_classifier=args.no_classifier)
    args.out.mkdir(parents=True,exist_ok=True)
    payloads = {'report.json':{'report':result['report'],'verification':result['verification'],'usage':result['usage']},
                'trace.json':result['trace'],'provenance.jsonld':result['provenance']}
    # Refuse overwriting unrelated artifacts; write each reviewed output exclusively.
    if any((args.out/name).exists() for name in payloads):
        parser.error('output files already exist; choose another --out directory')
    for name,payload in payloads.items():
        (args.out/name).write_text(serialize(payload),encoding='utf-8')
    print('Synthetic research model; not clinically validated. No medical advice.')
    print('Status:',result['report'].get('status','unknown'))
    print('Verification:', 'PASS' if result['verification']['passed'] else 'FAIL / UNVERIFIED')
    if args.dry_run:
        print('Offline scripted mapping: M1, mitral resistance scaled by three; this does not test natural-language mapping.')
    if result['report'].get('verified_summary'):
        print(('VERIFIED RECEIPT NARRATIVE' if result['verification']['passed'] else 'UNVERIFIED REPORT'))
        print(result['report']['verified_summary'])
    if result['report'].get('refusal'):
        print(result['report']['refusal'])
    for name in payloads:
        print(str((args.out/name).resolve()))
    return 0 if result['verification']['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
