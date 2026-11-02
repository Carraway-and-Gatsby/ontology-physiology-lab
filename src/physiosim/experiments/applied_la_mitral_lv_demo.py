"""Private, deterministic artifacts for an existing synthetic M1 invocation."""
from dataclasses import asdict
from hashlib import sha256
import numpy as np


def result_fingerprint(result):
    """Hash complete arrays with shape/dtype, and preserve the invocation config."""
    names = ('time','volumes','pressures','flows','cumulative_flows')
    arrays = {name: np.ascontiguousarray(getattr(result, name)) for name in names}
    return {'array_sha256': {name: sha256(value.tobytes()).hexdigest() for name,value in arrays.items()},
        'array_layout': {name: {'shape': list(value.shape), 'dtype': value.dtype.str} for name,value in arrays.items()},
        'config': {'parameters': asdict(result.parameters), 'settings': asdict(result.settings),
                   'cycles': result.cycles, 'samples_per_cycle': result.samples_per_cycle}}


import csv
from html import escape
from io import StringIO
import json
import os
from pathlib import Path
from physiosim.experiments.four_chamber_m1_demo import synthetic_fixture, FIXTURE_PROVENANCE
from physiosim.simulation.four_chamber_m1 import simulate_m1, SolverSettings
from physiosim.ontology.four_chamber_m1_manifest import build_m1_manifest
from physiosim.ontology.applied_la_mitral_lv import (
    build_applied_sidecar, gate_report, digest, PINNED_DOCUMENT,
)


def _json(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()


def _output_directory(output):
    path = Path(output).absolute()
    if path.is_symlink():
        raise ValueError('output final component must not be a symlink')
    if path.exists():
        if not path.is_dir() or any(path.iterdir()):
            raise ValueError('output must be a new or empty directory')
    else:
        path.mkdir(mode=0o700, parents=True)
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    os.fchmod(fd, 0o700)
    return fd


def _html(sidecar, rows):
    last = rows[-1]
    headings = ('time_s','V_la_ml','V_lv_ml','P_la_mmhg','P_lv_mmhg','Q_mitral_ml_s','Qcum_mitral_ml')
    table = ''.join('<tr><th>'+escape(key)+'</th><td>'+format(value,'.9g')+'</td></tr>'
                    for key,value in zip(headings,last))
    claims = ''.join('<tr><td>'+escape(x['record']['claim_id'])+'</td><td>'+
        escape(x['record']['sourceTemplate'].split('#')[-1]+' → '+x['record']['targetTemplate'].split('#')[-1])+
        '</td><td>'+escape(x['record']['decision'])+'</td><td>'+
        escape(x['record']['original_relation_status'].split('#')[-1])+'</td><td>'+
        escape(x['record']['expert_review_status'])+'</td></tr>' for x in sidecar['source']['claims'])
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><title>SYNTHETIC LA–mitral–LV</title>'
        '<style>body{font:16px system-ui;margin:2rem;max-width:1100px}svg{width:100%;height:auto}table{border-collapse:collapse}td,th{padding:.4rem;border:1px solid #bbb;text-align:left}</style>'
        '<h1>SYNTHETIC LA → mitral → LV</h1><p>Metadata only · four_chamber_m1@1.0.0 · Crosswalk PROPOSED · Numerical binding gate CLOSED (permission NONE).</p>'
        '<svg viewBox="0 0 1000 220" role="img" aria-label="LA blood in cavity, mitral flow, LV blood in cavity; wall and myocardium are unselected mechanical context candidates">'
        '<rect x="5" y="10" width="280" height="110" fill="#e0f1fa" stroke="#333"/><text x="20" y="40">LA blood template: V_la [mL]</text>'
        '<text x="20" y="70">la_cavity: spatial context</text><text x="20" y="100">P_la [mmHg] algebraic</text>'
        '<path d="M290 60H690l-12 -8m12 8l-12 8" fill="none" stroke="#333"/><text x="315" y="45">Q_mitral [mL/s], LA → LV</text>'
        '<text x="305" y="95">Q_cum_mitral [mL], run-integrated</text>'
        '<rect x="705" y="10" width="290" height="110" fill="#ffe5dc" stroke="#333"/><text x="720" y="40">LV blood template: V_lv [mL]</text>'
        '<text x="720" y="70">lv_cavity: spatial context</text><text x="720" y="100">P_lv [mmHg] algebraic</text>'
        '<text x="10" y="155">LA/LV wall + myocardium: mechanical context candidates; no selected bearer</text>'
        '<text x="10" y="185">E_lv(t): constitutive law reference; E_la constant · no area or resistance inferred</text></svg>'
        '<p>Valve: structure; orifice: opening / boundary REVIEW; annulus: attachment / definition REVISE; interface: DRAFT_MODEL_CONVENTION. Effective orifice area NOT_REPRESENTED.</p>'
        '<p>'+escape(sidecar['mitral']['restriction'])+'</p>'
        '<p>Common pressure gauge: '+escape(sidecar['variables']['P_la']['reference'])+'. Time in s; total blood volume in mL. No patient data. No clinical, anatomical or physiological validation. Fixed cycles do not establish steady state.</p>'
        '<h2>Actual final synthetic sample</h2><table>'+table+'</table>'
        '<h2>Source relation statuses (independent from mapping and numerical permission)</h2><table><tr><th>Claim</th><th>Direction</th><th>Decision</th><th>Original relation status</th><th>Expert review</th></tr>'+claims+'</table>'
        '<p>Source revision '+escape(sidecar['source']['source_commit'])+'. All source roles are knowledge templates.</p>'
        '<p>Unresolved: C5 adapter, mechanical bearer, mitral boundaries, LA v2 Smith role, inherited M1 batch-TDD review limitation (UNREVIEWED).</p>'
        '<p><a href="applied_sidecar.json">Sidecar and exact source locations</a> · <a href="gate_report.json">Gates</a> · <a href="source_receipt.json">Source receipt and third-party notice</a> · <a href="trace_la_mitral_lv.csv">Synthetic trace</a> · <a href="run_receipt.json">Invariance receipt</a></p></html>')


