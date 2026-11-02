"""Closed-schema verification of code-generated narrative and session receipts."""
from copy import deepcopy
import math
import json
from . import LIMITATIONS
from .catalog import catalogue
from .narrative import (metric_value, metric_display, metric_direction, direction_of,
    sufficient_precision, verified_summary, run_details, completion_status, FINDING_KEYS)

REPORT_KEYS = {'schema_version','status','hypothesis','model','verified_summary','runs','parameter_changes','ontology_ids','evidence','findings','limitations'}
SUMMARY_RULE = 'verified_summary must exactly equal the deterministic receipt narrative.'
SUMMARY_EXAMPLE = 'The synthetic model comparison is available in the verified receipt narrative.'


def changed_ports(runs):
    return [p for run in runs.values() for p in catalogue(run['model'])
            if p['name'] in {c['parameter'] for c in run['parameter_changes']} | set(run['baseline_overrides'])]


def grounding_ids(runs, ontology_receipts=()):
    ids = {v for p in changed_ports(runs) if p['binding'] for item in p['binding']['ids']
           for v in (item['id'],item['iri']) if v}
    for receipt in ontology_receipts:
        for entity in receipt.get('entities',[]):
            ids.update(x for x in [entity.get('id'),entity.get('iri'),*entity.get('identifiers',[])] if x)
    return ids


def relevant_evidence(receipts, runs, ontology_receipts=()):
    """Only get_evidence calls for session interventions/overrides or their entities."""
    ports = changed_ports(runs)
    queries = {p['name'] for p in ports}
    for p in ports:
        b = p['binding']
        if b:
            queries.update((b['key'],b['label']))
            queries.update(v for item in b['ids'] for v in (item['id'],item['iri']) if v)
    for receipt in ontology_receipts:
        for entity in receipt.get('entities',[]):
            if any(x.get('parameter') in queries for x in entity.get('related_parameters',[])):
                queries.update(v for v in [entity.get('id'),entity.get('iri'),entity.get('key'),entity.get('label'),
                                          *entity.get('identifiers',[])] if v)
    normalize = lambda s:s.casefold().replace('_',' ').strip()
    queries = {normalize(q) for q in queries}
    return [deepcopy(item) for query,items in receipts if normalize(query) in queries for item in items]


