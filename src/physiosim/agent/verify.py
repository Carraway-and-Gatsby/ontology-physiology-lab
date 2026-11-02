"""Closed-schema numeric claim checking against trusted session tool receipts.

Does not establish biological truth or that an LLM mapped a hypothesis correctly.
"""
from copy import deepcopy
import math
import re
from . import LIMITATIONS
from .catalog import known_ids, catalogue
from .tools import get_evidence
from .guard import check_scope

REPORT_KEYS = {'schema_version','status','hypothesis','model','summary','parameter_changes',
               'ontology_ids','evidence','findings','limitations'}
FINDING_KEYS = {'id','label','run_id','metric_path','value','decimals','direction'}
PROSE_QUANTITY = re.compile(
    r'\d|%|\b(?:increase\w*|decrease\w*|higher|lower|ris(?:e|es|ing)|rose|fall(?:s|ing)?|fell|'
    r'unchanged|larger|smaller|greater|less|reduc\w*|gain\w*|drop\w*|doubl\w*|tripl\w*|'
    r'percent(?:age)?|half|twice|thrice|'
    r'zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|'
    r'fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|'
    r'eighty|ninety|hundred|thousand|million|billion)\b|[증감]가|감소|(?:두|세|네)\s*배', re.I)
SUMMARY_QUANTITY = re.compile(PROSE_QUANTITY.pattern+r'|\b(?:mmhg|ml|bpm|lit(?:er|re)s?)\b',re.I)
SUMMARY_RULE = (
    'nonempty qualitative prose only; put quantitative values, percentages, units, '
    'multipliers and metric directions in findings. Model names (Phase 1, M1, '
    'four-chamber), catalogue parameter names, ontology IDs listed in the report, '
    'session run_ids and section/ordinal references are allowed. '
    'Triple/tripled is allowed only for a named parameter whose parameter_changes '
    'exactly match a tripling in the session receipts.')
SUMMARY_EXAMPLE = (
    'One paired synthetic M1 run compared the default mitral flow-path resistance '
    'with a modified setting and reported mean left atrial pressure and left '
    'ventricular stroke volume. All quantitative results and their directions are '
    'in the findings. The periodicity check was satisfied, but that does not '
    'establish physiological validity.')


def _identifier_pattern(names):
    return r'(?<!\w)(?:' + '|'.join(re.escape(x) for x in sorted(names,key=len,reverse=True)) + r')(?!\w)'


def _summary_has_quantity(summary, report, runs):
    """Mask only recognised identifiers and receipt-backed parameter restatements.

    This lexical check deliberately keeps metric directions in structured findings;
    it does not attempt to verify arbitrary natural-language metric claims.
    """
    text = summary
    changes = report.get('parameter_changes')
    changes = changes if isinstance(changes,list) else []
    by_parameter = {}
    for run_id,run in runs.items():
        for change in run['parameter_changes']:
            by_parameter.setdefault(change['parameter'],[]).append({'run_id':run_id,**change})
    for parameter,receipts in by_parameter.items():
        if not all(c in changes and math.isclose(c['intervention'],3*c['baseline'],rel_tol=1e-12,abs_tol=0.)
                   for c in receipts):
            continue
        aliases = {parameter,parameter.replace('_',' ')}
        if parameter.startswith('resistance_'):
            path = parameter[len('resistance_'):].replace('_',' ')
            aliases.update((path+' resistance',path+' valve resistance',path+' flow-path resistance'))
        name = _identifier_pattern(aliases)
        # Require a direct grammatical link; a metric elsewhere cannot inherit it.
        text = re.sub(name+r'\s+(?:(?:was|is|has been)\s+)?tripled\b', 'parameter change',text,flags=re.I)
        text = re.sub(r'\b(?:triple|tripled)\s+(?:the\s+)?'+name, 'parameter change',text,flags=re.I)
    names = {p['name'] for model in ('phase1','m1') for p in catalogue(model)}
    names.update(runs)
    ids = report.get('ontology_ids')
    if isinstance(ids,list):
        names.update(x for x in ids if isinstance(x,str) and x in known_ids())
    text = re.sub(_identifier_pattern(names),'identifier',text,flags=re.I)
    text = re.sub(r'\b(?:phase\s*1|m1|four[- ]chamber)\b','model',text,flags=re.I)
    text = re.sub(r'\b(?:section|step|part|figure|table|appendix)\s+(?:\d+|[ivx]+|one|two|three|four)\b',
                  'section',text,flags=re.I)
    text = re.sub(r'\b\d+(?:st|nd|rd|th)\b','ordinal',text,flags=re.I)
    # A structural introduction counts experiments, rather than reporting metrics.
    text = re.sub(r'\bone\s+(?:paired\s+)?(?:synthetic\s+)?(?:model\s+)?run\b',
                  'the run',text,flags=re.I)
    return bool(SUMMARY_QUANTITY.search(text))


