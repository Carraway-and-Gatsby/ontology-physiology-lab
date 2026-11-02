"""All verified display text is a pure function of trusted engine receipts."""
from copy import deepcopy
import math
import re
from .catalog import catalogue
from . import LIMITATIONS

COMPARTMENTS = {'la':'left atrial','ra':'right atrial','lv':'left ventricular','rv':'right ventricular',
                'sa':'systemic arterial','sv':'systemic venous','pa':'pulmonary arterial','pv':'pulmonary venous'}
UNITS = {'mmhg':'mmHg','ml':'mL','l_min':'L/min','ml_s':'mL/s','m3_s':'m³/s','bpm':'beat/min','s':'s'}
FINDING_KEYS = {'id','label','unit','run_id','metric_path','value','decimals','direction'}
METRICS = {
    'systemic_mean_pressure_mmhg': ('Mean systemic arterial pressure','mmHg'),
    'pulmonary_mean_pressure_mmhg': ('Mean pulmonary arterial pressure','mmHg'),
    'stroke_volume_ml': ('Left ventricular stroke volume','mL'),
    'cardiac_output_l_min': ('Left ventricular cardiac output','L/min'),
    'cardiac_output_m3_s': ('Left ventricular cardiac output','m³/s'),
}


def metric_display(path):
    key = path.split('.')[-1]
    if key in METRICS:
        label,unit = METRICS[key]
    else:
        match = re.fullmatch(r'(la|ra|lv|rv|sa|sv|pa|pv)_(pressure|volume)_(min|max|mean)_(mmhg|ml)',key)
        if match:
            c,quantity,stat,suffix = match.groups()
            label = {'min':'Minimum','max':'Maximum','mean':'Mean'}[stat]+' '+COMPARTMENTS[c]+' '+quantity
            unit = UNITS[suffix]
        else:
            unit = next((u for suffix,u in UNITS.items() if key.endswith('_'+suffix)), 'dimensionless')
            stem = key
            for suffix in sorted(UNITS,key=len,reverse=True):
                if stem.endswith('_'+suffix):
                    stem = stem[:-len(suffix)-1]; break
            words = stem.split('_')
            if words[0] in COMPARTMENTS:
                words[0] = COMPARTMENTS[words[0]]
            label = ' '.join(words).capitalize()
    return label, 'fraction' if path.startswith('delta.rel.') else unit


def metric_value(run, path):
    if not isinstance(path,str):
        raise ValueError('metric path required')
    parts = path.split('.')
    if len(parts) != 3 or not ((parts[0] in ('baseline','intervention') and parts[1] == 'metrics')
                              or (parts[0] == 'delta' and parts[1] in ('abs','rel'))):
        raise ValueError('invalid metric namespace')
    value = run[parts[0]][parts[1]][parts[2]]
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        raise ValueError('finite metric required')
    return value


def direction_tolerance(run, metric):
    scale = max(abs(run[c]['metrics'][metric]) for c in ('baseline','intervention'))
    settings = run['settings']
    return 10 * (settings['atol'] + settings['rtol'] * scale)


def direction_of(value, tolerance=1e-12):
    return 'increase' if value > tolerance else 'decrease' if value < -tolerance else 'unchanged'


def metric_direction(run, metric):
    return direction_of(run['delta']['abs'][metric], direction_tolerance(run,metric))


def sufficient_precision(value, decimals):
    return (isinstance(decimals,int) and not isinstance(decimals,bool) and 0 <= decimals <= 15
            and (value == 0 or (decimals >= max(0,2-math.floor(math.log10(abs(value))))
                                and round(value,decimals) != 0)))


def run_details(runs):
    return [{'run_id':rid,'baseline_overrides':deepcopy(run['baseline_overrides']),
             'diagnostics':{'cycles':run['settings']['cycles'],
                 'baseline':deepcopy(run['baseline']['periodicity']),
                 'intervention':deepcopy(run['intervention']['periodicity']),
                 'warnings':deepcopy(run['warnings'])}} for rid,run in runs.items()]


def completion_status(runs):
    if not runs:
        return 'unverified'
    return 'completed_with_warnings' if any(r['warnings'] or any(not r[c]['periodicity']['periodic']
        for c in ('baseline','intervention')) for r in runs.values()) else 'completed'


