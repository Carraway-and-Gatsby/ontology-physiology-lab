"""Deterministic offline ONTO-R1/R2 snapshots; invoke with PYTHONPATH=src."""
import argparse
import json
from pathlib import Path
from physiosim.ontology.contracts import build_contract_bundle, agent_path_projection


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true',help='Compare without writing.')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    bundle=build_contract_bundle()
    knowledge_path=root/'src/physiosim/agent/knowledge.json'
    knowledge=json.loads(knowledge_path.read_text())
    knowledge['flow_paths']={('m1' if m.model_id=='four_chamber_m1' else m.model_id):agent_path_projection(m) for m in bundle.models}
    outputs={knowledge_path:json.dumps(knowledge,indent=2,ensure_ascii=False)+'\n',
             root/'src/physiosim/ontology/quantity_contracts.json':bundle.to_json()}
    for path,content in outputs.items():
        if args.check:
            if not path.exists() or path.read_text()!=content:
                raise SystemExit('stale projection: '+str(path))
        else: path.write_text(content)
    print('canonical contracts and G4 knowledge projection match' if args.check else 'wrote canonical contracts and G4 knowledge projection')


if __name__=='__main__':main()
