"""Local JSON tools; runtime dependencies are stdlib, NumPy and SciPy only.

Numerical outputs and run identities are deterministic for fixed source/runtime;
observational timings are not. The bounded store is the sole intentional state.
"""
from collections import OrderedDict
from copy import deepcopy
from dataclasses import asdict
from functools import lru_cache
from hashlib import sha256
import json
import math
from pathlib import Path
import time
import sys
from threading import RLock

import numpy as np
from scipy.integrate import trapezoid
from physiosim.models import cardiovascular, four_chamber_m1
from physiosim.simulation import simulate
from physiosim.simulation.four_chamber_m1 import SolverSettings, simulate_m1
from .catalog import (MODELS, catalogue, default_parameters, apply_values, flatten,
                      knowledge, iri)

DEFAULT_CYCLES = 12
SAMPLES_PER_CYCLE = 400
MAX_CYCLES = 80
MAX_RUNS = 16
MAX_STORE_BYTES = 64 * 1024 * 1024
MAX_SERIES_POINTS = 601
PERIODICITY_THRESHOLD = 1e-3
_STORE = OrderedDict()
_STORE_LOCK = RLock()
FIXED_CAVEATS = [
    'SYNTHETIC research model; not clinically validated. No medical advice.',
    'Forward/backward flow summaries use sampled trapezoidal quadrature; ideal diode valves have no regurgitation.',
]


def _size_bytes(value):
    # Arrays own their buffers; getsizeof includes the float64 buffer plus header.
    size = sys.getsizeof(value)
    if isinstance(value,dict):
        size += sum(_size_bytes(k)+_size_bytes(v) for k,v in value.items())
    elif isinstance(value,(list,tuple)):
        size += sum(_size_bytes(v) for v in value)
    return size


def store_bytes():
    with _STORE_LOCK:
        return (sys.getsizeof(_STORE) + sum(_size_bytes(rid)+entry['stored_bytes']
                for rid,entry in _STORE.items())) if _STORE else 0


def _store_run(run_id, output, series):
    entry = {'result':deepcopy(output), 'series':series, 'stored_bytes':0}
    entry['stored_bytes'] = _size_bytes(entry)
    with _STORE_LOCK:
        _STORE[run_id] = entry
        _STORE.move_to_end(run_id)
        while _STORE and (len(_STORE) > MAX_RUNS or store_bytes() > MAX_STORE_BYTES):
            _STORE.popitem(last=False)



def _error(code, message):
    return {'error': {'code': code, 'message': str(message)}}


def _clean(value):
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [_clean(v) for v in value]
    if isinstance(value, (float, np.floating)):
        return float(value) if math.isfinite(value) else None
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def list_parameters(model):
    try:
        return {'model': model, 'parameters': catalogue(model),
                'limits': 'Conservative exploration range only; joint engine validation still applies. All inputs are synthetic.'}
    except (ValueError, TypeError):
        return _error('invalid_model', 'model must be phase1 or m1')


def _related(key):
    return [{'model': m, 'parameter': p['name']} for m in MODELS for p in catalogue(m)
            if p['binding'] and p['binding']['key'] == key]


