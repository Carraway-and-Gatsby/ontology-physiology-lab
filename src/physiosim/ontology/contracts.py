"""Canonical typed quantity contracts for the two executable model releases.

Metadata construction never runs a solver. Local identifiers are model design
assertions; retained external terms supply base properties, not equivalence.
"""
import json
from importlib.resources import files


def acceptance_matrix():
    return json.loads(files(__package__).joinpath('acceptance_matrix.json').read_text())

from dataclasses import asdict, dataclass, field
import math
from typing import Literal
from . import PROPERTIES, CONTEXTS

Kind = Literal['state', 'auxiliary_state', 'parameter', 'parameter_component',
               'algebraic_output', 'law_quantity', 'metric', 'diagnostic', 'time']
Status = Literal['used', 'context', 'catalogue-only', 'proposed', 'unknown', 'local']
KINDS = set(Kind.__args__)
STATUSES = set(Status.__args__)
AGGREGATIONS = {'instantaneous', 'initial', 'constant_parameter', 'beat_mean',
                'beat_integrated', 'run_integrated', 'extremum_max', 'extremum_min',
                'ratio', 'count', 'run_max', 'beat_pair_max', 'policy', 'sum'}
RELATIONS = {'blood_contained_in', 'lumped_compartment_context', 'organ_bearer',
             'traverses', 'bqbiol:occursIn', 'model_context', 'catalogue_presence'}
from .representation import GAUGE, pressure_reference
# Only retained v1.07 base properties; local concepts are classifications instead.
_PROPERTY_UNITS = {PROPERTIES[k].uri: u for k, u in {
    'pressure': {'mmHg'}, 'volume': {'mL', 'L'}, 'flow': {'mL/s', 'L/min', 'm^3/s'},
    'resistance': {'mmHg*s/mL'}, 'elastance': {'mmHg/mL'},
    'frequency': {'1/min', 'beat/min', '1/s'},
}.items()}


@dataclass(frozen=True)
class AnatomyContext:
    key: str
    relation: str
    status: Status
    note: str = ''

    def __post_init__(self):
        if not self.key or self.relation not in RELATIONS or self.status not in STATUSES:
            raise ValueError('invalid anatomy relation/status')
        if self.key.startswith('local:'):
            if self.status not in {'local', 'unknown', 'proposed'}:
                raise ValueError('local/proposed context cannot be promoted to adopted anatomy')
        else:
            nodes = json.loads(files(__package__).joinpath('anatomy_nodes_v2.json').read_text())
            if self.key not in {n['key'] for n in nodes['nodes']}:
                raise ValueError('anatomy key absent from retained v2 evidence')
            if self.status in {'local', 'unknown', 'proposed'}:
                raise ValueError('adopted v2 key requires explicit evidence status')


# canonical-unit -> alias-unit scale, explicitly reviewed instead of arbitrary factors
_ALIAS_SCALES = {('1/min', 'beat/min'): 1., ('1/min', '1/s'): 1/60,
                 ('mL/s', 'L/min'): .06, ('mL/s', 'm^3/s'): 1e-6,
                 ('mL', 'L'): .001}


@dataclass(frozen=True)
class Alias:
    name: str
    unit: str
    factor: float = 1.

    def convert(self, value):
        return value * self.factor


