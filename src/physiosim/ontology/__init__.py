"""Offline composite annotations; model assertions are not ontology entailments."""
from dataclasses import dataclass

BASE = 'https://example.org/physiosim/'  # Explicit project-local namespace, not a public ontology.
OPB_SOURCE = 'https://raw.githubusercontent.com/SemBioProcess/SemGen/master/src/semsim/owl/OPBv1.07.owl'
OLS_SOURCE = 'https://www.ebi.ac.uk/ols4/api/'
BQBIOL = 'http://biomodels.net/biology-qualifiers/'
OBO_XREF = 'http://www.geneontology.org/formats/oboInOwl#hasDbXref'


@dataclass(frozen=True)
class Concept:
    uri: str
    label: str
    source: str
    local: bool = False
    xref: str = ''  # the other ontology's identifier, kept on every v2 node


def _local(key, label):
    return Concept(BASE + 'concept/' + key, label, 'project-local model definition', True)


def _opb(number, label):
    return Concept('http://bhi.washington.edu/OPB#OPB_' + number, label, OPB_SOURCE)


def _uberon(number, label, fma):
    return Concept('http://purl.obolibrary.org/obo/UBERON_' + number, label, OLS_SOURCE, xref='FMA:' + fma)


PROPERTIES = {
    'pressure': _opb('00509', 'Fluid pressure'),
    'volume': _opb('00154', 'Fluid volume'),
    'flow': _opb('00299', 'Fluid flow rate'),
    'resistance': _opb('00160', 'Fluid flow resistance'),
    'elastance': _opb('00076', 'Fluid volumetric elastance'),
    'frequency': _opb('01212', 'Event frequency'),
    'compliance': _local('fluid_volume_compliance', 'Fluid volume compliance'),
    'stroke_volume': _local('stroke_volume', 'Left ventricular stroke volume per complete beat'),
    'cardiac_output': _local('cardiac_output', 'Cycle-mean aortic outflow'),
}
# Anatomical node specification v2 (docs/evidence_review/anatomy_nodes_v2.json): Uberon primary,
# FMA cross-reference kept. Only the nodes the registry refers to; keys follow the specification.
NODES = {
    'blood': _uberon('0000178', 'blood', '9670'),
    'lv_cavity': _uberon('0016514', 'cavity of left ventricle', '9466'),
    'rv_cavity': _uberon('0016509', 'cavity of right ventricle', '9291'),
    'mitral_valve': _uberon('0002135', 'mitral valve', '7235'),
    'aortic_valve': _uberon('0002137', 'aortic valve', '7236'),
    'tricuspid_valve': _uberon('0002134', 'tricuspid valve', '7234'),
    'pulmonary_valve': _uberon('0002146', 'pulmonary valve', '7246'),
    'heart': _uberon('0000948', 'heart', '7088'),
    'lv': _uberon('0002084', 'heart left ventricle', '7101'),
    'rv': _uberon('0002080', 'heart right ventricle', '7098'),
}
# Container of each compartment's blood, keyed by model compartment code (decisions.md C5: blood
# part_of cavity/lumen). The peripheral compartments stay local: no source maps them to v2 nodes.
ANATOMY = {
    'lv': NODES['lv_cavity'],
    'rv': NODES['rv_cavity'],
    **{k: _local(k, label) for k, label in {
        'sa': 'Lumped systemic arterial compartment', 'sv': 'Lumped systemic venous compartment',
        'pa': 'Lumped pulmonary arterial compartment', 'pv': 'Lumped pulmonary venous compartment',
        'circulation': 'Closed six-compartment blood circulation',
    }.items()},
}
BLOOD = NODES['blood']
# Location of each valve flow process, bqbiol:occursIn (decisions.md "Anatomical structures as nodes").
VALVES = {'aortic': NODES['aortic_valve'], 'tricuspid': NODES['tricuspid_valve'],
          'pulmonary_valve': NODES['pulmonary_valve'], 'mitral': NODES['mitral_valve']}
CONTEXTS = {
    'circulation': Concept('http://purl.obolibrary.org/obo/GO_0008015', 'blood circulation', OLS_SOURCE),
    'contraction': Concept('http://purl.obolibrary.org/obo/GO_0060047', 'heart contraction', OLS_SOURCE),
    'heart_failure': Concept('http://purl.obolibrary.org/obo/DOID_6000', 'congestive heart failure', OLS_SOURCE),
}