def verify_report(report, runs, *, hypothesis=None, evidence_receipts=None, ontology_receipts=()):
    failures = []; verified = []; invalid = []
    def fail(path,reason):
        failures.append({'path':path,'reason':reason})
    if not isinstance(report,dict):
        return {'passed':False,'failures':[{'path':'report','reason':'report must be a JSON object'}],
                'verified_claims':[], 'unverified_claims':[]}
    for key in sorted(REPORT_KEYS-set(report)):
        fail(key,'required field missing')
    for key in sorted(set(report)-REPORT_KEYS):
        fail(key,'unknown field: untracked claims are forbidden')
    if report.get('schema_version') != '2.0':
        fail('schema_version','must be 2.0')
    if report.get('status') != completion_status(runs):
        fail('status','must reflect all session warnings and periodicity flags')
    if not isinstance(report.get('hypothesis'),str) or (hypothesis is not None and report['hypothesis'] != hypothesis):
        fail('hypothesis','must echo the original hypothesis exactly')
    if not runs:
        fail('findings','at least one successful engine tool run is required')
    if report.get('model') not in ('phase1','m1') or any(r['model'] != report.get('model') for r in runs.values()):
        fail('model','must match every session run; one model per report')
    try:
        exact_runs = json.dumps(report.get('runs'),sort_keys=True,allow_nan=False) == json.dumps(run_details(runs),sort_keys=True,allow_nan=False)
    except (ValueError,TypeError):
        exact_runs = False
    if not exact_runs:
        fail('runs','baseline_overrides and diagnostics must exactly match every session receipt')
    try:
        if report.get('verified_summary') != verified_summary(report,runs):
            fail('verified_summary',SUMMARY_RULE)
    except (ValueError,KeyError,TypeError,AttributeError):
        fail('verified_summary',SUMMARY_RULE)
    if report.get('limitations') != LIMITATIONS:
        fail('limitations','canonical limitations required verbatim')
    ids = report.get('ontology_ids')
    allowed_ids = grounding_ids(runs,ontology_receipts)
    if not isinstance(ids,list) or any(not isinstance(x,str) or x not in allowed_ids for x in ids):
        fail('ontology_ids','IDs must come from session lookups or bindings of changed parameters'); ids=[]
    for p in changed_ports(runs):
        if p['binding'] and not any(x['id'] in ids or x['iri'] in ids for x in p['binding']['ids']):
            fail('ontology_ids','missing anatomical context for '+p['name'])
    expected = [{'run_id':rid,**c} for rid,r in runs.items() for c in r['parameter_changes']]
    changes = report.get('parameter_changes')
    if not isinstance(changes,list):
        fail('parameter_changes','must list all intervention receipts')
    else:
        valid = True
        for i,c in enumerate(changes):
            if not isinstance(c,dict) or set(c) != {'run_id','parameter','baseline','intervention'}:
                fail(f'parameter_changes.{i}','invalid change schema'); valid=False; continue
            if not isinstance(c['run_id'],str) or not isinstance(c['parameter'],str) or any(
                    isinstance(c[k],bool) or not isinstance(c[k],(int,float)) or not math.isfinite(c[k]) for k in ('baseline','intervention')):
                fail(f'parameter_changes.{i}','strings and finite numbers required'); valid=False
        if valid and sorted(changes,key=lambda x:(x['run_id'],x['parameter'])) != sorted(expected,key=lambda x:(x['run_id'],x['parameter'])):
            fail('parameter_changes','must exactly match all changes actually run')
    evidence = report.get('evidence')
    if not isinstance(evidence,list) or not evidence:
        fail('evidence','at least one related session evidence receipt required')
    else:
        for i,item in enumerate(evidence):
            if not isinstance(item,dict) or item not in (evidence_receipts or []):
                fail(f'evidence.{i}','must match get_evidence receipts for changed parameters/entities')
    findings = report.get('findings')
    if not isinstance(findings,list) or not findings:
        fail('findings','nonempty findings required'); findings=[]
    seen=set(); covered=set()
    for i,f in enumerate(findings):
        path=f'findings.{i}'; prior=len(failures)
        claim_id=f.get('id',path) if isinstance(f,dict) else path
        if not isinstance(f,dict) or set(f) != FINDING_KEYS:
            fail(path,'invalid finding schema'); invalid.append(claim_id); continue
        if not isinstance(f['id'],str) or f['id'] != 'finding-'+str(i) or f['id'] in seen:
            fail(path+'.id','code-generated finding ID required')
        else:
            seen.add(f['id'])
        value,decimals=f['value'],f['decimals']
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
            fail(path+'.value','finite number required')
        run=runs.get(f['run_id']) if isinstance(f['run_id'],str) else None
        if run is None:
            fail(path+'.run_id','no matching session tool run')
        else:
            covered.add(f['run_id'])
            try:
                actual=metric_value(run,f['metric_path'])
                label,unit=metric_display(f['metric_path'])
                if f['label'] != label or f['unit'] != unit:
                    fail(path+'.label','label and unit must equal code-generated metric display')
                if decimals is None:
                    if value != actual:
                        fail(path+'.value','exact receipt value required without rounding')
                elif not sufficient_precision(actual,decimals):
                    fail(path+'.decimals','at least three significant figures required; nonzero cannot round to zero')
                elif value != round(actual,decimals):
                    fail(path+'.value','does not equal exact stated Python rounding')
                expected_direction=metric_direction(run,f['metric_path'].split('.')[-1]) if f['metric_path'].startswith('delta.') else None
                if f['direction'] != expected_direction:
                    fail(path+'.direction','must match code direction using scale and solver tolerance')
            except (ValueError,KeyError,TypeError,IndexError):
                fail(path+'.metric_path','must resolve to finite session metric')
        (verified if len(failures)==prior else invalid).append(claim_id)
    if set(runs)-covered:
        fail('findings','every successful session experiment must be represented')
    return {'passed':not failures,'failures':failures,'verified_claims':verified,'unverified_claims':invalid,
            'scope':'Receipt consistency only; biological validity and semantic mapping require researcher review.'}


def mark_unverified(report, verification, *, response_hash=None):
    """Never persist rejected model fields, including malformed JSON or free prose."""
    result = {'schema_version':'2.0','status':'unverified',
              'note':'Final structured report could not be verified.', 'limitations':list(LIMITATIONS)}
    if response_hash is not None:
        result['response_hash'] = response_hash
    return result
