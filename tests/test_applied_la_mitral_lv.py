"""Small synthetic, contract and mutation checks for the isolated sidecar."""
import copy
import importlib.util
import json
from pathlib import Path
import pytest


def test_physiosim_imports_from_this_worktree():
    import physiosim

    workspace_src = Path(__file__).resolve().parents[1] / 'src'
    actual = Path(physiosim.__file__).resolve()
    assert actual.is_relative_to(workspace_src), (
        f'physiosim imported from {actual}; expected this worktree under '
        f'{workspace_src}. Run pytest with PYTHONPATH={workspace_src}'
    )


def test_module_importable():
    assert importlib.util.find_spec('physiosim.ontology.applied_la_mitral_lv') is not None


def test_slice_loads_pinned_revision_and_digests():
    from physiosim.ontology import applied_la_mitral_lv as a
    s = a.load_source_slice()
    assert s['source_commit'] == '70784bcdb9c14fba5271ee73f3c62b5f94ccbcfb'
    assert len(s['catalog']) == 14 and len(s['claims']) == 12
    assert len(s['boundaries']['proposals']) == 2
    assert all(a.digest(s[k]) == v for k, v in a.PINNED_SUBSETS.items())
    assert s['null_context_keys'] == ['heart/organ', 'heart/mitral_orifice']
    assert s['absent_claims'] == []


def test_slice_rejects_tampered_record_with_rewritten_receipt(tmp_path):
    from physiosim.ontology import applied_la_mitral_lv as a
    s = a.load_source_slice()
    s['catalog'][0]['record']['base_id'] = 'UBERON:0000178'
    s['subset_sha256']['catalog'] = a.digest(s['catalog'])
    p = tmp_path/'forged.json'; p.write_text(json.dumps(s))
    with pytest.raises(ValueError, match='integrity'):
        a.load_source_slice(p)


def test_slice_rejects_wrong_revision_observation_duplicate_missing_context():
    from physiosim.ontology import applied_la_mitral_lv as a
    source = a.load_source_slice()
    a.validate_source_slice(source)
    mutations = [lambda s: s.update(source_commit='unknown'),
        lambda s: s['catalog'].append(copy.deepcopy(s['catalog'][0])),
        lambda s: s['claims'].append(copy.deepcopy(s['claims'][0])),
        lambda s: s['catalog'][4]['record'].update(context=None),
        lambda s: s['catalog'][4]['record'].update(observed_in_CT=True),
        lambda s: s.update(observations=[]),
        lambda s: s['boundaries']['proposals'][0]['record'].update(patient_geometry_status='MEASURED')]
    for mutate in mutations:
        s = copy.deepcopy(source); mutate(s)
        with pytest.raises(ValueError): a.validate_source_slice(s)


def test_crosswalk_keeps_located_in_c5_m1_relations_distinct():
    from physiosim.ontology import applied_la_mitral_lv as a
    s = a.build_applied_sidecar()
    a.validate_applied_sidecar(s)
    for c in ('la','lv'):
        x = s['crosswalk'][c+'_blood']
        assert x['source_relation']['iri'].endswith('RO_0001025')
        assert x['source_relation']['direction'] == [x['source_template'], x['source_context']]
        assert x['target_c5']['relation'] == 'part_of' and x['target_c5']['applied'] is False
        assert x['m1_relation']['relation'] == 'blood_contained_in'
        assert x['equivalence'] == 'NONE'
    bad = copy.deepcopy(s); bad['crosswalk']['la_blood']['source_relation']['iri'] = 'part_of'
    with pytest.raises(ValueError): a.validate_applied_sidecar(bad)


def test_la_lv_contexts_and_role_assignments_reject_nonblood_bearers():
    from physiosim.ontology import applied_la_mitral_lv as a
    s = a.build_applied_sidecar()
    assert s['anatomy_roles']['V_la']['template'] == 'la_blood'
    assert s['anatomy_roles']['V_lv']['template'] == 'lv_blood'
    for c in ('la','lv'):
        assert s['anatomy_roles'][c+'_cavity']['role'] == 'SPATIAL_CONTEXT'
        for suffix in ('wall','myocardium'):
            assert s['anatomy_roles'][c+'_'+suffix]['role'] == 'MECHANICAL_CONTEXT_CANDIDATE'
    assert s['crosswalk']['la_blood']['source_id'] == s['crosswalk']['lv_blood']['source_id']
    assert s['crosswalk']['la_blood']['source_template'] != s['crosswalk']['lv_blood']['source_template']
    for template in ('la_blood','lv','lv_cavity','lv_wall','organ','UBERON:0000178','aorta'):
        b = copy.deepcopy(s); b['anatomy_roles']['V_lv']['template'] = template
        with pytest.raises(ValueError): a.validate_applied_sidecar(b)
    b = copy.deepcopy(s); b['crosswalk']['la_blood']['source_context'] = s['crosswalk']['lv_blood']['source_context']
    with pytest.raises(ValueError): a.validate_applied_sidecar(b)
    b = copy.deepcopy(s); b['anatomy_roles']['sa'] = {'template':'aorta'}
    with pytest.raises(ValueError): a.validate_applied_sidecar(b)