@dataclass(frozen=True)
class QuantityContract:
    model_id: str
    model_version: str
    name: str
    kind: Kind
    property_id: str | None
    classification: str | None
    aggregation: str
    unit: str
    bearer: str
    process_context: tuple[str, ...]
    anatomy: tuple[AnatomyContext, ...]
    evidence: tuple[str, ...]
    aliases: tuple[Alias, ...] = ()
    reference: str = 'not_applicable'
    compartment: str | None = None
    edge: str | None = None
    direction: tuple[str, str] | None = None
    participants: tuple[str, ...] = ()
    order: tuple[str, ...] = ()
    numerical_policy: str = 'not_applicable'
    unavailable: str = 'not_applicable'
    note: str = ''

    @property
    def id(self):
        return self.model_id + ':' + self.name

    def __post_init__(self):
        if not all(isinstance(x, str) and x.strip() for x in
                   (self.model_id, self.model_version, self.name, self.unit, self.bearer)):
            raise ValueError('missing model/version/name/unit/bearer')
        if self.kind not in KINDS or self.aggregation not in AGGREGATIONS:
            raise ValueError('invalid kind/aggregation')
        if bool(self.property_id) == bool(self.classification):
            raise ValueError('exactly one OPB property or local/nonphysical classification required')
        if self.property_id and self.unit not in _PROPERTY_UNITS.get(self.property_id, set()):
            raise ValueError('property/unit outside retained base contract')
        if self.classification and not self.classification.startswith(('local:', 'nonphysical:')):
            raise ValueError('classification must explicitly be local or nonphysical')
        if not self.bearer.startswith(self.model_id+':') or any(
                not p.startswith(self.model_id+':blood:') for p in self.participants):
            raise ValueError('bearer/participant model scope mismatch')
        if not self.evidence or not all(self.evidence) or not self.process_context:
            raise ValueError('missing evidence/process context')
        if self.property_id == PROPERTIES['pressure'].uri and self.reference != GAUGE:
            raise ValueError('pressure requires mathematical model gauge; atmosphere unknown')
        if self.property_id == PROPERTIES['resistance'].uri and not self.bearer.startswith(self.model_id+':path:'):
            raise ValueError('resistance bearer must be model flow path')
        if self.property_id == PROPERTIES['elastance'].uri and self.compartment in ('lv','rv'):
            if self.bearer != self.model_id+':organ:'+self.compartment:
                raise ValueError('ventricular elastance requires organ bearer, never wall/cavity')
        if self.compartment in _VESSELS and any(
                a.key != _VESSELS[self.compartment] or a.relation != 'lumped_compartment_context'
                for a in self.anatomy):
            raise ValueError('vascular blood requires non-identity lumen context, never atrial identity')
        if self.compartment and self.property_id in (PROPERTIES['volume'].uri, PROPERTIES['pressure'].uri):
            if self.bearer != self.model_id+':blood:'+self.compartment:
                raise ValueError('compartment pressure/volume must describe the same local blood entity')
        if self.model_id=='phase1' and self.compartment in ('la','ra'):
            raise ValueError('Phase 1 has no separate atrial quantity')
        if self.property_id == PROPERTIES['elastance'].uri and self.compartment in ('lv','rv'):
            if not any(a.key==self.compartment and a.relation=='organ_bearer' for a in self.anatomy):
                raise ValueError('ventricular elastance anatomy must be organ-level ventricle')
        if self.property_id == PROPERTIES['resistance'].uri and any(a.relation=='bqbiol:occursIn' for a in self.anatomy):
            raise ValueError('occursIn belongs to flow process, not resistance')
        names = {self.name}
        for a in self.aliases:
            expected = 1. if a.unit == self.unit else _ALIAS_SCALES.get((self.unit,a.unit))
            if not a.name or a.name in names or expected is None or not math.isfinite(a.factor) or a.factor != expected:
                raise ValueError('invalid/duplicate alias or untested conversion')
            names.add(a.name)


@dataclass(frozen=True)
class ModelContract:
    model_id: str
    model_version: str
    quantities: tuple[QuantityContract, ...]
    inventory: dict[str, tuple[str, ...]]
    paths: dict = field(default_factory=dict)
    anatomy_usage: dict[str, str] = field(default_factory=dict)
    policies: dict = field(default_factory=dict)
    blood_entities: dict = field(default_factory=dict)
    pressure_differentials: dict = field(default_factory=dict)
    dependency_graph: dict = field(default_factory=dict)

    def __post_init__(self):
        names = []
        for q in self.quantities:
            if (q.model_id,q.model_version) != (self.model_id,self.model_version):
                raise ValueError('quantity model/version mismatch')
            names.extend((q.name, *(a.name for a in q.aliases)))
        if len(names) != len(set(names)):
            raise ValueError('duplicate quantity/alias')
        for category, members in self.inventory.items():
            if len(members) != len(set(members)) or not set(members) <= set(names):
                raise ValueError('unresolved/duplicate inventory: '+category)

        if self.paths or self.blood_entities or self.pressure_differentials:
            from .representation import validate_representation
            validate_representation(self)

        if self.paths or self.dependency_graph:
            from .dependencies import validate_dependency_graph
            validate_dependency_graph(self,self.dependency_graph)

    def quantity(self, name):
        for q in self.quantities:
            if name == q.name or name in {a.name for a in q.aliases}:
                return q
        raise KeyError(self.model_id+':'+name)

    def unit(self, name):
        q = self.quantity(name)
        return next((a.unit for a in q.aliases if a.name == name), q.unit)

    def convert(self, name, value):
        q = self.quantity(name)
        return next((a.convert(value) for a in q.aliases if a.name == name), value)


