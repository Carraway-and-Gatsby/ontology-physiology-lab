"""Shared tool schemas and strict validation before execution or persistence."""
import json
import math
from .tools import MAX_CYCLES, TOOL_FUNCTIONS


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


def parse_json(content):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result
    def constant(value):
        raise ValueError('nonfinite JSON constant')
    return json.loads(content, object_pairs_hook=pairs, parse_constant=constant)


def _matches(value, schema):
    if 'oneOf' in schema:
        return sum(_matches(value, branch) for branch in schema['oneOf']) == 1
    kind = schema.get('type')
    if kind == 'object':
        if not isinstance(value, dict) or not set(schema.get('required', ())) <= set(value):
            return False
        props = schema.get('properties', {})
        extra = schema.get('additionalProperties', True)
        return all(_matches(v, props[k]) if k in props else
                   extra is True or (isinstance(extra, dict) and _matches(v, extra))
                   for k, v in value.items())
    if kind == 'array':
        return isinstance(value, list) and all(_matches(v, schema['items']) for v in value)
    if kind == 'string':
        return isinstance(value, str) and ('enum' not in schema or value in schema['enum'])
    if kind in ('number', 'integer'):
        return (type(value) in ((int,) if kind == 'integer' else (int, float))
                and (type(value) is int or math.isfinite(value))
                and ('minimum' not in schema or value >= schema['minimum'])
                and ('maximum' not in schema or value <= schema['maximum'])
                and ('exclusiveMinimum' not in schema or value > schema['exclusiveMinimum']))
    return False


def tool_arguments(name, content):
    """Return a schema-valid object or raise without reflecting model text."""
    if not isinstance(name, str) or name not in TOOL_FUNCTIONS:
        raise ValueError('unknown tool')
    args = parse_json(content)
    schema = next(s['function']['parameters'] for s in TOOL_SCHEMAS if s['function']['name'] == name)
    if not _matches(args, schema):
        raise ValueError('invalid tool arguments')
    return args