def fmt(value, signed=False):
    # At least three significant figures; small nonzero values never disappear.
    spec = '+.3f' if signed else '.3f'
    if value != 0 and (abs(value) < .1 or abs(value) >= 1e6):
        spec = '+#.6g' if signed else '#.6g'
    return format(value,spec)


def verified_summary(report, runs):
    if not runs:
        return None
    lines = ['Status: '+report.get('status',completion_status(runs))+'. Synthetic model outputs only.']
    for rid,run in runs.items():
        ports = {p['name']:p for p in catalogue(run['model'])}
        lines.append('Run '+rid+' ('+run['model']+').')
        if not run['baseline_overrides']:
            lines.append('Baseline overrides: none (catalogue defaults).')
        for name,value in run['baseline_overrides'].items():
            p = ports[name]
            lines.append(f"Baseline override {name}: {fmt(p['default'])} → {fmt(value)} {p['unit']}.")
        for change in run['parameter_changes']:
            name = change['parameter']
            lines.append(f"Parameter {name}: {fmt(change['baseline'])} → {fmt(change['intervention'])} {ports[name]['unit']}.")
        metrics = dict.fromkeys(f['metric_path'].split('.')[-1] for f in report.get('findings',[])
                                if isinstance(f,dict) and f.get('run_id') == rid and isinstance(f.get('metric_path'),str))
        for metric in metrics:
            try:
                before = metric_value(run,'baseline.metrics.'+metric)
                after = metric_value(run,'intervention.metrics.'+metric)
                delta = metric_value(run,'delta.abs.'+metric)
            except (KeyError,ValueError):
                continue
            label,unit = metric_display('baseline.metrics.'+metric)
            rel = run['delta']['rel'][metric]
            percent = 'relative change undefined' if rel is None else fmt(rel*100,True)+'%'
            direction = metric_direction(run,metric)
            direction = 'no meaningful change' if direction == 'unchanged' else direction
            lines.append(f'{label} ({metric}): {fmt(before)} → {fmt(after)} {unit} ({fmt(delta,True)}, {percent}); {direction}.')
        lines.append('Diagnostics: cycles='+str(run['settings']['cycles'])+'.')
        for c in ('baseline','intervention'):
            p = run[c]['periodicity']
            change = 'unavailable' if p['max_relative_change'] is None else fmt(p['max_relative_change'])
            lines.append(f"{c}: periodic={str(p['periodic']).lower()}, max relative beat-to-beat change={change}.")
        lines.extend('Warning: '+w for w in run['warnings'])
    return '\n'.join(lines)


def prepare_report(report, runs):
    """Drop model display claims; derive code-owned fields before verification.

    Numeric fabrication with adequate precision is left for the verifier to reject.
    Low-precision model values are filled with the exact receipt value instead.
    """
    if not isinstance(report,dict):
        return report
    # Parse only structured fields. Free prose and unknown fields are discarded.
    keys = {'schema_version','status','hypothesis','model','parameter_changes',
            'ontology_ids','evidence','findings','limitations'}
    result = {k:deepcopy(v) for k,v in report.items() if k in keys}
    result['limitations'] = list(LIMITATIONS)
    result['schema_version'] = '2.0'
    result['status'] = completion_status(runs)
    result['runs'] = run_details(runs)
    for i,f in enumerate(result.get('findings',[]) if isinstance(result.get('findings'),list) else []):
        if not isinstance(f,dict):
            continue
        f = {key:deepcopy(f[key]) for key in FINDING_KEYS & {'run_id','metric_path','value','decimals'} if key in f}
        result['findings'][i] = f
        f['id'] = 'finding-'+str(i)
        try:
            run = runs[f['run_id']]; actual = metric_value(run,f['metric_path'])
            f['label'],f['unit'] = metric_display(f['metric_path'])
            f['direction'] = metric_direction(run,f['metric_path'].split('.')[-1]) if f['metric_path'].startswith('delta.') else None
            if not sufficient_precision(actual,f.get('decimals')):
                f['value'] = actual; f['decimals'] = None
        except (KeyError,ValueError,TypeError):
            pass
    if runs:
        result['verified_summary'] = verified_summary(result,runs)
    return result