@dataclass(frozen=True)
class ContractBundle:
    models: tuple[ModelContract, ...]
    schema_version: str = '1.0.0'

    def __post_init__(self):
        ids = [m.model_id for m in self.models]
        if not ids or len(ids) != len(set(ids)):
            raise ValueError('empty/duplicate model IDs')

    def to_json(self):
        return json.dumps(asdict(self), sort_keys=True, indent=2, allow_nan=False)+'\n'

    @classmethod
    def from_json(cls, text):
        data = json.loads(text)
        models = []
        for m in data['models']:
            quantities = []
            for q in m['quantities']:
                q['anatomy'] = tuple(AnatomyContext(**a) for a in q['anatomy'])
                q['aliases'] = tuple(Alias(**a) for a in q['aliases'])
                for key in ('process_context','evidence','participants','order'):
                    q[key] = tuple(q[key])
                if q['direction'] is not None: q['direction'] = tuple(q['direction'])
                quantities.append(QuantityContract(**q))
            m['quantities'] = tuple(quantities)
            m['inventory'] = {k:tuple(v) for k,v in m['inventory'].items()}
            models.append(ModelContract(**m))
        return cls(tuple(models),data['schema_version'])

_VESSELS = {'sa':'systemic_arterial_lumen', 'sv':'systemic_venous_lumen',
            'pa':'pulmonary_arterial_lumen', 'pv':'pulmonary_venous_lumen'}
_VALVES = {'aortic':'aortic_valve', 'tricuspid':'tricuspid_valve',
           'pulmonary_valve':'pulmonary_valve', 'mitral':'mitral_valve'}


def _compartment_context(c):
    return AnatomyContext(c+'_cavity', 'blood_contained_in', 'used') if c not in _VESSELS else AnatomyContext(
        _VESSELS[c], 'lumped_compartment_context', 'context',
        'Non-identity lumen context; model-local lumped compartment retained.')


def _paths(model_id, compartments, edges):
    from .resistance import resistance_details
    details = resistance_details()
    paths = {}
    for name, source, target, kind in edges:
        keys = [_VALVES[name]] if name in _VALVES else []
        if name == 'systemic':
            keys = ['systemic_arterial_lumen', 'local:systemic_microvascular_bed', 'systemic_venous_lumen']
        elif name == 'pulmonary':
            keys = ['pulmonary_arterial_lumen', 'local:pulmonary_microvascular_bed', 'pulmonary_venous_lumen']
        elif name == 'venous_return': keys = ['systemic_venous_lumen', 'ra_cavity']
        elif name == 'pulmonary_venous': keys = ['pulmonary_venous_lumen', 'la_cavity']
        elif model_id == 'phase1' and name in ('mitral','tricuspid'):
            keys = (['pulmonary_venous_lumen', 'la', 'mitral_valve'] if name == 'mitral' else
                    ['systemic_venous_lumen', 'ra', 'tricuspid_valve'])
        contexts = []
        for key in keys:
            note = 'No dedicated v2 node; model-local path segment, no adopted external identifier.' if key.startswith('local:') else ''
            if model_id == 'phase1' and key in ('la','ra'):
                note = 'Lumped atrial filling in venous reservoir; no separate atrial state or identity.'
            contexts.append(AnatomyContext(key,'traverses','unknown' if key.startswith('local:') else 'context',note))
        paths[name] = {'id':model_id+':path:'+name, 'source':source, 'target':target, 'kind':kind,
                       'participants':[model_id+':blood:'+c for c in (source,target)],
                       'traverses':[asdict(c) for c in contexts],
                       'process_location':_VALVES.get(name),
                       'evidence':['docs/decisions.md#2026-11-02', 'docs/physiology'+('_four_chamber_m1' if model_id!='phase1' else '')+'.md']}
        if name in details:
            paths[name]['resistance_detail'] = details[name]
    return paths


