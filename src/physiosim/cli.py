"""Command-line entry point; never requires a network or LLM to simulate."""
import argparse
import json
from pathlib import Path
from physiosim.experiments.runner import run_experiment


def main(argv=None):
    parser = argparse.ArgumentParser(description='EXPERIMENTAL cardiovascular simulations; not for clinical use')
    parser.add_argument('--config', type=Path, help='JSON numerical settings; defaults match experiments/phase1.json')
    parser.add_argument('--output', type=Path, default=Path('results/phase1'))
    args = parser.parse_args(argv)
    try:
        config = json.loads(args.config.read_text()) if args.config else None
        if config is not None and not isinstance(config, dict):
            raise ValueError('configuration must be a JSON object')
        report = run_experiment(args.output, config)
    except (ValueError, OSError, RuntimeError) as exc:
        parser.exit(1, f'Experiment failed: {exc}\n')
    print('EXPERIMENTAL SIMULATIONS — not clinically validated')
    for name, scenario in report['scenarios'].items():
        m = scenario['metrics']
        print(f"{name}: CO={m['cardiac_output_l_min']:.6f} L/min; SV={m['stroke_volume_ml']:.6f} mL; {scenario['status']}")
    print(f'Results: {args.output.resolve()}')
    if not report['all_periodic']:
        print('At least one run did not meet the declared periodicity gate; outputs retained as transients.')
        return 2
    return 0