def test_mitral_valve_orifice_annulus_interface_distinct_with_diode_limitation():
    from physiosim.ontology import applied_la_mitral_lv as a
    s = a.build_applied_sidecar(); m = s['mitral']
    assert len({m[k]['role'] for k in ('valve','orifice','annulus','interface')}) == 4
    assert m['effective_orifice_area'] == 'NOT_REPRESENTED'
    assert m['interface']['status'] == 'DRAFT_MODEL_CONVENTION'
    assert m['interface']['signed_flow_allowed'] is True and m['direction'] == ['la','lv']
    assert 'no-reverse-flow' in m['restriction'] and 'regurgitation' in m['restriction']
    assert m['orifice']['boundary_review'] == 'REVIEW' and m['annulus']['definition_review'] == 'REVISE'
    for key in ('valve','orifice','annulus','interface'):
        for equivalence in ('EOA','mitral_valve','owl:sameAs','equivalentClass'):
            b = copy.deepcopy(s); b['mitral'][key]['equivalence'] = equivalence
            with pytest.raises(ValueError): a.validate_applied_sidecar(b)


def test_symbols_parameters_units_reference_temporal_direction_match_m1():
    from physiosim.ontology import applied_la_mitral_lv as a
    from physiosim.ontology.four_chamber_m1_manifest import build_m1_manifest
    s = a.build_applied_sidecar(); m = build_m1_manifest()
    assert set(s['variables']) == {'V_la','V_lv','P_la','P_lv','Q_mitral','Q_cum_mitral',
        'lv_edv_sample_ml','lv_esv_sample_ml','lv_ejection_fraction_sample','la_pressure_mean_mmhg'}
    for name, variable in s['variables'].items(): assert variable == m['variables'][name]
    assert s['roles']['V_lv']['kind'] == 'state'
    assert s['roles']['P_la']['kind'] == 'algebraic_observable'
    assert s['roles']['Q_cum_mitral']['kind'] == 'auxiliary_integral'
    assert s['roles']['lv_edv_sample_ml']['kind'] == 'metric'
    assert s['ports']['mitral_flow_port']['ref'] == 'Q_mitral'
    assert s['ports']['mitral_flow_port']['kind'] == 'port'
    for name, parameter in s['parameters'].items(): assert parameter == m['parameter_contract'][name]
    assert set(s['parameters']) == {'elastance_la','emin_lv','emax_lv','resistance_mitral',
        'unstressed_volumes','initial_volumes','heart_rate','systolic_fraction'}
    assert s['volume_references']['V0_la']['index'] == 7 and s['volume_references']['V0_lv']['index'] == 0
    mutations = [('V_lv','unit','L'),('P_la','reference','absolute'),('Q_mitral','direction',['lv','la']),
        ('Q_cum_mitral','temporal','instantaneous'),('P_lv','kind','state'),('V_la','compartment','lv')]
    for name, field, value in mutations:
        b = copy.deepcopy(s); b['variables'][name][field] = value
        with pytest.raises(ValueError): a.validate_applied_sidecar(b)
    for field, value in [('model_version','2.0.0'),('model_id','other')]:
        b = copy.deepcopy(s); b[field] = value
        with pytest.raises(ValueError): a.validate_applied_sidecar(b)
    for name in ('SV_lv','CO_lv','Q_aortic'):
        b = copy.deepcopy(s); b['variables'][name] = m['variables'][name]
        with pytest.raises(ValueError): a.validate_applied_sidecar(b)
    b = copy.deepcopy(s); b['parameters']['resistance_mitral']['unit'] = 'mmHg/mL'
    with pytest.raises(ValueError): a.validate_applied_sidecar(b)