class _Builder:
    def __init__(self, model_id, version, compartments, edges, parameter_type):
        self.model_id, self.version = model_id, version
        self.compartments, self.edges = compartments, edges
        self.parameter_type = parameter_type
        self.quantities, self.inventory = {}, {}
        self.paths = _paths(model_id, compartments, edges)
        self.doc = 'docs/physiology'+('_four_chamber_m1' if model_id!='phase1' else '')+'.md'

    def add(self, name, kind, prop, unit, aggregation='instantaneous', *, category=None,
            c=None, edge=None, bearer=None, anatomy=None, aliases=(), policy='not_applicable',
            unavailable='not_applicable', order=(), note=''):
        if self.model_id == 'phase1' and c in ('sv', 'pv'):
            note = (note+' Phase 1 atrial filling is lumped in this venous compartment; no separate atrial state or identity.').strip()
        property_id = PROPERTIES[prop].uri if prop in PROPERTIES and not PROPERTIES[prop].local else None
        classification = None if property_id else prop
        if classification and not classification.startswith(('local:', 'nonphysical:')):
            classification = 'local:'+classification
        process = CONTEXTS['contraction' if prop in ('elastance','frequency','local:activation_fraction') else 'circulation'].uri
        if classification and classification.startswith('nonphysical:'):
            process = 'local:numerical_policy'
        if bearer is None:
            bearer = ('blood:'+c if c else 'flow_process:'+edge if edge else 'model')
        if anatomy is None:
            anatomy = (_compartment_context(c),) if c else ()
            if edge:
                anatomy = (AnatomyContext(_VALVES[edge],'bqbiol:occursIn','used'),) if edge in _VALVES else ()
        path = self.paths.get(edge)
        q = QuantityContract(self.model_id,self.version,name,kind,property_id,classification,
            aggregation,unit,self.model_id+':'+bearer,(process,),tuple(anatomy),
            (self.doc,'docs/decisions.md#2026-11-02'),tuple(aliases),
            reference=GAUGE if prop=='pressure' else 'not_applicable', compartment=c,edge=edge,
            direction=(path['source'],path['target']) if path else None,
            participants=tuple(path['participants']) if path else (), order=tuple(order),
            numerical_policy=policy,unavailable=unavailable,note=note)
        if name in self.quantities: raise ValueError('duplicate builder quantity: '+name)
        self.quantities[name] = q
        if category: self.group(category,name)
        return q

    def group(self, category, *names):
        self.inventory.setdefault(category,[]).extend(names)

    def parameters(self):
        from dataclasses import fields
        for f in fields(self.parameter_type):
            name = f.name
            c = name.rsplit('_',1)[-1]
            kw = {}; aliases = []
            if name.endswith('volumes'):
                prop,unit = 'volume','mL'
                kw = {'bearer':'blood_collection', 'order':self.compartments}
            elif name.startswith('resistance_'):
                prop,unit = 'resistance','mmHg*s/mL'
                e = name[11:]
                kw = {'edge':e, 'bearer':'path:'+e,
                      'anatomy':tuple(AnatomyContext(**a) for a in self.paths[e]['traverses'])}
                aliases = [Alias('R_'+e,unit)]
            elif name.startswith('compliance_'):
                prop,unit = 'local:fluid_volume_compliance','mL/mmHg'
                kw = {'c':c,'bearer':'compartment:'+c}
                aliases = [Alias('C_'+c,unit)]
            elif name.startswith(('emin_','emax_','elastance_')):
                prop,unit = 'elastance','mmHg/mL'
                if c in ('lv','rv'):
                    kw = {'c':c,'bearer':'organ:'+c,'anatomy':(AnatomyContext(c,'organ_bearer','used'),)}
                else:
                    kw = {'c':c,'bearer':'compartment:'+c}
            elif name == 'heart_rate':
                prop,unit = 'frequency','1/min'
                kw = {'bearer':'heart_process','anatomy':(AnatomyContext('heart','model_context','used'),)}
                aliases = [Alias('HR','1/min'), Alias('HR_per_s','1/s',1/60)]
            else:
                prop,unit = 'local:activation_fraction','dimensionless'
                kw = {'bearer':'activation_construct'}
            aggregation = 'initial' if name=='initial_volumes' else 'constant_parameter'
            self.add(name,'parameter',prop,unit,aggregation,category='parameter',aliases=aliases,**kw)
            if name.endswith('volumes'):
                for component in self.compartments:
                    port = name+'.'+component
                    self.add(port,'parameter_component','volume','mL',aggregation,
                             category='parameter_component',c=component)
                    self.group('scalar_parameter_port',port)
            else: self.group('scalar_parameter_port',name)

    def finish(self):
        nodes = json.loads(files(__package__).joinpath('anatomy_nodes_v2.json').read_text())['nodes']
        used = {a.key for q in self.quantities.values() for a in q.anatomy if a.status=='used'} | {'blood'}
        context = {a['key'] for p in self.paths.values() for a in p['traverses']}
        context |= {a.key for q in self.quantities.values() for a in q.anatomy if a.status=='context'}
        usage = {n['key']:'used' if n['key'] in used else 'context' if n['key'] in context else 'catalogue-only' for n in nodes}
        from types import SimpleNamespace
        from .representation import build_representation
        from .dependencies import build_dependency_graph
        data = dict(model_id=self.model_id,model_version=self.version,quantities=tuple(self.quantities.values()),
                    inventory={k:tuple(v) for k,v in self.inventory.items()},paths=self.paths,
                    anatomy_usage=usage,policies=_policies())
        # Construct derived metadata before the immutable, fully validated contract.
        view = SimpleNamespace(**data)
        view.quantity = lambda name: ModelContract.quantity(view,name)
        blood, pressure = build_representation(view)
        return ModelContract(**data,blood_entities=blood,pressure_differentials=pressure,
                             dependency_graph=build_dependency_graph(view))


