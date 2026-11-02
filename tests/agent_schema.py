"""Offline validator for the JSON Schema subset in report.schema.json (tests only)."""
import json
import math
from pathlib import Path
import re

SCHEMA = json.loads((Path(__file__).resolve().parents[1]/'src/physiosim/agent/report.schema.json').read_text())


def validate_report(report):
    try:
        import jsonschema
    except ImportError:
        validate(report, SCHEMA)
    else:
        jsonschema.Draft202012Validator.check_schema(SCHEMA)
        jsonschema.validate(report, SCHEMA)


def validate(value, schema, path='$'):
    if '$ref' in schema:
        assert schema['$ref'].startswith('#/$defs/')
        return validate(value, SCHEMA['$defs'][schema['$ref'].split('/')[-1]], path)
    if 'oneOf' in schema:
        matches=0
        for branch in schema['oneOf']:
            try:
                validate(value, branch, path)
            except AssertionError:
                pass
            else:
                matches+=1
        assert matches==1, f'{path}: expected one envelope, matched {matches}'
        return
    if 'const' in schema:
        assert value==schema['const'] and type(value)==type(schema['const']), f'{path}: const'
    if 'enum' in schema:
        assert any(value==v and type(value)==type(v) for v in schema['enum']), f'{path}: enum'
    types=schema.get('type',[])
    if isinstance(types,str):types=[types]
    checks={'object':lambda: isinstance(value,dict),'array':lambda: isinstance(value,list),
            'string':lambda: isinstance(value,str),'boolean':lambda: type(value) is bool,
            'number':lambda: type(value) in (int,float) and math.isfinite(value),
            'integer':lambda: type(value) is int,'null':lambda: value is None}
    if types:
        assert any(checks[t]() for t in types),f'{path}: type {types}'
    if isinstance(value,dict):
        assert set(schema.get('required',[]))<=set(value),f'{path}: required'
        props=schema.get('properties',{})
        extra=schema.get('additionalProperties',True)
        for k,v in value.items():
            if k in props:
                validate(v,props[k],path+'.'+k)
            elif extra is False:
                raise AssertionError(f'{path}: extra {k}')
            elif isinstance(extra,dict):
                validate(v,extra,path+'.'+k)
    if isinstance(value,list):
        assert len(value)>=schema.get('minItems',0),f'{path}: minItems'
        for i,v in enumerate(value):
            validate(v,schema.get('items',{}),f'{path}[{i}]')
    if isinstance(value,str):
        assert len(value)>=schema.get('minLength',0),f'{path}: minLength'
        if 'pattern' in schema:
            assert re.search(schema['pattern'],value),f'{path}: pattern'
    if type(value) in (int,float):
        if 'minimum' in schema:assert value>=schema['minimum'],f'{path}: minimum'
        if 'maximum' in schema:assert value<=schema['maximum'],f'{path}: maximum'
        if 'exclusiveMinimum' in schema:assert value>schema['exclusiveMinimum'],f'{path}: exclusiveMinimum'