def lookup_ontology(query):
    if not isinstance(query, str) or not query.strip():
        return _error('invalid_query', 'query must be a nonempty string')
    query = query.casefold().strip()
    source = knowledge()['source']
    templates = {x['record']['template_uri']: x['record'] for x in source['catalog']}
    relations = []
    for index, claim in enumerate(source['claims']):
        r = claim['record']
        a, b = templates[r['sourceTemplate']], templates[r['targetTemplate']]
        relations.append({'source': a['base_id'], 'target': b['base_id'],
                          'source_template': a['template_uri'], 'target_template': b['template_uri'],
                          'predicate': r['relation'],
                          'label': {'http://purl.obolibrary.org/obo/BFO_0000050': 'part_of',
                                    'http://purl.obolibrary.org/obo/RO_0001025': 'located_in'}.get(r['relation']),
                          'decision': r.get('decision'), 'formalization_decision': r.get('formalization_decision'),
                          'expert_review_status': r.get('expert_review_status'),
                          'scope': 'Source knowledge claim; not an adopted engine axiom or numerical binding.',
                          'evidence': {'path': 'src/physiosim/ontology/applied_la_mitral_lv_source_v1.json',
                                       'anchor': '/claims/'+str(index)}})
    matches = []
    seen = set()
    for index, n in enumerate(knowledge()['anatomy']['nodes']):
        related = _related(n['key'])
        search = ' '.join(str(n.get(k, '')) for k in ('key', 'structure', 'uberon', 'uberon_label', 'fma', 'fma_label'))
        search += ' '+' '.join(x['parameter'] for x in related)
        search += ' '+(iri(n['uberon']) or '')+' '+(iri(n['fma']) or '')
        if query not in search.casefold() and not all(w in search.casefold() for w in query.replace('_',' ').split()):
            continue
        primary = n['uberon'] if n['primary'] == 'UBERON' else n['fma']
        ids = [n['uberon'], n['fma']]
        seen.update(ids)
        matches.append({'id': primary, 'iri': iri(primary), 'label': n['structure'],
                        'key': n['key'], 'identifiers': ids, 'synonyms': n.get('synonyms', []),
                        'source_labels': {k: n.get(k+'_label') for k in ('uberon', 'fma')},
                        'related_parameters': related,
                        'relations': [r for r in relations if r['source'] in ids or r['target'] in ids],
                        'source': {'path': 'src/physiosim/ontology/anatomy_nodes_v2.json', 'anchor': '/nodes/'+str(index)},
                        'scope': 'V2 context only; FMA-primary vessel/lumen mappings retain Uberon as related structure.'})
    for r in templates.values():
        if r['base_id'] in seen:
            continue
        search = ' '.join(str(r.get(k,'')) for k in ('key','base_id','base_label','base_iri'))
        if query in search.casefold():
            matches.append({'id': r['base_id'], 'iri': r['base_iri'], 'label': r['base_label'],
                            'synonyms': [], 'related_parameters': [],
                            'relations': [x for x in relations if r['base_id'] in (x['source'], x['target'])],
                            'scope': 'Source anatomical knowledge template; no selected numerical binding.'})
            seen.add(r['base_id'])
    return {'query': query, 'entities': matches}


def get_evidence(entity_or_param):
    if not isinstance(entity_or_param, str):
        return _error('invalid_query', 'entity_or_param must be a string')
    query = entity_or_param.strip()
    keys = {query}
    parameter = False
    anatomy = False
    for model in MODELS:
        for p in catalogue(model):
            if query == p['name']:
                parameter = True
                keys.add(query.split('.')[0])
                if p['binding']:
                    keys.add(p['binding']['key']); anatomy = True
    for n in knowledge()['anatomy']['nodes']:
        if query in (n['key'], n['uberon'], n['fma'], iri(n['uberon']), iri(n['fma']), n['structure']):
            keys.add(n['key']); anatomy = True
    if parameter:
        keys.add('__parameter__')
    if anatomy:
        keys.add('__anatomy__')
    return [{k: deepcopy(v) for k, v in item.items() if k != 'keys'}
            for item in knowledge()['evidence'] if keys.intersection(item['keys'])]


@lru_cache(maxsize=1)
def engine_identity():
    from physiosim.simulation import _hybrid
    from physiosim.simulation import four_chamber_m1 as m1_sim
    import physiosim.simulation as p1_sim
    modules = (cardiovascular, four_chamber_m1, p1_sim, m1_sim, _hybrid)
    return {m.__name__: sha256(Path(m.__file__).read_bytes()).hexdigest() for m in modules}


def _periodicity(result, cycles):
    n = result.samples_per_cycle
    count = min(3, cycles - 1)
    if count < 1:
        return {'available': False, 'periodic': False, 'threshold': PERIODICITY_THRESHOLD,
                'comparisons': 0, 'max_relative_change': None,
                'definition': 'max compartment waveform difference / max(prior-beat max absolute compartment volume, 1 mL), across up to last three successive beat pairs'}
    changes = []
    for offset in range(count):
        end = len(result.time) - offset*n
        current = result.volumes[end-n-1:end]
        prior = result.volumes[end-2*n-1:end-n]
        scale = np.maximum(np.max(np.abs(prior), axis=0), 1.)
        changes.append(float(np.max(np.max(np.abs(current-prior), axis=0) / scale)))
    value = max(changes)
    return {'available': True, 'periodic': value < PERIODICITY_THRESHOLD,
            'threshold': PERIODICITY_THRESHOLD, 'comparisons': count, 'max_relative_change': value,
            'definition': 'max compartment waveform difference / max(prior-beat max absolute compartment volume, 1 mL), across up to last three successive beat pairs'}