def _phase1_builder():
    from physiosim.models.cardiovascular import COMPARTMENTS, FLOW_NAMES, VALVE_INDICES, Parameters
    edges = tuple((name,COMPARTMENTS[i],COMPARTMENTS[(i+1)%len(COMPARTMENTS)],
                   'diode' if i in VALVE_INDICES else 'resistor') for i,name in enumerate(FLOW_NAMES))
    return _Builder('phase1','phase1-f7d9cd1',COMPARTMENTS,edges,Parameters)


def build_phase1_contract():
    b = _phase1_builder()
    b.parameters()
    _dynamics(b)
    _phase1_metrics(b)
    _agent_metrics(b)
    _numerical_controls(b)
    return b.finish()


def _dynamics(b):
    for c in b.compartments:
        b.add('V_'+c,'state','volume','mL',category='physical_state',c=c)
        b.add('P_'+c,'algebraic_output','pressure','mmHg',category='algebraic_output',c=c)
        b.add('rhs['+c+']','law_quantity','local:volume_rate','mL/s',category='derivative',c=c,
              note='Signed volume derivative, not an inertial flow state.')
    for name,source,target,kind in b.edges:
        b.add('Q_'+name,'algebraic_output','flow','mL/s',category='algebraic_output',edge=name,
              policy='nonnegative_diode' if kind=='diode' else 'signed_resistor')
        b.add('Q_cum_'+name,'auxiliary_state','volume','mL','run_integrated',
              category='auxiliary_state',edge=name,policy='solver_integrated_signed' if kind=='resistor' else 'solver_integrated_forward',
              unavailable='optional_cumulative_flows' if b.model_id=='phase1' else 'not_applicable')
    for c in ('lv','rv'):
        b.add('E_'+c,'algebraic_output','elastance','mmHg/mL',category='algebraic_output',c=c,
              bearer='organ:'+c,anatomy=(AnatomyContext(c,'organ_bearer','used'),))
    b.add('time','time','nonphysical:independent_time','s',category='independent_variable')
    b.add('period','time','local:cycle_duration','s','constant_parameter',category='derived_timing')
    b.add('beat_duration','time','local:cycle_duration','s',category='derived_timing',
          note='Actual final sampled beat endpoint duration used by metric code.')
    b.add('activation','law_quantity','local:activation_fraction','dimensionless',category='internal_law_quantity',
          bearer='activation_construct',note='Synchronous cosine e(t); model construct, not a structure.')


