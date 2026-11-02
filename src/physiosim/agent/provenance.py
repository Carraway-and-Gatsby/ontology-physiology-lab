"""PROV-O JSON-LD without an RDF runtime dependency or remote contexts."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
from physiosim import __version__
from .tool_protocol import tool_arguments
from .tools import TOOL_FUNCTIONS

CONTEXT = {'@version':1.1, 'rdfs':'http://www.w3.org/2000/01/rdf-schema#', 'prov':'http://www.w3.org/ns/prov#', 'xsd':'http://www.w3.org/2001/XMLSchema#',
           'lab':'urn:physiosim:agent:',
           'prov:used':{'@type':'@id'}, 'prov:wasInformedBy':{'@type':'@id'}, 'prov:wasDerivedFrom':{'@type':'@id'}, 'prov:wasGeneratedBy':{'@type':'@id'},
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


def text_receipt(content):
    """A free-text receipt records identity and size, never the source text."""
    if (isinstance(content, dict) and set(content) == {'sha256','chars','stored'} and content['stored'] is False
            and isinstance(content['sha256'],str) and len(content['sha256']) == 64
            and all(c in '0123456789abcdef' for c in content['sha256'])
            and type(content['chars']) is int and content['chars'] >= 0):
        return dict(content)
    text = content if isinstance(content,str) else json.dumps(content,sort_keys=True,ensure_ascii=False)
    return {'sha256':sha256(text.encode('utf-8')).hexdigest(), 'chars':len(text), 'stored':False}


def argument_receipt(name, content):
    try:
        args = tool_arguments(name, content)
    except (ValueError, TypeError):
        return text_receipt(content)
    # Free string values are data for execution, but only their digests persist.
    def strings(value):
        if isinstance(value,str):
            return text_receipt(value)
        if isinstance(value,list):
            return [strings(v) for v in value]
        if isinstance(value,dict):
            return {k:strings(v) for k,v in value.items()}
        return value
    return {k:v if k == 'model' else strings(v) for k,v in args.items()}


def tool_result_receipt(name, result):
    if isinstance(result,dict):
        result = dict(result)
        if name == 'lookup_ontology' and 'query' in result:
            result['query'] = text_receipt(result['query'])
        if isinstance(result.get('error'),dict) and 'message' in result['error']:
            result['error'] = {**result['error'],'message':text_receipt(result['error']['message'])}
    return result


def assistant_receipt(message):
    if not isinstance(message,dict):
        return None
    result = {'role':'assistant'}
    if message.get('content') is not None:
        result['content'] = text_receipt(message['content'])
    if message.get('tool_calls'):
        calls = message['tool_calls']
        result['tool_calls'] = []
        for call in calls if isinstance(calls,list) else []:
            function = call.get('function') if isinstance(call,dict) else None
            function = function if isinstance(function,dict) else {}
            name = function.get('name')
            name = name if isinstance(name,str) and name in TOOL_FUNCTIONS else 'unknown_tool'
            result['tool_calls'].append({'function':{'name':name,
                'arguments':argument_receipt(name,function.get('arguments','{}'))}})
    return result


def build_provenance(hypothesis, trace, *, provider, model, started_at, ended_at, commit=None, report=None):
    identity = sha256((hypothesis+'\n'+started_at+'\n'+provider+'\n'+model).encode()).hexdigest()[:24]
    base = 'urn:physiosim:session:'+identity+':'
    software = {'@id':base+'software','@type':['prov:Agent','prov:SoftwareAgent'],
                'rdfs:label':'physiosim synthetic experiment agent', 'lab:packageVersion':__version__,
                'lab:engineCommit':commit if commit is not None else 'unavailable',
                'lab:commitCaveat':'Commit identifies checkout HEAD; observed source hashes record runtime bytes and may include uncommitted changes.'}
    llm = {'@id':base+'llm','@type':['prov:Agent','prov:SoftwareAgent'],
           'rdfs:label':model,'lab:provider':provider,'lab:model':model}
    session = {'@id':base+'session','@type':'prov:Activity','rdfs:label':'synthetic research session',
               'prov:startedAtTime':started_at, 'prov:endedAtTime':ended_at,
               'prov:wasAssociatedWith':[software['@id'],llm['@id']],
               'lab:hypothesis':hypothesis,'lab:scope':'Synthetic, exploratory, not clinically validated. No medical advice.'}
    graph = [software,llm,session]
    previous = session['@id']
    for index, step in enumerate(trace):
        if not step.get('tool_name') and step.get('kind') not in ('classifier','model','repair'):
            continue
        prefix = base+('tool-' if step.get('tool_name') else step['kind']+'-')+str(index)
        is_tool = bool(step.get('tool_name'))
        # The loop has already built the validated, redacted assistant receipt.
        result = step.get('result') if is_tool else step.get('model_message')
        config = {'arguments':step.get('args',{})}
        if isinstance(result,dict) and 'run_id' in result and 'settings' in result:
            config.update(model=result['model'], baseline_parameters=result['baseline']['parameters'],
                          intervention_parameters=result['intervention']['parameters'], solver_settings=result['settings'],
                          engine_source_sha256=result['engine_source_sha256'])
        graph.extend([
            {'@id':prefix+':input','@type':'prov:Entity','rdfs:label':'tool input configuration' if is_tool else 'model call configuration', 'lab:configuration':_json(config)},
            {'@id':prefix,'@type':'prov:Activity','rdfs:label':step.get('tool_name') or step['kind'], 'prov:wasInformedBy':list(dict.fromkeys([session['@id'],previous])),
             'prov:startedAtTime':step['started_at'],'prov:endedAtTime':step['ended_at'],
             'prov:used':prefix+':input','prov:wasAssociatedWith':[software['@id'],llm['@id']],
             'lab:engineCommit':software['lab:engineCommit'],'lab:packageVersion':__version__,
             'lab:llmProvider':provider,'lab:llmModel':model},
            {'@id':prefix+':result','@type':'prov:Entity','rdfs:label':'tool output receipt' if is_tool else 'assistant message digest',
             'prov:wasGeneratedBy':prefix,'prov:wasAttributedTo':software['@id'] if is_tool else llm['@id'],
             'lab:runId':result.get('run_id','not-an-engine-run') if isinstance(result,dict) else 'not-an-engine-run',
             'lab:sha256':sha256(serialize(result).encode()).hexdigest(),
             **({'lab:sourceSha256':result['source_sha256']} if step.get('tool_name') == 'get_timeseries' and 'source_sha256' in result else {'lab:result':_json(result)})},
        ])
        previous = prefix
    cited = {f.get('run_id') for f in (report or {}).get('findings',[]) if isinstance(f,dict)}
    derived = [n['@id'] for n in graph if n.get('@type') == 'prov:Entity' and n.get('lab:runId') in cited]
    graph.append({'@id':base+'report','@type':'prov:Entity','rdfs:label':'session report',
                  'prov:wasGeneratedBy':session['@id'],'prov:wasDerivedFrom':derived,
                  'lab:sha256':sha256(serialize(report).encode()).hexdigest()})
    return {'@context':CONTEXT,'@graph':graph}
