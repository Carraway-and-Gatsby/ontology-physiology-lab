import json, pathlib, argparse

def source_nodes(side):
    return [{"id": x["record"]["template_uri"], "label": x["record"]["key"], "layer": "source", "record": x["record"], "provenance": x["provenance"]} for x in side["source"]["catalog"]]

def source_edges(side):
    return [{"id": x["record"]["claim_id"], "layer": "source_claim", "claim_id": x["record"]["claim_id"], "source": x["record"]["sourceTemplate"], "target": x["record"]["targetTemplate"], "predicate": x["record"]["relation"], "record": x["record"], "provenance": x["provenance"]} for x in side["source"]["claims"]]

def catalog_nodes(catalog):
    return [{"id": "catalog:"+x["key"], "label": x["structure"], "layer": "catalog", "record": x, "provenance": "inputs/anatomy_nodes_v2.json#/nodes/"+str(i)} for i,x in enumerate(catalog["nodes"])]

def dependency_edges(side):
    return [{"id": "dependency:%s:%s"%(i,j), "source": "model:"+on, "target": "model:"+d["dependent"], "layer": "model_reference", "predicate": "dependency (on → dependent)", "record": d, "provenance": "inputs/applied_sidecar.json#/dependencies/%s/on/%s"%(i,j)} for i,d in enumerate(side["dependencies"]) for j,on in enumerate(d["on"])]

def encode(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).replace("<", "\\u003c")

def valid(nodes, edges):
    ids=[n["id"] for n in nodes]; es=[e["id"] for e in edges]
    return len(ids)==len(set(ids)) and len(es)==len(set(es)) and all(e["source"] in ids and e["target"] in ids for e in edges)

def build_graph(input_dir):
    path = pathlib.Path(input_dir)
    side = json.loads((path/'applied_sidecar.json').read_text(encoding='utf-8'))
    catalog = json.loads((path/'anatomy_nodes_v2.json').read_text(encoding='utf-8'))
    manifest = json.loads((path/'m1_manifest.json').read_text(encoding='utf-8'))
    nodes = source_nodes(side) + catalog_nodes(catalog)
    edges = source_edges(side) + dependency_edges(side)
    for n in nodes:
        if n['layer'] == 'source':
            key = n['record']['key']
            n['crosswalk'] = side['crosswalk'].get(key)
            n['crosswalk_provenance'] = 'inputs/applied_sidecar.json#/crosswalk/'+key
            n['anatomy_role'] = side['anatomy_roles'].get(key)
    model = {}
    def add(name, section, record):
        n = model.setdefault(name, {'id':'model:'+name, 'label':name, 'layer':'model', 'records':{}, 'provenance':[]})
        n['records'][section] = record
        n['provenance'].append('inputs/applied_sidecar.json#/'+section+'/'+name.replace('~','~0').replace('/','~1'))
    for section in ('roles','variables','laws','parameters','parameter_roles','volume_references','ports'):
        for name, record in side[section].items(): add(name,section,record)
    for dep in side['dependencies']:
        for name in [dep['dependent']]+dep['on']:
            if name not in model: add(name,'dependency_name',name)
    for name,n in model.items():
        for section in ('variables','parameter_contract'):
            if name in manifest['semantic_contract'][section]:
                n['records']['manifest_'+section] = manifest['semantic_contract'][section][name]
                n['provenance'].append('inputs/m1_manifest.json#/semantic_contract/'+section+'/'+name)
    by_key = {n['record']['key']:n['id'] for n in nodes if n['layer']=='source'}
    for key, role in side['anatomy_roles'].items():
        if key not in model: add(key,'anatomy_roles',role)
        else:
            model[key]['records']['anatomy_roles']=role
            model[key]['provenance'].append('inputs/applied_sidecar.json#/anatomy_roles/'+key)
        edges.append({'id':'role:'+key, 'source':model[key]['id'], 'target':by_key[role['template']], 'layer':'model_reference', 'predicate':role['role'], 'record':role, 'provenance':'inputs/applied_sidecar.json#/anatomy_roles/'+key})
    for name, port in side['ports'].items():
        if port.get('ref') in model:
            edges.append({'id':'port:'+name,'source':model[name]['id'],'target':model[port['ref']]['id'],'layer':'model_reference','predicate':'port ref','record':port,'provenance':'inputs/applied_sidecar.json#/ports/'+name+'/ref'})
    nodes += list(model.values())
    scope = {'numeric_binding':'CLOSED','target_mapping':'PROPOSED','source_commit':'680bd29650d97957256dd05fd3281ee8403f6aed', 'external_numeric_permission':'NONE', 'source_review':side['status_axes'], 'crosswalk':side['crosswalk'], 'mitral':side['mitral'], 'boundaries':side['source']['boundaries'], 'special_claims':side['source']['special_claims'], 'unresolved_conflicts':side['evidence']['unresolved_conflicts'], 'evidence':side['evidence'], 'model_source':side['model_source'], 'catalog_metadata':{k:v for k,v in catalog.items() if k!='nodes'}, 'manifest_evidence':manifest['semantic_contract']['evidence_status'], 'manifest_unresolved_conflicts':manifest['semantic_contract']['unresolved_conflicts'], 'sidecar_original':side, 'manifest_original':manifest}
    assert valid(nodes,edges), 'duplicate or dangling graph identifiers'
    return {'nodes':nodes,'edges':edges,'scope':scope}

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--input-dir',required=True); parser.add_argument('--output-dir',required=True); args=parser.parse_args()
    graph=build_graph(args.input_dir); data=encode(graph)
    output=pathlib.Path(args.output_dir); output.mkdir(parents=True,exist_ok=True)
    (output/'graph-data.json').write_text(data,encoding='utf-8')
    template=(pathlib.Path(__file__).parent/'viewer.html').read_text(encoding='utf-8')
    (output/'index.html').write_text(template.replace('<!-- GRAPH_DATA -->',data),encoding='utf-8')
if __name__=='__main__': main()
