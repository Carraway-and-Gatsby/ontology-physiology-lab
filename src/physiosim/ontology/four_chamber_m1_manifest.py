"""Offline, model-specific M1 contract. No changes to the legacy registry.

Identifier checks establish consistency with the project-owned v2 file, not
fresh external ontology/source validation or anatomical equivalence.
"""
from dataclasses import fields
from hashlib import sha256
import json
from importlib.resources import files
from pathlib import Path
from physiosim.models.four_chamber_m1 import (
    MODEL_ID, MODEL_VERSION, PRESSURE_REFERENCE, COMPARTMENTS, EDGES, FourChamberM1Parameters,
)
from . import PROPERTIES, BASE

SOURCE_PATH = 'docs/evidence_review/anatomy_nodes_v2.json'
_CAVITIES = {'lv':'lv_cavity','rv':'rv_cavity','la':'la_cavity','ra':'ra_cavity'}
_VESSELS = {'sa':'systemic_arterial_lumen','sv':'systemic_venous_lumen',
            'pa':'pulmonary_arterial_lumen','pv':'pulmonary_venous_lumen'}
_VALVES = {'aortic':'aortic_valve','mitral':'mitral_valve',
           'tricuspid':'tricuspid_valve','pulmonary_valve':'pulmonary_valve'}


def load_anatomy_v2(path=None):
    """Bundled project resource or explicit local path; no network fallback."""
    path = Path(path) if path is not None else files("physiosim.ontology").joinpath("anatomy_nodes_v2.json")
    document=json.loads(path.read_text())
    keys=[n['key'] for n in document['nodes']]
    if len(keys)!=len(set(keys)) or not document.get('ontology_versions'):
        raise ValueError('invalid v2 node specification')
    return document