def test_activation_law_doc_anchored_not_manifest_variable():
    from physiosim.ontology import applied_la_mitral_lv as a
    s = a.build_applied_sidecar()
    assert 'E_lv(t)' not in s['variables']
    assert s['laws']['E_lv(t)']['kind'] == 'constitutive_law'
    assert s['laws']['activation']['inputs'] == ['heart_rate','systolic_fraction']
    root = Path(__file__).resolve().parents[1]
    for law in s['laws'].values():
        assert law['anchor'] in (root/law['path']).read_text()
        assert law['source_sha256'] == a.sha256((root/law['path']).read_bytes()).hexdigest()
    assert {d['kind'] for d in s['dependencies']} == {'constitutive','conservation','definition'}
    assert all(d['kind'] != 'value_equivalence' for d in s['dependencies'])
    b = copy.deepcopy(s); b['laws']['E_lv(t)']['anchor'] = 'invented equation'
    with pytest.raises(ValueError): a.validate_applied_sidecar(b)
    b = copy.deepcopy(s); b['dependencies'][0]['kind'] = 'value_equivalence'
    with pytest.raises(ValueError): a.validate_applied_sidecar(b)


def test_status_axes_independent_never_promoted():
    from physiosim.ontology import applied_la_mitral_lv as a
    s = a.build_applied_sidecar(); axes = s['status_axes']
    assert axes['target_crosswalk_review'] == 'PROPOSED'
    assert axes['external_numeric_permission'] == 'NONE'
    assert {v['decision'] for v in axes['source_claims'].values()} == {'ACCEPT','REVIEW'}
    assert all(v['expert_review_status'] == 'NOT_INDEPENDENTLY_EXPERT_REVIEWED' for v in axes['source_claims'].values())
    assert axes['special_reviews']['mitral_orifice_boundary_equivalence'] == 'REVIEW'
    assert axes['special_reviews']['mitral_annulus_complete_fibrous_ring_interpretation'] == 'REVISE'
    assert s['evidence']['verbatim_evidence'] and s['evidence']['extracted_facts']
    assert s['evidence']['interpretations'] and s['evidence']['unresolved_conflicts']
    for field, value in [('target_crosswalk_review','OWNER_APPROVED'),('external_numeric_permission','APPROVED_FOR_BINDING')]:
        b = copy.deepcopy(s); b['status_axes'][field] = value
        with pytest.raises(ValueError): a.validate_applied_sidecar(b)
    b = copy.deepcopy(s); b['crosswalk']['mitral_orifice']['crosswalk_review'] = 'OWNER_APPROVED'
    with pytest.raises(ValueError): a.validate_applied_sidecar(b)
    b = copy.deepcopy(s); b['source']['claims'][0]['record']['expert_review_status'] = 'EXPERT_APPROVED'
    with pytest.raises(ValueError): a.validate_applied_sidecar(b)


def test_numeric_binding_gate_closed_and_request_rejected():
    from physiosim.ontology import applied_la_mitral_lv as a
    s = a.build_applied_sidecar(); report = a.gate_report(s)
    assert report['G1']['status'] == 'PASS'
    assert report['G2']['executed'] is False
    assert report['G3'] == {'status':'CLOSED','external_numeric_permission':'NONE'}
    assert report['status_axes'] == s['status_axes']
    for request in ({}, {'source_decision':'ACCEPT'}, {'owner_approved':True}, {'value':1.0,'unit':'mL'}):
        with pytest.raises(PermissionError, match='CLOSED'): a.request_numeric_binding(**request)
    bad = copy.deepcopy(s); bad['crosswalk']['lv_blood']['numeric_use'] = 'ACCEPT'
    with pytest.raises(ValueError): a.gate_report(bad)


def test_m1_manifest_and_arrays_unchanged_second_run():
    from physiosim.ontology import applied_la_mitral_lv as a
    from physiosim.experiments import applied_la_mitral_lv_demo as demo
    from physiosim.experiments.four_chamber_m1_demo import synthetic_fixture
    from physiosim.simulation.four_chamber_m1 import simulate_m1, SolverSettings
    from physiosim.ontology.four_chamber_m1_manifest import build_m1_manifest
    import numpy as np
    p = synthetic_fixture(); settings = SolverSettings(max_step=p.period/200)
    manifest = build_m1_manifest(); before = copy.deepcopy(manifest)
    first = simulate_m1(p, cycles=2, samples_per_cycle=50, settings=settings)
    original = demo.result_fingerprint(first)
    s = a.build_applied_sidecar(); a.validate_applied_sidecar(s)
    second = simulate_m1(p, cycles=2, samples_per_cycle=50, settings=settings)
    assert original == demo.result_fingerprint(first) == demo.result_fingerprint(second)
    for name in ('time','volumes','pressures','flows','cumulative_flows'):
        assert np.array_equal(getattr(first,name), getattr(second,name))
    assert manifest == before == build_m1_manifest()
    assert len(original['array_sha256']) == 5 and original['config']['cycles'] == 2