def metric_value(run, path):
    """Only exposed metric namespaces are valid numeric evidence, never timings."""
    if not isinstance(path,str):
        raise ValueError('metric_path must be a string')
    parts = path.split('.')
    if len(parts) != 3 or not ((parts[0] in ('baseline','intervention') and parts[1] == 'metrics')
                               or (parts[0] == 'delta' and parts[1] in ('abs','rel'))):
        raise ValueError('metric_path must be baseline.metrics.KEY, intervention.metrics.KEY, delta.abs.KEY or delta.rel.KEY')
    value = run[parts[0]][parts[1]][parts[2]]
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        raise ValueError('metric is null or not finite numeric evidence')
    return value


def direction_of(value):
    return 'increase' if value > 0 else 'decrease' if value < 0 else 'unchanged'


def verify_report(report, runs, *, hypothesis=None, evidence_receipts=None):
    """Fail closed on malformed data; never execute or trust a model-supplied run.

    `runs` maps IDs to exact successful outputs retained by the current session.
    Unknown fields and quantitative prose are forbidden by the report contract.
    """
    failures = []; verified = []; invalid = []
    def fail(path, reason):
        failures.append({'path':path,'reason':reason})
    if not isinstance(report,dict):
        return {'passed':False,'failures':[{'path':'report','reason':'report must be a JSON object'}],
                'verified_claims':[], 'unverified_claims':[]}
    for key in sorted(REPORT_KEYS - set(report)):
        fail(key,'required field missing')
    for key in sorted(set(report) - REPORT_KEYS):
        fail(key,'unknown field: untracked claims are forbidden')
    if report.get('schema_version') != '1.0':
        fail('schema_version','must be 1.0')
    if report.get('status') != 'completed':
        fail('status','completed report required for claim verification')
    if not isinstance(report.get('hypothesis'),str) or (hypothesis is not None and report['hypothesis'] != hypothesis):
        fail('hypothesis','must echo the original hypothesis exactly')
    if not runs:
        fail('findings','at least one successful engine tool run is required')
    if report.get('model') not in ('phase1','m1') or any(r['model'] != report.get('model') for r in runs.values()):
        fail('model','must match every cited session run; use one model per report')
    summary = report.get('summary')
    if not isinstance(summary,str) or not summary.strip() or _summary_has_quantity(summary,report,runs):
        fail('summary',SUMMARY_RULE)
    elif not check_scope(summary)['allowed']:
        fail('summary','clinical or personal guidance is forbidden in output')
    if report.get('limitations') != LIMITATIONS:
        fail('limitations','must include the canonical synthetic-model limitations verbatim')
    ids = report.get('ontology_ids')
    if not isinstance(ids,list) or any(not isinstance(x,str) or x not in known_ids() for x in ids):
        fail('ontology_ids','every ontology ID must exist in the bundled repository data')
        ids = []
    expected = []
    for run_id, run in runs.items():
        expected.extend({'run_id':run_id,**change} for change in run['parameter_changes'])
        for change in run['parameter_changes']:
            p = next(p for p in catalogue(run['model']) if p['name'] == change['parameter'])
            if p['binding'] and not any(x['id'] in ids or x['iri'] in ids for x in p['binding']['ids']):
                fail('ontology_ids','missing existing anatomical context for '+change['parameter'])
    changes = report.get('parameter_changes')
    if not isinstance(changes,list):
        fail('parameter_changes','must be a list of all intervention receipts')
    else:
        valid_changes = True
        for i, change in enumerate(changes):
            if not isinstance(change,dict) or set(change) != {'run_id','parameter','baseline','intervention'}:
                fail(f'parameter_changes.{i}','invalid change schema'); valid_changes=False; continue
            if not isinstance(change['run_id'],str) or not isinstance(change['parameter'],str):
                fail(f'parameter_changes.{i}','run_id and parameter must be strings'); valid_changes=False
            if any(isinstance(change[k],bool) or not isinstance(change[k],(int,float)) or not math.isfinite(change[k]) for k in ('baseline','intervention')):
                fail(f'parameter_changes.{i}','change values must be finite numbers'); valid_changes=False
        if valid_changes and sorted(changes,key=lambda x:(x['run_id'],x['parameter'])) != sorted(expected,key=lambda x:(x['run_id'],x['parameter'])):
            fail('parameter_changes','must exactly match all changes actually run, without omissions or additions')
    evidence = report.get('evidence')
    if not isinstance(evidence,list) or not evidence:
        fail('evidence','at least one repository evidence item required')
    else:
        allowed = evidence_receipts
        if allowed is None:
            allowed = [item for r in runs.values() for p in r['parameter_changes'] for item in get_evidence(p['parameter'])]
        for i,item in enumerate(evidence):
            if not isinstance(item,dict) or item not in allowed:
                fail(f'evidence.{i}','must exactly match an actual repository evidence tool receipt')
    findings = report.get('findings')
    if not isinstance(findings,list) or not findings:
        fail('findings','nonempty numeric findings list required'); findings=[]
    seen = set(); covered = set()
    for i, f in enumerate(findings):
        path = f'findings.{i}'; prior = len(failures)
        claim_id = f.get('id',path) if isinstance(f,dict) else path
        if not isinstance(f,dict) or set(f) != FINDING_KEYS:
            fail(path,'invalid finding schema'); invalid.append(claim_id); continue
        if not isinstance(f['id'],str) or not f['id'] or f['id'] in seen:
            fail(path+'.id','claim IDs must be unique nonempty strings')
        else:
            seen.add(f['id'])
        if not isinstance(f['label'],str) or not f['label'].strip() or PROSE_QUANTITY.search(f['label']):
            fail(path+'.label','qualitative label only; quantitative prose must be structured')
        elif not check_scope(f['label'])['allowed']:
            fail(path+'.label','clinical or personal guidance is forbidden in output')
        value, decimals = f['value'], f['decimals']
        if isinstance(decimals,bool) or not isinstance(decimals,int) or not 0 <= decimals <= 12:
            fail(path+'.decimals','integer rounding precision in [0,12] required')
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
            fail(path+'.value','finite numeric value required')
        run = runs.get(f['run_id']) if isinstance(f['run_id'],str) else None
        if run is None:
            fail(path+'.run_id','no matching tool run in this session')
        else:
            covered.add(f['run_id'])
            try:
                actual = metric_value(run,f['metric_path'])
                if isinstance(decimals,int) and not isinstance(decimals,bool) and 0 <= decimals <= 12 and value != round(actual,decimals):
                    fail(path+'.value','does not equal tool metric after stated Python round(value, decimals)')
                direction = f['direction']
                if direction not in ('increase','decrease','unchanged',None):
                    fail(path+'.direction','must be increase, decrease, unchanged or null')
                elif direction is not None:
                    metric = f['metric_path'].split('.')[-1]
                    if direction != direction_of(run['delta']['abs'][metric]):
                        fail(path+'.direction','direction disagrees with unrounded tool delta')
            except (ValueError, KeyError, TypeError, IndexError):
                fail(path+'.metric_path','metric evidence path does not resolve to a finite session tool metric')
        (verified if len(failures) == prior else invalid).append(claim_id)
    if set(runs) - covered:
        fail('findings','every successful session experiment must be represented')
    return {'passed':not failures, 'failures':failures, 'verified_claims':verified,
            'unverified_claims':invalid,
            'scope':'Checks tool consistency and source membership, not biological validity or hypothesis-to-parameter semantic correctness.'}


def mark_unverified(report, verification):
    result = deepcopy(report) if isinstance(report,dict) else {'raw_response':report}
    result['status'] = 'unverified'
    # Structural failures taint the report as a whole, even when a numeric field matched.
    findings = result.get('findings',[])
    for finding in findings if isinstance(findings,list) else []:
        if isinstance(finding,dict):
            finding['verification_status'] = 'UNVERIFIED' if finding.get('id') in verification['unverified_claims'] else 'VERIFIED_VALUE_ONLY'
    return result