def _digest(document):
    return sha256(json.dumps(document,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def build_m1_manifest(nodes=None):
    nodes=load_anatomy_v2() if nodes is None else nodes
    lookup={n['key']:n for n in nodes['nodes']}
    source={'path':SOURCE_PATH,'version':nodes['title'],
            'ontology_versions':nodes['ontology_versions'],'canonical_json_sha256':_digest(nodes),
            'validation_scope':'Checked against project-owned v2; no new external source validation.'}

    def anatomy(key):
        n=lookup[key]
        return {'key':key,'primary_id':n['uberon'] if n['primary']=='UBERON' else n['fma'],
                'uberon':n['uberon'],'fma':n['fma'],'structure':n['structure'],
                'uberon_relation':'same_structure_v2_xref' if n['primary']=='UBERON' else 'related_structure',
                'provenance':SOURCE_PATH+'#/nodes/'+str(nodes['nodes'].index(n)),
                'source_role_in_smith':n['role_in_smith']}

    compartments={}
    for c in COMPARTMENTS:
        chamber=c in _CAVITIES
        compartments[c]={'anatomy':anatomy((_CAVITIES if chamber else _VESSELS)[c]),
            'relation':'blood_contained_in' if chamber else 'lumped_compartment_context',
            'relationship_direction':['modelled_blood', 'anatomical_container' if chamber else 'anatomical_context'],
            'interpretation':'Separate M1 blood volume state.' if chamber else
                'Anatomical context only; the lumen label is not identity with the whole lumped vascular bed.'}
    edges={}
    for e in EDGES:
        edges[e.name]={'source':e.source,'target':e.target,'kind':e.kind,
            'anatomy':anatomy(_VALVES[e.name]) if e.name in _VALVES else None,
            'relation':'flow_location' if e.name in _VALVES else 'project_local_flow_path',
            'relationship_direction':['flow_process','valve_location'] if e.name in _VALVES else [e.source,e.target],
            'interpretation':'Model flow located at v2 valve.' if e.name in _VALVES else
                'No dedicated v2 path node; project-local connection between the named compartments.'}
    variables={}

    def add(name,prop,unit,kind,temporal='instantaneous',direction=None,compartment=None,edge=None):
        concept=PROPERTIES[prop]
        variables[name]={'property':concept.uri,'property_source':concept.source,'unit':unit,'kind':kind,
            'temporal':temporal,'direction':direction,'compartment':compartment,'edge':edge,
            'bearer':'flow_process' if direction else 'blood',
            'reference':PRESSURE_REFERENCE if prop=='pressure' else 'not applicable',
            'provenance':'docs/physiology_four_chamber_m1.md#equations-and-contract'}

    for c in COMPARTMENTS:
        add('V_'+c,'volume','mL','volume',compartment=c)
        add('P_'+c,'pressure','mmHg','chamber_pressure' if c in _CAVITIES else 'compartment_pressure',compartment=c)
    for e in EDGES:
        add('Q_'+e.name,'flow','mL/s','flow',direction=[e.source,e.target],edge=e.name)
        add('Q_cum_'+e.name,'volume','mL','cumulative_transported_volume','run_integrated',
            direction=[e.source,e.target],edge=e.name)
    for c,e in [('lv','aortic'),('rv','pulmonary_valve')]:
        direction=[edges[e]['source'],edges[e]['target']]
        add('SV_'+c,'volume','mL','forward_stroke_volume','beat_integrated',direction,c,e)
        add('CO_'+c,'flow','mL/s','cardiac_output','beat_mean',direction,c,e)
        add(c+'_cardiac_output_l_min','flow','L/min','cardiac_output','beat_mean',direction,c,e)
        for suffix in ['edv_sample_ml','esv_sample_ml']:
            add(c+'_'+suffix,'volume','mL','sampled_volume_extremum','beat_sample_extremum',compartment=c)
        variables[c+'_ejection_fraction_sample']={
            'property':BASE+'concept/volume_excursion_fraction','property_source':'project-local M1 definition',
            'unit':'dimensionless','kind':'sampled_volume_excursion_fraction','temporal':'beat_sample_extremum',
            'direction':None,'compartment':c,'edge':None,'bearer':'blood','reference':'not applicable',
            'provenance':'docs/physiology_four_chamber_m1.md#equations-and-contract'}
    for c in ('la','ra','sa','pa'):
        for stat in ['min','max','mean']:
            temporal='beat_mean' if stat=='mean' else 'beat_sample_extremum'
            add(c+'_pressure_'+stat+'_mmhg','pressure','mmHg','pressure_summary',temporal,compartment=c)
            if c in ('la','ra'):
                add(c+'_volume_'+stat+'_ml','volume','mL','volume_summary',temporal,compartment=c)
    parameters={}
    for field in fields(FourChamberM1Parameters):
        name=field.name
        if name.endswith('volumes'):
            unit='mL'; prop='volume'
        elif name.startswith('resistance_'):
            unit='mmHg*s/mL'; prop='resistance'
        elif name.startswith('compliance_'):
            unit='mL/mmHg'; prop='compliance'
        elif name=='heart_rate':
            unit='1/min'; prop='frequency'
        elif name=='systolic_fraction':
            unit='dimensionless'; prop=None
        else:
            unit='mmHg/mL'; prop='elastance'
        parameters[name]={'unit':unit,'property':PROPERTIES[prop].uri if prop else BASE+'concept/systolic_fraction',
            'property_source':PROPERTIES[prop].source if prop else 'project-local M1 definition',
            'provenance':'Required explicit caller input; no literature-derived default or calibration.',
            'temporal':'initial' if name=='initial_volumes' else 'constant_parameter',
            'order':list(COMPARTMENTS) if name.endswith('volumes') else None}
    return {'model_id':MODEL_ID,'model_version':MODEL_VERSION,'pressure_reference':PRESSURE_REFERENCE,
        'source':source,'compartments':compartments,'edges':edges,'variables':variables,
        'parameter_contract':parameters,
        'metric_aliases':{**{c+'_stroke_volume_ml':'SV_'+c for c in ('lv','rv')},
                          **{c+'_cardiac_output_ml_s':'CO_'+c for c in ('lv','rv')}},
        'evidence_status':{'verbatim_evidence':'Not reproduced here; see v2 source pointers.',
            'extracted_facts':'Identifiers, labels and Smith roles copied from project-owned v2.',
            'interpretation':'M1 topology, gauge and mappings are software design assertions, not ontology entailments.'},
        'unresolved_conflicts':[
            'v2 la_cavity/ra_cavity roles describe Smith lumped venous blood; M1 uses separate states. No legacy identity or volume split is asserted.',
            'v2 pulmonary_venous_lumen records UBERON:0013127 as related structure with no FMA xref; FMA:52455 is the primary lumen identifier.']}


def validate_m1_manifest(manifest,nodes=None):
    """Reject any change to M1 endpoints, source IDs, roles or variable contract.

    A focused closed contract intentionally accepts no ad-hoc alternate mapping.
    Exact units remain fixed because the exported numeric fields have no
    automatic unit conversion.
    """
    expected=build_m1_manifest(nodes)
    if not isinstance(manifest,dict): raise ValueError('manifest must be an object')
    try:
        for field,value in expected.items():
            if manifest.get(field)!=value:
                raise ValueError('M1 semantic contract mismatch: '+field)
        if set(manifest)!=set(expected): raise ValueError('unexpected manifest fields')
    except (KeyError,TypeError) as error:
        raise ValueError('invalid M1 semantic contract') from error
    return None