def test_demo_private_deterministic_and_refuses_nonempty(tmp_path):
    from physiosim.experiments import applied_la_mitral_lv_demo as demo
    from physiosim.ontology import applied_la_mitral_lv as a
    import csv
    import os
    one, two = tmp_path/'one', tmp_path/'two'
    old_umask = os.umask(0o022); os.umask(old_umask)
    demo.run_applied_demo(one); demo.run_applied_demo(two)
    actual_umask = os.umask(old_umask); assert actual_umask == old_umask
    files = {'applied_sidecar.json','gate_report.json','source_receipt.json','trace_la_mitral_lv.csv','index.html','run_receipt.json'}
    assert {p.name for p in one.iterdir()} == files
    assert one.stat().st_mode & 0o777 == 0o700
    for name in files:
        assert (one/name).read_bytes() == (two/name).read_bytes()
        assert (one/name).stat().st_mode & 0o777 == 0o600
    receipt = json.loads((one/'run_receipt.json').read_text())
    assert receipt['invariance']['before'] == receipt['invariance']['after']
    assert receipt['manifest_before_sha256'] == receipt['manifest_after_sha256']
    assert set(receipt['output_sha256']) == files-{'run_receipt.json'}
    for name, value in receipt['output_sha256'].items(): assert value == a.sha256((one/name).read_bytes()).hexdigest()
    report = json.loads((one/'gate_report.json').read_text())
    assert report['G3']['status'] == 'CLOSED' and report['G2']['executed'] is True
    rows = list(csv.DictReader((one/'trace_la_mitral_lv.csv').open()))
    assert len(rows) == 101 and float(rows[-1]['Qcum_mitral_ml']) > 0
    html = (one/'index.html').read_text()
    assert 'SYNTHETIC' in html and 'CLOSED' in html and '<svg' in html
    assert 'approved' not in html.lower() and '<script' not in html and 'https://' not in html
    saved = {p.name:p.read_bytes() for p in one.iterdir()}
    with pytest.raises(ValueError): demo.run_applied_demo(one)
    assert saved == {p.name:p.read_bytes() for p in one.iterdir()}
    link = tmp_path/'link'; link.symlink_to(two, target_is_directory=True)
    with pytest.raises(ValueError): demo.run_applied_demo(link)
    with pytest.raises(ValueError): demo.run_applied_demo(link/'nested')
    empty = tmp_path/'empty'; empty.mkdir(); demo.run_applied_demo(empty)


def test_cli_main_requires_output_and_runs_workspace_script(tmp_path, capsys):
    from physiosim.experiments import applied_la_mitral_lv_demo as demo
    import os
    import subprocess
    import sys
    with pytest.raises(SystemExit) as missing: demo.main([])
    assert missing.value.code == 2
    capsys.readouterr()
    root = Path(__file__).resolve().parents[1]
    output = tmp_path/'cli'
    command = [sys.executable, str(root/'scripts/run_applied_la_mitral_lv.py'), '--output', str(output)]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(root/'src'))
    run = subprocess.run(command, env=env, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    assert json.loads(run.stdout)['status'] == 'pass'
    assert (output/'index.html').is_file()
    again = subprocess.run(command, env=env, capture_output=True, text=True)
    assert again.returncode != 0 and json.loads(again.stdout)['status'] == 'blocked'


def test_law_port_parameter_time_metadata_explicit_and_closed():
    from physiosim.ontology import applied_la_mitral_lv as a
    s = a.build_applied_sidecar()
    assert s['time_contract'] == {'unit':'s','reference':'elapsed from synthetic run start',
        'origin':0,'phase':'phi=(t mod T)/T; T=60/heart_rate s','aggregation':'per manifest variable'}
    expected_units = {'activation':'dimensionless','E_lv(t)':'mmHg/mL','P_la':'mmHg',
        'P_lv':'mmHg','Q_mitral':'mL/s','Q_cum_mitral':'mL'}
    for name, unit in expected_units.items():
        law = s['laws'][name]
        assert law['unit'] == unit and law['temporal'] == ('run_integrated' if name == 'Q_cum_mitral' else 'instantaneous')
        assert law['reference'] and law['sign'] and law['aggregation']
    port = s['ports']['mitral_flow_port']
    assert port['unit'] == 'mL/s' and port['temporal'] == 'instantaneous'
    assert all(s['parameter_roles'][name]['kind'] == 'parameter' for name in s['parameters'])
    assert s['target_anatomy_source']['ontology_versions']
    for field in ('laws','ports','time_contract','parameter_roles','target_anatomy_source'):
        bad = copy.deepcopy(s); bad[field]['unexpected'] = 'external value equivalence'
        with pytest.raises(ValueError): a.validate_applied_sidecar(bad)