@dataclass(frozen=True)
class VariableAnnotation:
    name: str
    anatomy: Concept
    property: Concept
    unit: str
    equation: str
    role: str
    source_context: str = 'project six-compartment lumped cardiovascular model; not a clinical measurement'
    orientation: tuple[str, str] | None = None
    temporal_context: str = 'instantaneous'
    reference: str = 'not applicable'
    source_document: str = 'docs/physiology.md'
    applicable_contexts: tuple[str, ...] = ('baseline', 'reduced_contractility', 'partial_contractility_restoration')
    depends_on: tuple[str, ...] = ()
    biological_context: tuple[str, ...] = ('circulation',)
    bearer: str = 'blood'  # blood, compartment wall, flow process, or heart process
    occurs_in: Concept | None = None  # location of a flow process (valve flows only)
    flow_path: dict | None = None  # D-G4 canonical model-local resistance bearer

    @property
    def uri(self):
        return BASE + 'variable/' + self.name


def cardiovascular_registry() -> dict[str, VariableAnnotation]:
    """Return a fresh registry; names deliberately match the model's compartment codes."""
    from .contracts import _phase1_builder
    paths = _phase1_builder().paths
    registry = {}

    def add(name, anatomy, prop, unit, equation, role, **kwargs):
        registry[name] = VariableAnnotation(name, anatomy, PROPERTIES[prop], unit, equation, role, **kwargs)

    for compartment in ('lv', 'rv', 'sa', 'sv', 'pa', 'pv'):
        anatomy = ANATOMY[compartment]
        add('V_' + compartment, anatomy, 'volume', 'mL', 'dV/dt = Q_in - Q_out', 'state')
        chamber = compartment in ('lv', 'rv')
        add('P_' + compartment, anatomy, 'pressure', 'mmHg',
            'P = E(t)*(V - V0)' if chamber else 'P = (V - V0)/C', 'algebraic',
            reference='model gauge pressure; fixed external pressure zero',
            depends_on=('V_' + compartment, ('E_' if chamber else 'C_') + compartment))
        if chamber:
            # Organ-level v2 reference; whether the wall node fits a whole-chamber elastance is undecided.
            add('E_' + compartment, NODES[compartment], 'elastance', 'mmHg/mL',
                'E(t) = Emin + (Emax-Emin)*activation(t,HR)', 'time-varying parameter',
                depends_on=('HR',), biological_context=('contraction',), bearer='compartment wall')
        else:
            add('C_' + compartment, anatomy, 'compliance', 'mL/mmHg',
                'C = dV/dP; constant linear reservoir compliance', 'parameter', bearer='compartment wall')
    edges = [('aortic', 'lv', 'sa', True), ('systemic', 'sa', 'sv', False),
             ('tricuspid', 'sv', 'rv', True), ('pulmonary_valve', 'rv', 'pa', True),
             ('pulmonary', 'pa', 'pv', False), ('mitral', 'pv', 'lv', True)]
    for edge, origin, target, valve in edges:
        anatomy = _local('path_' + edge, f'Model flow path {origin} to {target}')
        orientation = (origin, target)
        add('Q_' + edge, anatomy, 'flow', 'mL/s',
            'Q = max(P_up-P_down,0)/R' if valve else 'Q = (P_up-P_down)/R', 'algebraic',
            orientation=orientation, depends_on=('P_' + origin, 'P_' + target, 'R_' + edge), bearer='flow process',
            occurs_in=VALVES.get(edge))
        add('R_' + edge, anatomy, 'resistance', 'mmHg*s/mL', 'R = pressure_drop / flow',
            'parameter', orientation=orientation, bearer='flow path', flow_path=paths[edge])
    add('HR', NODES['heart'], 'frequency', '1/min', 'T_seconds = 60 / HR_per_minute',
        'parameter', biological_context=('contraction',), bearer='heart process')
    add('CO', NODES['lv'], 'cardiac_output', 'mL/s', 'CO = integral(Q_aortic, complete_beat)/T',
        'observable', orientation=('lv', 'sa'), temporal_context='complete-beat mean', depends_on=('Q_aortic', 'HR'), bearer='flow process')
    add('SV', NODES['lv'], 'stroke_volume', 'mL', 'SV = integral(Q_aortic, complete_beat)',
        'observable', temporal_context='complete beat', depends_on=('Q_aortic',), bearer='flow process')
    add('V_total', ANATOMY['circulation'], 'volume', 'mL', 'V_total = sum(V_i)',
        'observable', depends_on=tuple('V_' + x for x in ('lv', 'rv', 'sa', 'sv', 'pa', 'pv')))
    return registry


class SemanticConnectionError(ValueError):
    """Variables cannot be directly equated under the requested contract."""


@dataclass(frozen=True)
class UnitConversion:
    """Explicit permission to rescale values, from exactly source_unit to target_unit.

    Pint supplies the multiplier; callers cannot provide unchecked factors. Only
    multiplicative cardiovascular units are supported; no offsets or sign flips.
    """
    source_unit: str
    target_unit: str