def _metrics(result, model):
    metrics = result.metrics()  # preserve exact engine metric definitions and numbers
    beat = result.final_beat
    t = result.time[beat]; duration = float(t[-1]-t[0])
    for i, c in enumerate(result.compartment_names):
        for kind, values, unit in (('pressure', result.pressures[beat,i], 'mmhg'), ('volume', result.volumes[beat,i], 'ml')):
            for stat, value in (('min', values.min()), ('max', values.max()), ('mean', trapezoid(values,t)/duration)):
                metrics.setdefault(f'{c}_{kind}_{stat}_{unit}', float(value))
    edges = result.flow_names if model == 'phase1' else result.edge_names
    for i, edge in enumerate(edges):
        q = result.flows[beat,i]
        metrics[f'{edge}_forward_volume_ml'] = float(trapezoid(np.maximum(q,0),t))
        metrics[f'{edge}_backward_volume_ml'] = float(trapezoid(np.maximum(-q,0),t))
        metrics[f'{edge}_mean_flow_ml_s'] = float(trapezoid(q,t)/duration)
    if model == 'm1':
        metrics['stroke_volume_ml'] = metrics['lv_stroke_volume_ml']
        metrics['cardiac_output_l_min'] = metrics['lv_cardiac_output_l_min']
        metrics['lv_ejection_fraction'] = metrics['lv_ejection_fraction_sample']
    if not np.isfinite(result.volumes).all() or not np.isfinite(result.pressures).all() or not np.isfinite(result.flows).all():
        raise RuntimeError('engine returned nonfinite trajectory')
    if np.any(result.volumes <= 0):
        raise RuntimeError('engine returned nonpositive compartment volume')
    return _clean(metrics)


def _series(result, model):
    # Copy only the last three complete beats: no view can retain a full solve.
    start = max(0,len(result.time)-3*result.samples_per_cycle-1)
    data = {'time_s':np.array(result.time[start:],dtype=np.float64,copy=True)}
    for i,c in enumerate(result.compartment_names):
        data['pressure.'+c] = np.array(result.pressures[start:,i],dtype=np.float64,copy=True)
        data['volume.'+c] = np.array(result.volumes[start:,i],dtype=np.float64,copy=True)
    edges = result.flow_names if model == 'phase1' else result.edge_names
    for i,e in enumerate(edges):
        data['flow.'+e] = np.array(result.flows[start:,i],dtype=np.float64,copy=True)
    length = len(data['time_s'])
    indices = np.unique(np.linspace(0,length-1,min(MAX_SERIES_POINTS,length),dtype=int))
    stats = {n:{'min':float(v.min()),'max':float(v.max()),'mean':float(np.mean(v))} for n,v in data.items()}
    digest = sha256()
    for n,v in data.items():
        digest.update(n.encode()); digest.update(v.tobytes())
    return {'full':data, 'view':{n:v[indices].copy() for n,v in data.items()},
            'statistics':stats, 'sha256':digest.hexdigest()}


def run_experiment(model, intervention, baseline_overrides=None, cycles=None):
    started = time.perf_counter()
    try:
        p = default_parameters(model)
        if cycles is None:
            cycles = DEFAULT_CYCLES
        if isinstance(cycles, bool) or not isinstance(cycles, int) or not 1 <= cycles <= MAX_CYCLES:
            raise ValueError(f'cycles must be an integer in [1, {MAX_CYCLES}]')
        baseline_overrides = {} if baseline_overrides is None else baseline_overrides
        p, _ = apply_values(p, model, baseline_overrides, allow_scale=False)
        changed, changes = apply_values(p, model, intervention, allow_scale=True)
        # The explicit maximum step is identical even for HR interventions.
        divisor = 100 if model == 'phase1' else 200
        settings = {'method': 'DOP853', 'rtol': 1e-7 if model == 'phase1' else 1e-9,
                    'atol': 1e-8 if model == 'phase1' else 1e-10,
                    'max_step': min(p.period, changed.period)/divisor,
                    'cycles': cycles, 'samples_per_cycle': SAMPLES_PER_CYCLE, 'analysed_beats': 1,
                    'max_step_rule': 'min(baseline period, intervention period)/'+str(divisor)}
        config = {'model': model, 'baseline_parameters': flatten(p,model),
                  'intervention_parameters': flatten(changed,model), 'settings': settings,
                  'engine_source_sha256': engine_identity()}
        run_id = 'run-'+sha256(json.dumps(config,sort_keys=True,allow_nan=False).encode()).hexdigest()[:24]
        results = {}; series = {}; timings = {}
        for condition, parameters in (('baseline',p),('intervention',changed)):
            tick = time.perf_counter()
            if model == 'phase1':
                result = simulate(parameters, cycles=cycles, samples_per_cycle=SAMPLES_PER_CYCLE,
                                  rtol=settings['rtol'], atol=settings['atol'], method=settings['method'],
                                  max_step=settings['max_step'])
            else:
                result = simulate_m1(parameters, cycles=cycles, samples_per_cycle=SAMPLES_PER_CYCLE,
                                     settings=SolverSettings(**{k:settings[k] for k in ('method','rtol','atol','max_step')}))
            metrics = _metrics(result,model)
            periodicity = _periodicity(result,cycles)
            results[condition] = {'parameters': flatten(parameters,model), 'metrics': metrics,
                                  'periodicity': periodicity,
                                  'duration_s': float(result.time[-1]),
                                  'analysis_window_s': [float(result.time[result.final_beat][0]),float(result.time[-1])]}
            series[condition] = _series(result,model)
            timings[condition+'_s'] = time.perf_counter()-tick
        absolute = {}; relative = {}
        for key, before in results['baseline']['metrics'].items():
            after = results['intervention']['metrics'][key]
            absolute[key] = None if before is None or after is None else after-before
            relative[key] = None if before in (None,0) or after is None else (after-before)/abs(before)
        warnings = []
        if cycles < (40 if model == 'phase1' else 30):
            warnings.append('Shorter than the documented demo duration; transient effects may remain.')
        for condition in results:
            if not results[condition]['periodicity']['periodic']:
                warnings.append(condition+': final beats do not meet the stated periodicity threshold (or comparison unavailable).')
        output = _clean({'run_id':run_id, 'model':model, 'settings':settings,
                         **results, 'parameter_changes':changes, 'baseline_overrides':baseline_overrides,
                         'requested_intervention':intervention, 'delta':{'abs':absolute,'rel':relative},
                         'engine_source_sha256':engine_identity(), 'warnings':warnings, 'caveats':list(FIXED_CAVEATS),
                         'timings':{**timings,'total_s':time.perf_counter()-started}})
        _store_run(run_id,output,series)
        return output
    except (ValueError, TypeError, KeyError, OverflowError) as exc:
        return _error('invalid_request', exc)
    except Exception as exc:
        return _error('engine_failure', type(exc).__name__+': '+str(exc))