def _phase1_metrics(b):
    b.add('heart_rate_bpm','metric','frequency','1/min','constant_parameter',category='metric')
    b.add('stroke_volume_ml','metric','volume','mL','beat_integrated',category='metric',edge='aortic',
          aliases=(Alias('SV','mL'),),policy='sampled_trapezoidal')
    b.add('CO','metric','flow','mL/s','beat_mean',edge='aortic',
          aliases=(Alias('cardiac_output_l_min','L/min',.06),Alias('cardiac_output_m3_s','m^3/s',1e-6)),
          policy='sampled_trapezoidal')
    b.group('metric','cardiac_output_l_min','cardiac_output_m3_s')
    b.group('binding_observable','CO','SV')
    for name,agg in [('lv_edv_ml','extremum_max'),('lv_esv_ml','extremum_min')]:
        b.add(name,'metric','volume','mL',agg,category='metric',c='lv',policy='sampled_final_beat')
    b.add('lv_ejection_fraction','metric','local:volume_excursion_fraction','dimensionless','ratio',
          category='metric',c='lv',policy='sampled_volume_extrema',note='(EDV-ESV)/EDV, not necessarily flow-derived SV/EDV.')
    for name,c,agg in [('systemic_systolic_pressure_mmhg','sa','extremum_max'),
                       ('systemic_diastolic_pressure_mmhg','sa','extremum_min'),
                       ('systemic_mean_pressure_mmhg','sa','beat_mean'),
                       ('pulmonary_mean_pressure_mmhg','pa','beat_mean'),
                       ('pulmonary_venous_mean_pressure_mmhg','pv','beat_mean')]:
        b.add(name,'metric','pressure','mmHg',agg,category='metric',c=c,policy='sampled_trapezoidal' if agg=='beat_mean' else 'sampled_final_beat')
    b.add('volume_drift_ml','diagnostic','nonphysical:conservation_residual','mL','run_max',category='metric',
          policy='max_absolute_total_volume_drift')
    b.add('final_beat_max_volume_difference_ml','diagnostic','nonphysical:absolute_periodicity','mL',
          'beat_pair_max',category='metric',policy='sampled_last_two_beats_absolute_max',unavailable='raw_nan_serialized_null')
    b.add('stroke_volume_cumulative_ml','metric','volume','mL','beat_integrated',category='cumulative_metric',
          edge='aortic',policy='solver_integrated_difference',unavailable='optional_cumulative_flows')
    b.add('cardiac_output_cumulative_l_min','metric','flow','L/min','beat_mean',category='cumulative_metric',
          edge='aortic',policy='solver_integrated_difference',unavailable='optional_cumulative_flows')
    for name,_,_,kind in b.edges:
        b.add('final_beat_net_throughput_'+name+'_ml','metric','volume','mL','beat_integrated',category='cumulative_metric',
              edge=name,policy='solver_integrated_signed_difference' if kind=='resistor' else 'solver_integrated_difference',
              unavailable='optional_cumulative_flows')
    b.add('local_balance_residual_ml','diagnostic','nonphysical:local_balance_residual','mL','run_max',
          category='diagnostic_metric',policy='incidence_wiring_and_roundoff_only',unavailable='null_without_cumulative_flows')
    b.add('V_total','algebraic_output','volume','mL','sum',category='binding_observable',bearer='blood_collection')


def diagnostic_values(result):
    """Strict JSON-safe diagnostic projection; original engine APIs are untouched."""
    if hasattr(result,'conservation'):
        values = result.conservation()
        p = result.periodicity()
        values['periodicity.max_difference_ml'] = p['max_difference_ml']
        values.update({'periodicity.per_compartment_ml.'+c:None if p['per_compartment_ml'] is None else p['per_compartment_ml'][c]
                       for c in result.compartment_names})
        return values
    return {'local_balance_residual_ml':result.local_balance_residual_ml() if result.cumulative_flows is not None else None}


def _m1_builder():
    from physiosim.models.four_chamber_m1 import MODEL_ID, MODEL_VERSION, COMPARTMENTS, EDGES, FourChamberM1Parameters
    return _Builder(MODEL_ID,MODEL_VERSION,COMPARTMENTS,
                    tuple((e.name,e.source,e.target,e.kind) for e in EDGES),FourChamberM1Parameters)