@dataclass(frozen=True)
class Connection:
    source: str
    target: str
    source_unit: str
    target_unit: str
    factor: float

    def convert(self, value):
        """Apply the validated numeric scale (also supports NumPy arrays)."""
        return value * self.factor


def validate_connection(source: VariableAnnotation, target: VariableAnnotation,
                        *, conversion: UnitConversion | None = None) -> Connection:
    """Validate direct variable equivalence, NOT physical adjacency or causality."""
    import math
    import pint

    for endpoint in (source, target):
        for field in ('name', 'unit', 'equation', 'role', 'source_context', 'source_document',
                      'temporal_context', 'reference', 'bearer'):
            value = getattr(endpoint, field)
            if not isinstance(value, str) or not value.strip():
                raise SemanticConnectionError(f'incomplete {field}')
        for field in ('anatomy', 'property', 'occurs_in'):
            concept = getattr(endpoint, field)
            if field == 'occurs_in' and concept is None:
                continue
            if not isinstance(concept, Concept) or any(not isinstance(value, str) or not value.strip()
                                                       for value in (concept.uri, concept.label, concept.source)):
                raise SemanticConnectionError(f'incomplete {field}')
        if not endpoint.biological_context or any(not isinstance(c, str) or not c.strip() for c in endpoint.biological_context):
            raise SemanticConnectionError('incomplete biological_context')
        if endpoint.property.uri in {PROPERTIES[k].uri for k in ('flow', 'resistance', 'cardiac_output')}:
            if not endpoint.orientation or len(endpoint.orientation) != 2 or any(c not in ANATOMY for c in endpoint.orientation):
                raise SemanticConnectionError('incomplete flow orientation')

    for field in ('anatomy', 'property'):
        if getattr(source, field).uri != getattr(target, field).uri:
            raise SemanticConnectionError(f'{field} mismatch')
    if (source.occurs_in and source.occurs_in.uri) != (target.occurs_in and target.occurs_in.uri):
        raise SemanticConnectionError('occurs_in mismatch')
    for field in ('orientation', 'temporal_context', 'reference', 'bearer', 'biological_context'):
        if getattr(source, field) != getattr(target, field):
            raise SemanticConnectionError(f'{field} mismatch')
    units = pint.UnitRegistry()
    canonical_units = {'pressure': 'mmHg', 'volume': 'mL', 'flow': 'mL/s',
                       'resistance': 'mmHg*s/mL', 'compliance': 'mL/mmHg',
                       'elastance': 'mmHg/mL', 'frequency': '1/min',
                       'stroke_volume': 'mL', 'cardiac_output': 'mL/s'}
    expected = {PROPERTIES[k].uri: u for k, u in canonical_units.items()}
    for endpoint in (source, target):
        if endpoint.property.uri not in expected:
            raise SemanticConnectionError('property has no supported units contract')
        try:
            units.Quantity(1, endpoint.unit).to(expected[endpoint.property.uri])
        except (pint.PintError, ValueError, TypeError) as exc:
            raise SemanticConnectionError(f'property and units incompatible: {exc}') from exc
    if source.unit != target.unit and conversion is None:
        # Distinguish a dimension error from a missing explicit rescaling contract.
        try:
            pint.UnitRegistry().Quantity(1, source.unit).to(target.unit)
        except (pint.PintError, ValueError, TypeError) as exc:
            raise SemanticConnectionError(f'units incompatible: {exc}') from exc
        raise SemanticConnectionError('explicit unit conversion contract required')
    if conversion is not None and (conversion.source_unit, conversion.target_unit) != (source.unit, target.unit):
        raise SemanticConnectionError('conversion contract does not match endpoint unit strings')
    try:
        units = pint.UnitRegistry()
        zero = units.Quantity(0, source.unit).to(target.unit).magnitude
        factor = units.Quantity(1, source.unit).to(target.unit).magnitude
    except (pint.PintError, ValueError, TypeError) as exc:
        raise SemanticConnectionError(f'units incompatible: {exc}') from exc
    if zero != 0 or not math.isfinite(factor) or factor <= 0:
        raise SemanticConnectionError('units require unsupported offset or nonpositive scale')
    return Connection(source.name, target.name, source.unit, target.unit, float(factor))


