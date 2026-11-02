"""Deterministic EN/KO hypothesis metric selection for step-limit recovery."""
import re
from .catalog import COMPARTMENTS, catalogue
from .narrative import metric_display, metric_value

# Canonical aliases avoid picking duplicate engine aliases for common phrases.
METRIC_ALIASES = {
    'stroke_volume_ml': ('stroke volume', '1회 박출량', '일회박출량', '일회 박출량'),
    'cardiac_output_l_min': ('cardiac output', '심박출량', '심장박출량', '심장 박출량'),
}
CHAMBER_ALIASES = {
    'la': ('left atrial', '좌심방'), 'ra': ('right atrial', '우심방'),
    'lv': ('left ventricular', '좌심실'), 'rv': ('right ventricular', '우심실'),
    'sa': ('systemic arterial', '전신 동맥', '체동맥'),
    'sv': ('systemic venous', '전신 정맥', '체정맥'),
    'pa': ('pulmonary arterial', '폐동맥'), 'pv': ('pulmonary venous', '폐정맥'),
}
for chamber, names in CHAMBER_ALIASES.items():
    METRIC_ALIASES[chamber+'_pressure_mean_mmhg'] = (
        chamber+' pressure', *(name+' pressure' for name in names if name.isascii()),
        *(name+suffix for name in names if not name.isascii() for suffix in ('압',' 압력',' 압')))
METRIC_ALIASES['systemic_mean_pressure_mmhg'] = ('mean systemic pressure', '평균 동맥압')
METRIC_ALIASES['pulmonary_mean_pressure_mmhg'] = ('mean pulmonary pressure', '평균 폐동맥압')


def _matches(text, term):
    # Korean particles can immediately follow a metric name; English needs boundaries.
    return (term in text if not term.isascii() else
            re.search(r'(?<!\w)'+re.escape(term)+r'(?!\w)',text) is not None)


def default_metrics(run):
    """CO, SV, and mean pressures at affected model compartments/edge endpoints.

    Global rate/activation ports use every compartment. Valve ports use the actual
    phase1 ring or M1 atrial topology. Local chamber/reservoir ports use that chamber.
    """
    model = run['model']; compartments = COMPARTMENTS[model]
    if model == 'phase1':
        from physiosim.models.cardiovascular import FLOW_NAMES
        edges = dict(zip(FLOW_NAMES,zip(compartments,(*compartments[1:],compartments[0]))))
    else:
        from physiosim.models.four_chamber_m1 import EDGES
        edges = {e.name:(e.source,e.target) for e in EDGES}
    affected = set()
    ports = {p['name']:p for p in catalogue(model)}
    for name in dict.fromkeys([c['parameter'] for c in run['parameter_changes']]+list(run['baseline_overrides'])):
        binding = ports[name]['binding']
        key = binding['key'] if binding else ''
        if name.startswith('resistance_'):
            affected.update(edges.get(name[len('resistance_'):],()))
        elif name in ('heart_rate','systolic_fraction') or key == 'heart':
            affected.update(compartments)
        else:
            c = name.split('.')[-1] if '.' in name else name.rsplit('_',1)[-1]
            if c in compartments:
                affected.add(c)
    return ['cardiac_output_l_min','stroke_volume_ml',
            *(c+'_pressure_mean_mmhg' for c in compartments if c in affected)]


def _select_metrics(hypothesis, run):
    text = hypothesis.casefold(); metrics = []
    changed = {c['parameter'] for c in run['parameter_changes']} | set(run['baseline_overrides'])
    # Direct parameter outputs (currently heart_rate_bpm) only echo an input.
    echoes = {name+suffix for name in changed for suffix in ('','_bpm','_s','_ml','_mmhg')}
    for metric in run['baseline']['metrics']:
        if metric in echoes:
            continue
        label,_ = metric_display('baseline.metrics.'+metric)
        # Generic labels that duplicate canonical CO/SV should select the canonical metric.
        terms = [metric,*METRIC_ALIASES.get(metric,())]
        if metric not in ('lv_stroke_volume_ml','lv_cardiac_output_l_min','cardiac_output_m3_s'):
            terms.append(label.casefold())
        if any(_matches(text,term) for term in terms):
            metrics.append(metric)
    def valid_metrics(chosen):
        valid = []
        for metric in chosen:
            if metric in echoes:
                continue
            try:
                for prefix in ('baseline.metrics.','intervention.metrics.','delta.abs.'):
                    metric_value(run,prefix+metric)
            except (KeyError,ValueError,TypeError):
                continue
            valid.append(metric)
        return list(dict.fromkeys(valid))
    matched = valid_metrics(metrics)
    return (matched,'code_hypothesis_terms') if matched else (valid_metrics(default_metrics(run)),'code_default_set')


def select_metrics(hypothesis, run):
    return _select_metrics(hypothesis,run)[0]


def selection_basis(hypothesis, runs):
    # Individual runs without usable matches still receive their default set.
    return ('code_hypothesis_terms' if any(_select_metrics(hypothesis,r)[1] == 'code_hypothesis_terms'
                                         for r in runs.values()) else 'code_default_set')


def select_findings(hypothesis, runs):
    return [{'run_id':rid,'metric_path':prefix+metric}
            for rid,run in runs.items() for metric in select_metrics(hypothesis,run)
            for prefix in ('baseline.metrics.','intervention.metrics.','delta.abs.')]
