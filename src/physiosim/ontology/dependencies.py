"""Descriptive law graph of the existing engines; no solver or new equations.

Separate law nodes distinguish constitutive, definition, initialization and
signed conservation relations. Dependencies never assert value equivalence or
ontology-derived causation. All names resolve to canonical quantity contracts.
"""
import numpy as np
from . import PROPERTIES


def engine_topology(model_id):
    if model_id == 'phase1':
        from physiosim.models.cardiovascular import COMPARTMENTS, FLOW_NAMES, VALVE_INDICES
        edges = [dict(name=e, source=COMPARTMENTS[i], target=COMPARTMENTS[(i+1)%len(COMPARTMENTS)],
                      kind='diode' if i in VALVE_INDICES else 'resistor') for i,e in enumerate(FLOW_NAMES)]
        incidence = np.roll(np.eye(len(edges),dtype=int),1,axis=0)-np.eye(len(edges),dtype=int)
    elif model_id == 'four_chamber_m1':
        from physiosim.models.four_chamber_m1 import COMPARTMENTS, EDGES, INCIDENCE
        edges = [dict(name=e.name,source=e.source,target=e.target,kind=e.kind) for e in EDGES]
        incidence = INCIDENCE.astype(int)
    else:
        raise ValueError('unknown engine release')
    return list(COMPARTMENTS),edges,incidence.tolist()


def build_dependency_graph(model):
    compartments,edges,incidence = engine_topology(model.model_id)
    laws=[]
    mid=model.model_id
    code='src/physiosim/models/'+('cardiovascular' if mid=='phase1' else 'four_chamber_m1')+'.py'
    sim='src/physiosim/simulation/'+('__init__' if mid=='phase1' else 'four_chamber_m1')+'.py'
    def add(output,inputs,equation,kind='definition',temporal='instantaneous',coefficients=None,evidence=None):
        inputs=list(dict.fromkeys(model.quantity(n).name for n in inputs))
        output=model.quantity(output).name
        laws.append({'id':mid+':law:'+kind+':'+output, 'kind':kind,
                     'outputs':[output], 'inputs':inputs, 'equation':equation,
                     'temporal':temporal,'coefficients':coefficients or {},
                     'evidence':evidence or [code,model.quantity(output).evidence[0]]})
    add('period',['heart_rate'],'period = 60 / heart_rate')
    add('beat_duration',['time','solver.samples_per_cycle'],
        'n=samples_per_cycle; beat=time[-n-1:]; duration=beat[-1]-beat[0]',temporal='final_complete_beat',evidence=[sim])
    add('activation',['time','period','systolic_fraction'],
        'phase=(time % period)/period; e=0.5*(1-cos(2*pi*phase/systolic_fraction)) if phase<systolic_fraction else 0',
        'constitutive',evidence=['src/physiosim/models/cardiovascular.py#elastance'])
    for c in ('lv','rv'):
        add('E_'+c,['activation','emin_'+c,'emax_'+c],
            'E_'+c+' = emin_'+c+' + (emax_'+c+' - emin_'+c+')*activation','constitutive')
    for c in compartments:
        for vector in ('initial_volumes','unstressed_volumes'):
            add(vector+'.'+c,[vector],f'{vector}.{c} = {vector}[{compartments.index(c)}]')
        add('V_'+c,['initial_volumes.'+c],f'V_{c}(0) = initial_volumes.{c}','initialization',temporal='initial')
        coefficient='E_'+c if c in ('lv','rv') else 'elastance_'+c if c in ('la','ra') else 'compliance_'+c
        equation=f'P_{c} = (V_{c} - unstressed_volumes.{c})'
        equation += (' / ' if coefficient.startswith('compliance') else ' * ')+coefficient
        add('P_'+c,['V_'+c,'unstressed_volumes.'+c,coefficient],equation,'constitutive')
        coefficients={'Q_'+e['name']:incidence[compartments.index(c)][j] for j,e in enumerate(edges)
                      if incidence[compartments.index(c)][j]}
        add('rhs['+c+']',list(coefficients),'dV_'+c+'/dt = '+ ' + '.join(f'{v}*{k}' for k,v in coefficients.items()),
            'conservation',coefficients=coefficients)
        add('V_'+c,['rhs['+c+']','time','initial_volumes.'+c],f'V_{c}(t) = V_{c}(0) + integral(rhs[{c}], 0..t)',
            'state_evolution',temporal='run',evidence=[code,sim])
    for e in edges:
        name,source,target=e['name'],e['source'],e['target']
        expr=f'(P_{source} - P_{target}) / resistance_{name}'
        add('Q_'+name,['P_'+source,'P_'+target,'resistance_'+name],
            f'Q_{name} = '+('max('+expr+', 0)' if e['kind']=='diode' else expr),'constitutive')
        add('Q_cum_'+name,['Q_'+name,'time'],f'Q_cum_{name}(t) = integral(Q_{name}, 0..t); Q_cum_{name}(0)=0',
            temporal='run_integrated',evidence=[sim])
    if 'V_total' in {q.name for q in model.quantities}:
        add('V_total',['V_'+c for c in compartments],'V_total = sum(V_c for c in compartments)')
    covered={o for l in laws for o in l['outputs']}
    for q in model.quantities:
        if q.name in covered or q.kind not in ('metric','diagnostic') or q.name.startswith('solver.'):
            continue
        inputs,equation=_summary_definition(model,q,compartments,edges)
        add(q.name,inputs,equation,temporal=q.aggregation,
            evidence=[sim,'src/physiosim/agent/tools.py#_metrics'] if q.kind=='metric' else
                     [sim,'src/physiosim/agent/tools.py#_periodicity','src/physiosim/validation/__init__.py'])
    return {'model_id':mid,'model_version':model.model_version,
            'scope':'Existing executable equations and metric definitions; descriptive metadata, no numeric rebinding.',
            'compartments':compartments,'edges':edges,'incidence':incidence,'laws':laws}