def _m1_metrics(b):
    from .four_chamber_m1_manifest import build_m1_manifest
    manifest = build_m1_manifest()
    reverse_properties = {v.uri:k for k,v in PROPERTIES.items()}
    inverse_aliases = {target:alias for alias,target in manifest['metric_aliases'].items()}
    # The release manifest remains the adapter input, not a duplicated 62-name list.
    for name, record in manifest['variables'].items():
        if name in b.quantities: continue
        prop = reverse_properties.get(record['property'], 'local:volume_excursion_fraction')
        c, e = record['compartment'], record['edge']
        temporal = record['temporal']
        agg = {'beat_sample_extremum':'ratio' if 'fraction' in name else
               'extremum_max' if ('max' in name or 'edv' in name) else 'extremum_min'}.get(temporal,temporal)
        policy = ('solver_integrated_difference' if temporal in ('beat_mean','beat_integrated') and e else
                  'sampled_volume_extrema' if 'fraction' in name else
                  'sampled_trapezoidal' if temporal=='beat_mean' else 'sampled_final_beat')
        aliases = (Alias(inverse_aliases[name],record['unit']),) if name in inverse_aliases else ()
        b.add(name,'metric',prop,record['unit'],agg,c=c,edge=e,aliases=aliases,policy=policy,
              note='Adapted from M1 manifest; legacy kind '+record['kind']+'; no property equivalence asserted.')
        b.group('metric',inverse_aliases.get(name,name))
    b.group('manifest_variable',*manifest['variables'])
    for name in ('total_initial_volume_ml','total_volume_drift_ml','local_balance_residual_ml'):
        b.add(name,'diagnostic','nonphysical:conservation_diagnostic','mL',
              'initial' if name=='total_initial_volume_ml' else 'run_max',category='diagnostic_metric',
              policy='declared_initial_total' if name=='total_initial_volume_ml' else
                     'incidence_wiring_and_roundoff_only' if name=='local_balance_residual_ml' else 'max_absolute_total_volume_drift')
    for c in b.compartments:
        b.add('periodicity.per_compartment_ml.'+c,'diagnostic','nonphysical:absolute_periodicity','mL',
              'beat_pair_max',category='diagnostic_metric',c=c,
              policy='sampled_last_two_beats_absolute_max',unavailable='null_with_fewer_than_two_beats')
    b.add('periodicity.max_difference_ml','diagnostic','nonphysical:absolute_periodicity','mL',
          'beat_pair_max',category='diagnostic_metric',policy='sampled_last_two_beats_absolute_max',
          unavailable='null_with_fewer_than_two_beats')


def build_m1_contract():
    b = _m1_builder()
    b.parameters()
    _dynamics(b)
    _m1_metrics(b)
    _agent_metrics(b)
    _numerical_controls(b)
    return b.finish()


def _agent_metrics(b):
    from dataclasses import replace
    core = list(b.inventory['metric'])
    names = list(core)
    for c in b.compartments:
        for kind, prop, unit, suffix in [('pressure','pressure','mmHg','mmhg'),('volume','volume','mL','ml')]:
            for stat,agg in [('min','extremum_min'),('max','extremum_max'),('mean','beat_mean')]:
                name = f'{c}_{kind}_{stat}_{suffix}'
                if name not in b.quantities:
                    b.add(name,'metric',prop,unit,agg,c=c,
                          policy='sampled_trapezoidal' if stat=='mean' else 'sampled_final_beat')
                if name not in names: names.append(name)
    for edge,_,_,kind in b.edges:
        for suffix,prop,unit,agg,policy in [
            ('forward_volume_ml','volume','mL','beat_integrated','sampled_positive_trapezoidal'),
            ('backward_volume_ml','volume','mL','beat_integrated','sampled_negative_magnitude_trapezoidal'),
            ('mean_flow_ml_s','flow','mL/s','beat_mean','sampled_signed_trapezoidal')]:
            name = edge+'_'+suffix
            b.add(name,'metric',prop,unit,agg,edge=edge,policy=policy,
                  note='Signed resistor throughput differs from positive-only forward volume.' if kind=='resistor' else 'Ideal diode; backward flow zero by engine law.')
            names.append(name)
    if b.model_id == 'four_chamber_m1':
        for alias,target in [('stroke_volume_ml','SV_lv'),('cardiac_output_l_min','lv_cardiac_output_l_min'),
                             ('lv_ejection_fraction','lv_ejection_fraction_sample')]:
            q = b.quantities[target]
            b.quantities[target] = replace(q,aliases=q.aliases+(Alias(alias,q.unit),))
            names.append(alias)
    b.group('agent_metric',*names)
    b.group('agent_added_metric',*(n for n in names if n not in core))
    policy_fields = {
        'agent_periodicity':{
            'available':('boolean','policy'), 'periodic':('boolean','policy'),
            'threshold':('dimensionless','ratio'), 'comparisons':('count','count'),
            'max_relative_change':('dimensionless','ratio'), 'definition':('text','policy')},
        'strict_periodicity':{
            'beats':('count','count'), 'tolerance_ml':('mL','policy'), 'residuals_ml':('mL','beat_pair_max'),
            'max_residual_ml':('mL','beat_pair_max'), 'monotone_nonincreasing':('boolean','policy'),
            'passed':('boolean','policy'), 'available':('boolean','policy')},
        'audit_closed_loop':{'volume_drift_ml':('mL','run_max'),'volume_tolerance_ml':('mL','policy')},
    }
    for group, records in policy_fields.items():
        for field,(unit,agg) in records.items():
            b.add(group+'.'+field,'diagnostic','nonphysical:'+group,unit,agg,category=group,
                  policy='relative_compartment_waveform_last_up_to_three_pairs' if group=='agent_periodicity' else
                         'absolute_waveform_last_requested_pairs' if group=='strict_periodicity' else 'total_volume_conservation',
                  unavailable='null_when_unavailable' if field in ('max_relative_change','max_residual_ml') else 'not_applicable',
                  note='Ordered by successive beat pair, not by compartment.' if field=='residuals_ml' else '')