def run_applied_demo(output):
    """Execute two identical short synthetic runs, then write exclusive private files.

    The receipt excludes itself from output checksums. No external values enter M1.
    """
    previous_umask = os.umask(0o077)
    directory_fd = None
    try:
        directory_fd = _output_directory(output)
        parameters = synthetic_fixture()
        settings = SolverSettings(max_step=parameters.period/200)
        invocation = {'cycles': 2, 'samples_per_cycle': 50, 'settings': settings}
        manifest_before = digest(build_m1_manifest())
        first = simulate_m1(parameters, **invocation)
        before = result_fingerprint(first)
        sidecar = build_applied_sidecar()
        report = gate_report(sidecar)
        second = simulate_m1(parameters, **invocation)
        after = result_fingerprint(second)
        manifest_after = digest(build_m1_manifest())
        if before != result_fingerprint(first) or before != after or manifest_before != manifest_after:
            raise RuntimeError('sidecar numerical or manifest invariance failed')
        report['G2'] = {'status': 'PASS', 'executed': True,
                        'scope': 'Two identical existing synthetic M1 invocations; exact array/config hashes match.'}
        la, lv = (first.compartment_names.index(c) for c in ('la','lv'))
        mitral = first.edge_names.index('mitral')
        rows = np.column_stack((first.time, first.volumes[:,la], first.volumes[:,lv],
            first.pressures[:,la], first.pressures[:,lv], first.flows[:,mitral], first.cumulative_flows[:,mitral]))
        stream = StringIO(newline='')
        writer = csv.writer(stream, lineterminator='\n')
        writer.writerow(('time_s','V_la_ml','V_lv_ml','P_la_mmhg','P_lv_mmhg','Q_mitral_ml_s','Qcum_mitral_ml'))
        writer.writerows(rows)
        source = sidecar['source']
        source_receipt = {k: source[k] for k in ('source_repo','source_commit','full_files','subset_sha256','third_party_notice','roles')}
        source_receipt['canonical_document_sha256'] = PINNED_DOCUMENT
        source_receipt['trust_boundary'] = 'Expected complete-document, subset and full-file hashes are pinned independently in the Python module. Receipt hashes do not authorize binding.'
        payloads = {'applied_sidecar.json': _json(sidecar), 'gate_report.json': _json(report),
            'source_receipt.json': _json(source_receipt), 'trace_la_mitral_lv.csv': stream.getvalue().encode(),
            'index.html': _html(sidecar, rows).encode()}
        receipt = {'synthetic': True, 'fixture_provenance': FIXTURE_PROVENANCE,
            'invariance': {'before': before, 'after': after},
            'manifest_before_sha256': manifest_before, 'manifest_after_sha256': manifest_after,
            'output_sha256': {name: sha256(blob).hexdigest() for name,blob in payloads.items()},
            'checksum_scope': 'All listed output files; run_receipt.json is explicitly excluded from its own checksums.',
            'external_numeric_binding': 'CLOSED', 'inherited_m1_review': 'UNREVIEWED; batch-TDD limitation unresolved'}
        payloads['run_receipt.json'] = _json(receipt)
        for name, blob in payloads.items():
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
            with os.fdopen(os.open(name, flags, 0o600, dir_fd=directory_fd), 'wb') as handle:
                handle.write(blob)
        return receipt
    finally:
        if directory_fd is not None: os.close(directory_fd)
        os.umask(previous_umask)


def main(argv=None):
    """Required-output CLI; results are a router-compatible JSON envelope."""
    import argparse
    parser = argparse.ArgumentParser(description='Private synthetic LA–mitral–LV metadata demo')
    parser.add_argument('--output', required=True, type=Path, help='New or empty private directory')
    arguments = parser.parse_args(argv)
    try:
        run_applied_demo(arguments.output)
    except (ValueError, OSError, RuntimeError) as error:
        print(json.dumps({'status': 'blocked', 'summary': str(error), 'evidence': []}))
        return 2
    print(json.dumps({'status': 'pass', 'summary': 'Synthetic metadata demo completed; numerical binding CLOSED.',
        'evidence': [str(arguments.output/'run_receipt.json'), str(arguments.output/'index.html')]}))
    return 0