def _summary_definition(model,q,compartments,edges):
    n=q.name; p=q.numerical_policy; c=q.compartment; e=q.edge
    volumes=['V_'+c for c in compartments]
    sampled=['time','solver.samples_per_cycle']
    if n=='heart_rate_bpm': return ['heart_rate'],'heart_rate_bpm = heart_rate'
    if 'ejection_fraction' in n:
        edv=c+'_edv_ml' if model.model_id=='phase1' else c+'_edv_sample_ml'
        esv=c+'_esv_ml' if model.model_id=='phase1' else c+'_esv_sample_ml'
        return [edv,esv],f'{n} = ({edv} - {esv}) / {edv}'
    if e:
        scale=' * 0.06' if q.unit=='L/min' else ''
        mean=' / beat_duration' if q.aggregation=='beat_mean' else ''
        if p.startswith('solver_integrated'):
            return ['Q_cum_'+e,*sampled]+(['beat_duration'] if mean else []),f'{n} = (Q_cum_{e}[-1] - Q_cum_{e}[-n-1])'+mean+scale+'; n=samples_per_cycle'
        expr='max(Q_'+e+',0)' if 'positive' in p else 'max(-Q_'+e+',0)' if 'negative' in p else 'Q_'+e
        return ['Q_'+e,*sampled]+(['beat_duration'] if mean else []),f'{n} = trapezoid({expr}[final_beat], time[final_beat])'+mean+scale
    if q.property_id in (PROPERTIES['pressure'].uri,PROPERTIES['volume'].uri) and c:
        source=('P_' if q.property_id==PROPERTIES['pressure'].uri else 'V_')+c
        if q.aggregation=='beat_mean':
            return [source,*sampled,'beat_duration'],f'{n} = trapezoid({source}[final_beat], time[final_beat]) / beat_duration'
        stat='max' if q.aggregation=='extremum_max' else 'min'
        return [source,*sampled],f'{n} = {stat}({source}[final_beat]); final_beat = [-samples_per_cycle-1:]'
    if n=='total_initial_volume_ml': return ['initial_volumes'],n+' = sum(initial_volumes)'
    if 'drift' in n:
        return volumes,n+' = max(abs(sum(V_c(t)) - sum(V_c(0)))) over all samples'
    if n=='local_balance_residual_ml':
        return volumes+['Q_cum_'+e['name'] for e in edges],n+' = max(abs(V(t)-V(0)-INCIDENCE @ Q_cum(t))); wiring/roundoff only'
    if n.startswith('periodicity.') or n=='final_beat_max_volume_difference_ml':
        return (['V_'+c] if c else volumes)+sampled,n+' = max(abs(V[-n-1:] - V[-2*n-1:-n])); n=samples_per_cycle; unavailable with fewer than two beats'
    if n.startswith('agent_periodicity.'):
        field=n.split('.')[1]
        if field in ('threshold','definition'):
            value=model.policies['agent_periodicity']['threshold' if field=='threshold' else 'definition']
            return [],f'{n} = {value!r}; declared software policy'
        if field in ('comparisons','available'):
            return ['solver.cycles'],f'count=min(3,cycles-1); {n} = '+('max(count,0)' if field=='comparisons' else 'count>=1')
        if field=='max_relative_change':
            return volumes+sampled+['solver.cycles'],n+' = max over last min(3,cycles-1) beat pairs of max_c(max_phase(abs(current-prior))/max(max_phase(abs(prior)),1 mL)); null if no pair'
        return ['agent_periodicity.max_relative_change','agent_periodicity.threshold','agent_periodicity.available'],n+' = available and max_relative_change < threshold'
    if n.startswith('strict_periodicity.'):
        field=n.split('.')[1]
        if field in ('beats','tolerance_ml'):
            return [],f'{n} = {model.policies["strict_periodicity"]["default_beats" if field=="beats" else "tolerance_ml"]!r}; default software policy'
        if field=='available':
            return volumes+['solver.samples_per_cycle','strict_periodicity.beats'],n+' = (len(volumes)-1)/samples_per_cycle >= beats+1'
        if field=='residuals_ml':
            return volumes+['solver.samples_per_cycle','strict_periodicity.beats'],n+' = [max(abs(V[j*n:(j+1)*n+1]-V[(j-1)*n:j*n+1])) for j in range(cycles-beats,cycles)]; n=samples_per_cycle; cycles=(len(V)-1)/n; [] if unavailable'
        if field=='max_residual_ml': return ['strict_periodicity.residuals_ml'],n+' = max(residuals_ml) or unavailable'
        if field=='monotone_nonincreasing': return ['strict_periodicity.residuals_ml','strict_periodicity.available'],n+' = available and all(residual[i+1] <= residual[i])'
        return ['strict_periodicity.max_residual_ml','strict_periodicity.tolerance_ml','strict_periodicity.available'],n+' = available and max_residual_ml <= tolerance_ml'
    if n.startswith('audit_closed_loop.'):
        if n.endswith('volume_tolerance_ml'):
            return [],n+' = 1e-6 mL; agent software policy'
        return volumes,n+' = max(abs(sum(V_c(t)) - sum(V_c(0))))'
    raise ValueError('missing metric definition: '+n)


def validate_dependency_graph(model,graph):
    """Closed release validation rejects incomplete laws and mass-balanced rewiring."""
    if graph != build_dependency_graph(model):
        raise ValueError('dependency law/topology/input contract mismatch')
    ids=[l['id'] for l in graph['laws']]
    if len(ids)!=len(set(ids)): raise ValueError('duplicate law ID')
    for law in graph['laws']:
        for name in law['inputs']+law['outputs']: model.quantity(name)