def _policies():
    return {
        'agent_periodicity':{'threshold':1e-3,'comparison':'strict_less_than',
            'max_comparisons':3,'minimum_prior_volume_scale_ml':1.,'unit':'dimensionless',
            'definition':'max compartment waveform difference / max(prior-beat max absolute compartment volume, 1 mL)',
            'unavailable':'available=false, comparisons=0, max_relative_change=null'},
        'strict_periodicity':{'tolerance_ml':1e-4,'comparison':'less_than_or_equal',
            'default_beats':3,'unit':'mL','definition':'absolute max waveform difference over phases and compartments per beat pair',
            'unavailable':'raw max_residual_ml NaN; strict JSON projection null; available=false'},
        'pressure_reference':pressure_reference(),
        'review':{'physiology':'UNREVIEWED','numeric_inputs':'synthetic/exploratory','external_numeric_permission':'NONE'},
    }


def validate_quantity_connection(source, target):
    """Direct equivalence only; equal units alone never establish compatibility."""
    for name in ('model_id','model_version','kind','property_id','classification','aggregation',
                 'unit','bearer','reference','direction','participants','numerical_policy','compartment'):
        if getattr(source,name) != getattr(target,name):
            raise ValueError('quantity connection mismatch: '+name)
    return None


def build_contract_bundle():
    return ContractBundle((build_phase1_contract(),build_m1_contract()))


def agent_path_projection(model):
    """Offline lightweight agent projection of canonical D-G4 paths.

    Path identity is local. Traversed structures carry only retained v2 keys;
    they are not resistance bearers or an adopted anatomical path identifier.
    """
    anatomy = json.loads(files(__package__).joinpath('anatomy_nodes_v2.json').read_text())
    nodes = {n['key']:n for n in anatomy['nodes']}
    source = json.loads(files(__package__).joinpath('applied_la_mitral_lv_source_v1.json').read_text())
    fma_iris = {x['record']['base_id']:x['record']['base_iri'] for x in source['catalog']}
    result = {}
    for name,path in model.paths.items():
        ids = []
        for context in path['traverses']:
            node = nodes.get(context['key'])
            if node is None: continue
            for vocabulary in ('uberon','fma'):
                identifier = node.get(vocabulary)
                if not identifier: continue
                ids.append({'id':identifier,
                    'iri':fma_iris.get(identifier) if vocabulary=='fma' else
                          'http://purl.obolibrary.org/obo/'+identifier.replace(':','_'),
                    'label':node.get(vocabulary+'_label',node['structure']),
                    'relation':'related_structure' if vocabulary=='uberon' and node['primary']!='UBERON' else 'traversed_structure',
                    'context_relation':'traverses','anatomy_key':node['key']})
        result[name] = {'key':path['id'], 'label':f"Model flow path {path['source']} to {path['target']}",
                  'relation':'property_of_flow_path','ids':ids,'primary_id':None,
                  'source':'src/physiosim/ontology/contracts.py#'+model.model_id+':path:'+name,
                  'scope':'D-G4: model-local resistance bearer; IDs describe traversed anatomy, never the bearer.',
                  'source_compartment':path['source'], 'target_compartment':path['target'],
                  'traverses':path['traverses']}
        if 'resistance_detail' in path:
            result[name]['resistance_detail'] = path['resistance_detail']
    return result


def _numerical_controls(b):
    controls = {'cycles':'count','samples_per_cycle':'count','method':'identifier',
                'rtol':'dimensionless','atol':'mL','max_step':'s'}
    if b.model_id=='phase1': controls['cumulative_flows']='boolean'
    for name,unit in controls.items():
        b.add('solver.'+name,'diagnostic','nonphysical:numerical_control',unit,
              'count' if unit=='count' else 'policy',category='numerical_control',
              policy='numerical_control_not_physiological_input',
              note='Metadata only; no solver settings are modified. None max_step selects period/100.')
