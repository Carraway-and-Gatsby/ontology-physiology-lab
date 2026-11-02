"""PROV-O JSON-LD without an RDF runtime dependency or remote contexts."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
from physiosim import __version__

CONTEXT = {'prov':'http://www.w3.org/ns/prov#', 'xsd':'http://www.w3.org/2001/XMLSchema#',
           'lab':'urn:physiosim:agent:',
           'prov:used':{'@type':'@id'}, 'prov:wasGeneratedBy':{'@type':'@id'},
           'prov:wasAssociatedWith':{'@type':'@id'}, 'prov:wasAttributedTo':{'@type':'@id'},
           'prov:startedAtTime':{'@type':'xsd:dateTime'}, 'prov:endedAtTime':{'@type':'xsd:dateTime'}}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def serialize(document):
    """Stable key ordering/whitespace for fixed timestamps, trace and inputs."""
    return json.dumps(document,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False)+'\n'


def engine_commit():
    try:
        root = Path(__file__).resolve().parents[3]
        result = subprocess.run(['git','-C',str(root),'rev-parse','HEAD'],capture_output=True,text=True,timeout=2,check=True)
        commit = result.stdout.strip()
        return commit if len(commit) == 40 and all(c in '0123456789abcdef' for c in commit) else None
    except (OSError,subprocess.SubprocessError):
        return None


def _json(value):
    return {'@value':value,'@type':'@json'}


def build_provenance(hypothesis, trace, *, provider, model, started_at, ended_at, commit=None):
    identity = sha256((hypothesis+'\n'+started_at+'\n'+provider+'\n'+model).encode()).hexdigest()[:24]
    base = 'urn:physiosim:session:'+identity+':'
    software = {'@id':base+'software','@type':['prov:Agent','prov:SoftwareAgent'],
                'prov:label':'physiosim synthetic experiment agent', 'lab:packageVersion':__version__,
                'lab:engineCommit':commit if commit is not None else 'unavailable',
                'lab:commitCaveat':'Commit identifies checkout HEAD; observed source hashes record runtime bytes and may include uncommitted changes.'}
    llm = {'@id':base+'llm','@type':['prov:Agent','prov:SoftwareAgent'],
           'prov:label':model,'lab:provider':provider,'lab:model':model}
    session = {'@id':base+'session','@type':'prov:Activity','prov:label':'synthetic research session',
               'prov:startedAtTime':started_at, 'prov:endedAtTime':ended_at,
               'prov:wasAssociatedWith':[software['@id'],llm['@id']],
               'lab:hypothesis':hypothesis,'lab:scope':'Synthetic, exploratory, not clinically validated. No medical advice.'}
    graph = [software,llm,session]
    for index, step in enumerate(trace):
        if not step.get('tool_name'):
            continue
        prefix = base+'tool-'+str(index)
        result = step.get('result',{})
        config = {'arguments':step.get('args',{})}
        if isinstance(result,dict) and 'run_id' in result and 'settings' in result:
            config.update(model=result['model'], baseline_parameters=result['baseline']['parameters'],
                          intervention_parameters=result['intervention']['parameters'], solver_settings=result['settings'],
                          engine_source_sha256=result['engine_source_sha256'])
        graph.extend([
            {'@id':prefix+':input','@type':'prov:Entity','prov:label':'tool input configuration', 'lab:configuration':_json(config)},
            {'@id':prefix,'@type':'prov:Activity','prov:label':step['tool_name'],
             'prov:startedAtTime':step['started_at'],'prov:endedAtTime':step['ended_at'],
             'prov:used':prefix+':input','prov:wasAssociatedWith':[software['@id'],llm['@id']],
             'lab:engineCommit':software['lab:engineCommit'],'lab:packageVersion':__version__,
             'lab:llmProvider':provider,'lab:llmModel':model},
            {'@id':prefix+':result','@type':'prov:Entity','prov:label':'tool output receipt',
             'prov:wasGeneratedBy':prefix,'prov:wasAttributedTo':software['@id'],
             'lab:runId':result.get('run_id','not-an-engine-run') if isinstance(result,dict) else 'not-an-engine-run',
             'lab:sha256':sha256(serialize(result).encode()).hexdigest(), 'lab:result':_json(result)},
        ])
    return {'@context':CONTEXT,'@graph':graph}