def _selected_series(run_id, names):
    if not isinstance(run_id,str) or run_id not in _STORE:
        return None, _error('unknown_run','run unavailable or evicted from bounded memory')
    _STORE.move_to_end(run_id)
    stored = _STORE[run_id]['series']
    if names is None:
        names = list(stored['baseline']['full'])
    if not isinstance(names,list) or any(not isinstance(n,str) or n not in stored['baseline']['full'] for n in names):
        return None, _error('invalid_names','names must be available pressure, volume, flow or time series')
    return stored,list(dict.fromkeys(['time_s']+names))


def get_timeseries(run_id, names=None, *, full=False):
    """JSON UI view; full means the stored final three beats, never all cycles."""
    with _STORE_LOCK:
        stored,names = _selected_series(run_id,names)
        if stored is None:
            return names
        key = 'full' if full else 'view'
        length = len(stored['baseline'][key]['time_s'])
        return {'run_id':run_id,'downsampled':not full,'max_points':length if full else MAX_SERIES_POINTS,
                **{c:{n:stored[c][key][n].tolist() for n in names} for c in ('baseline','intervention')},
                'note':'Final three beats only; uniformly sampled UI view; metrics use the final complete beat.'}


def compact_timeseries(run_id, names=None):
    with _STORE_LOCK:
        stored,names = _selected_series(run_id,names)
        if stored is None:
            return names
        source_hash = sha256(''.join(stored[c]['sha256'] for c in ('baseline','intervention')).encode()).hexdigest()
        result = {'run_id':run_id,'max_points':60,'source_sha256':source_hash,
                  'note':'Cached statistics of the stored final three beats; up to 60 uniformly selected LLM points.'}
        for c in ('baseline','intervention'):
            result[c] = {}
            for n in names:
                values = stored[c]['full'][n]
                indices = np.unique(np.linspace(0,len(values)-1,min(60,len(values)),dtype=int))
                result[c][n] = {**stored[c]['statistics'][n],'points':values[indices].tolist()}
        return result


def get_run(run_id):
    """Trusted local receipt for consumers; agent verification uses session receipts."""
    with _STORE_LOCK:
        if not isinstance(run_id,str) or run_id not in _STORE:
            return _error('unknown_run','run unavailable or evicted')
        _STORE.move_to_end(run_id)
        return deepcopy(_STORE[run_id]['result'])


TOOL_FUNCTIONS = {f.__name__:f for f in (list_parameters,lookup_ontology,run_experiment,get_evidence,get_timeseries)}


def dispatch(name, arguments):
    if name not in TOOL_FUNCTIONS:
        return _error('unknown_tool','unknown tool')
    if not isinstance(arguments,dict):
        return _error('invalid_arguments','tool arguments must be an object')
    try:
        return TOOL_FUNCTIONS[name](**arguments)
    except Exception as exc:
        return _error('invalid_arguments',type(exc).__name__+': '+str(exc))