def build_graph(registry=None):
    """Build an RDFLib Dataset separating verified labels from model assertions.

    No OWL inference is performed. Mathematical and anatomical containment
    assertions are project interpretations, never asserted as external axioms.
    """
    from rdflib import Dataset, Namespace, URIRef, Literal
    from rdflib.namespace import RDF, RDFS, DCTERMS

    registry = cardiovascular_registry() if registry is None else registry
    ds = Dataset()
    ns = Namespace(BASE)
    ds.bind('sim', ns)
    ds.bind('dcterms', DCTERMS)
    model = ds.graph(URIRef(BASE + 'graph/model-assertions'))
    labels = ds.graph(URIRef(BASE + 'graph/verified-labels'))
    provenance = ds.graph(URIRef(BASE + 'graph/provenance'))
    provenance.add((model.identifier, DCTERMS.description,
                    Literal('Project-authored model assertions; not ontology entailments')))
    provenance.add((labels.identifier, DCTERMS.description,
                    Literal('Selected source-verified labels only; no imported ontology axioms')))
    # Only the source-verified built-in catalog is allowed in the verified graph.
    known = (*PROPERTIES.values(), *ANATOMY.values(), *NODES.values(), *CONTEXTS.values())
    verified = {c.uri: c for c in known if not c.local}
    for c in verified.values():
        labels.add((URIRef(c.uri), RDFS.label, Literal(c.label)))
        labels.add((URIRef(c.uri), DCTERMS.source, URIRef(c.source)))
        if c.xref:
            labels.add((URIRef(c.uri), URIRef(OBO_XREF), Literal(c.xref)))
    for key, v in registry.items():
        subject = URIRef(v.uri)
        model.add((subject, RDF.type, ns.AnnotatedVariable))
        model.add((subject, RDFS.label, Literal(v.name)))
        model.add((subject, ns.anatomy, URIRef(v.anatomy.uri)))
        model.add((subject, ns.physicalProperty, URIRef(v.property.uri)))
        for predicate, value in [('unit', v.unit), ('equation', v.equation), ('role', v.role),
                                  ('sourceContext', v.source_context), ('temporalContext', v.temporal_context),
                                  ('reference', v.reference), ('bearerKind', v.bearer)]:
            model.add((subject, ns[predicate], Literal(value)))
        model.add((subject, DCTERMS.source, Literal(v.source_document)))
        for context in v.applicable_contexts:
            model.add((subject, ns.applicableScenario, URIRef(BASE + 'scenario/' + context)))
        for c in filter(None, (v.anatomy, v.property, v.occurs_in)):
            if c.uri not in verified:
                model.add((URIRef(c.uri), RDFS.label, Literal(c.label)))
                model.add((URIRef(c.uri), ns.mappingStatus, Literal('local extension' if c.local else 'unverified caller concept')))
        bearer = URIRef(BASE + 'bearer/' + key)
        if v.flow_path:
            bearer = URIRef(BASE + v.flow_path['id'].replace(':', '/'))
            for context in v.flow_path['traverses']:
                target = URIRef(BASE + 'anatomy-context/' + context['key'])
                model.add((bearer, ns.traverses, target))
                model.add((target, ns.anatomyKey, Literal(context['key'])))
                model.add((target, ns.mappingStatus, Literal(context['status'])))
                if context['note']:
                    model.add((target, ns.usageNote, Literal(context['note'])))
        model.add((subject, ns.propertyOf, bearer))
        if v.bearer == 'blood' and not v.anatomy.local:
            # C5 bearer form: the portion of blood is part of its cavity or lumen.
            model.add((bearer, URIRef(BQBIOL + 'isPartOf'), URIRef(v.anatomy.uri)))
        else:
            # Non-blood bearers and local compartments keep the project relation (no lumen mapping decided).
            model.add((bearer, ns.locatedIn, URIRef(v.anatomy.uri)))
        if v.bearer == 'blood':
            model.add((bearer, ns.entityType, URIRef(BLOOD.uri)))
        if v.occurs_in:
            model.add((bearer, URIRef(BQBIOL + 'occursIn'), URIRef(v.occurs_in.uri)))
        if v.orientation:
            model.add((subject, ns.flowSource, URIRef(ANATOMY[v.orientation[0]].uri)))
            model.add((subject, ns.flowSink, URIRef(ANATOMY[v.orientation[1]].uri)))
        for dependency in v.depends_on:
            model.add((subject, ns.dependsOn, URIRef(BASE + 'variable/' + dependency)))
        for context in v.biological_context:
            model.add((subject, ns.processContext, URIRef(CONTEXTS[context].uri)))
    # Disease concepts are vocabulary context only: no assertion of disease in baseline.
    provenance.add((URIRef(CONTEXTS['heart_failure'].uri), ns.usageNote,
                    Literal('Disease context vocabulary only; does not diagnose simulated baseline')))
    return ds


def export_graph(registry=None, *, format='trig') -> str:
    """Serialize named graphs; reject flattening formats that would lose provenance."""
    if format not in {'trig', 'nquads'}:
        raise ValueError('Use trig or nquads to preserve assertion/source separation')
    return build_graph(registry).serialize(format=format)
