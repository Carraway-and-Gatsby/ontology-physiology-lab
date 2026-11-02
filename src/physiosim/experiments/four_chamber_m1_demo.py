"""Synthetic M1 fixture and deterministic private artifacts, without network."""
import argparse
from dataclasses import asdict
from hashlib import sha256
from html import escape
from importlib import import_module
from importlib.resources import files
from importlib.metadata import version
from io import BytesIO, StringIO
import json
import os
from pathlib import Path
import platform
# Retained for the pre-existing portability test's monkeypatch target.
from tempfile import TemporaryDirectory
import numpy as np
from physiosim.models.cardiovascular import Parameters as LegacyParameters
from physiosim.models.four_chamber_m1 import FourChamberM1Parameters, COMPARTMENTS, EDGE_NAMES
from physiosim.simulation.four_chamber_m1 import SolverSettings, simulate_m1
from physiosim.ontology.four_chamber_m1_manifest import build_m1_manifest, validate_m1_manifest

FIXTURE_PROVENANCE = ('SYNTHETIC/EXPLORATORY test-design values; not literature-derived, not fitted, '
    'not normal physiology. Ventricular/vascular scalars reuse legacy exploratory defaults; '
    'new atrial and venous-inflow values are test-design choices. Explicit caller total: 5120 mL.')
LIMITATIONS = ('not clinically validated; no atrial contraction, AV delay, inertance, closure regurgitation, '
    'valve area/FSI, septal/pericardial coupling, renal or drug models. Fixed cycles do not prove steady state. '
    'No Smith or published four-chamber reference reproduction. Sampled EDV/ESV/EF describe volume excursion; '
    'they need not equal ejection throughput during overlap or transients.')


def synthetic_fixture():
    legacy=asdict(LegacyParameters())
    legacy.update(elastance_la=.15,elastance_ra=.10,
        resistance_venous_return=.05,resistance_pulmonary_venous=.05,
        unstressed_volumes=(10.,700.,2500.,20.,10.,100.,400.,20.),
        initial_volumes=(140.,850.,3200.,60.,140.,180.,490.,60.))
    return FourChamberM1Parameters(**legacy)


def _json(data):
    return (json.dumps(data,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()


def _publish(output, payloads):
    """Publish prepared bytes exclusively through a no-follow directory fd.

    Roll back only entries created by this call; leave existing results untouched.
    """
    output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    parent_fd = os.open(output.parent, os.O_RDONLY | os.O_DIRECTORY)
    directory_fd = None
    created_identity = None
    written = []
    try:
        try:
            os.mkdir(output.name, mode=0o700, dir_fd=parent_fd)
            created = os.stat(output.name, dir_fd=parent_fd, follow_symlinks=False)
            created_identity = (created.st_dev, created.st_ino)
        except FileExistsError:
            pass
        directory_fd = os.open(output.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                               dir_fd=parent_fd)
        if os.listdir(directory_fd):
            raise FileExistsError('output must be a new or empty private directory')
        os.fchmod(directory_fd, 0o700)
        for name, data in payloads.items():
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=directory_fd)
            written.append(name)
            try:
                stream = os.fdopen(fd, 'wb')
            except BaseException:
                os.close(fd)
                raise
            with stream:
                stream.write(data)
    except BaseException:
        if directory_fd is not None:
            for name in reversed(written):
                os.unlink(name, dir_fd=directory_fd)
        if created_identity is not None:
            current = os.stat(output.name, dir_fd=parent_fd, follow_symlinks=False)
            if (current.st_dev, current.st_ino) == created_identity:
                os.rmdir(output.name, dir_fd=parent_fd)
        raise
    finally:
        if directory_fd is not None:
            os.close(directory_fd)
        os.close(parent_fd)


def _figure(result):
    # Render in-process before publication; leave matplotlib configuration alone.
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    fig=Figure(figsize=(11,8)); FigureCanvasAgg(fig)
    axes=fig.subplots(2,2); beat=result.final_beat; time=result.time[beat]
    for c in ('lv','rv','la','ra'):
        i=COMPARTMENTS.index(c)
        axes[0,0].plot(time,result.pressures[beat,i],label=c)
        axes[0,1].plot(time,result.volumes[beat,i],label=c)
        axes[1,0].plot(result.volumes[beat,i],result.pressures[beat,i],label=c)
    for edge in ('aortic','pulmonary_valve','mitral','tricuspid'):
        axes[1,1].plot(time,result.flow(edge)[beat],label=edge)
    for ax,x,y in [(axes[0,0],'time (s)','pressure (mmHg)'),
                   (axes[0,1],'time (s)','volume (mL)'),
                   (axes[1,0],'volume (mL)','pressure (mmHg)'),
                   (axes[1,1],'time (s)','flow (mL/s)')]:
        ax.set(xlabel=x,ylabel=y); ax.legend(fontsize=8)
    fig.suptitle('SYNTHETIC/EXPLORATORY M1 — not clinically validated (final beat)')
    fig.tight_layout(rect=(0,0,1,.95))
    buffer=BytesIO(); fig.savefig(buffer,format='png',dpi=120,metadata={'Software':'physiosim four_chamber_m1'})
    return buffer.getvalue()


def run_demo(output, *, parameters=None, cycles=30, samples_per_cycle=400, settings=None):
    """Write only into an explicitly named new/empty directory; never overwrite.

    Determinism is same environment/dependencies, not cross-platform bit identity.
    A supplied configuration is a synthetic research input, not patient data.
    """
    p=synthetic_fixture() if parameters is None else parameters
    settings=SolverSettings(max_step=p.period/200) if settings is None else settings
    manifest=build_m1_manifest(); validate_m1_manifest(manifest)
    output=Path(output)
    if output.is_symlink(): raise ValueError('output must not be a symlink')
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise FileExistsError('output must be a new or empty private directory')
    # Invalid numerical/physiological input fails before writing artifacts.
    result=simulate_m1(p,cycles,samples_per_cycle,settings)
    effective=asdict(settings)
    effective['max_step']=p.period/100 if settings.max_step is None else settings.max_step
    config={'parameters':asdict(p),'simulation':{'cycles':cycles,'samples_per_cycle':samples_per_cycle},'solver':effective}
    summary={'model_id':manifest['model_id'],'model_version':manifest['model_version'],
        'provenance':FIXTURE_PROVENANCE if parameters is None else
            'SYNTHETIC/EXPLORATORY caller-supplied research configuration; no calibration asserted.',
        'limitations':LIMITATIONS,'parameters':asdict(p),'settings':effective,
        'simulation':config['simulation'],'metrics':result.metrics(),
        'metric_semantics':'SV/CO use integrated outlet flows; EDV/ESV/EF use sampled extrema. Pressure/volume means use sampled time quadrature.',
        'conservation':result.conservation(),'periodicity':result.periodicity(),
        'pressure_reference':manifest['pressure_reference'],'null_policy':'Unavailable periodicity for a single beat is null.'}
    # A controlled umask covers matplotlib's temporary cache as well as outputs.
    previous_umask=os.umask(0o077)
    try:
        columns=['time_s']+['V_'+c+'_ml' for c in COMPARTMENTS]+['P_'+c+'_mmhg' for c in COMPARTMENTS]+[
            'Q_'+e+'_ml_s' for e in EDGE_NAMES]+['Qcum_'+e+'_ml' for e in EDGE_NAMES]
        table=StringIO()
        np.savetxt(table,np.column_stack((result.time,result.volumes,result.pressures,result.flows,result.cumulative_flows)),
            delimiter=',',header=','.join(columns),comments='',fmt='%.17g')
        payloads = {'trajectories.csv': table.getvalue().encode(),
                    'summary.json': _json(summary), 'figure.png': _figure(result)}
        html=('<!doctype html><html lang="en"><meta charset="utf-8"><title>Synthetic M1</title>'
            '<style>body{font:16px system-ui;max-width:1100px;margin:auto;padding:24px}img{width:100%}pre{white-space:pre-wrap}</style>'
            '<h1>SYNTHETIC/EXPLORATORY four_chamber_m1</h1><p>'+escape(LIMITATIONS)+'</p>'
            '<img src="figure.png" alt="Final beat pressures, volumes, PV loops and flows">'
            '<p><a href="trajectories.csv">Trajectories</a> · <a href="summary.json">Summary</a> · '
            '<a href="manifest.json">Semantic contract and provenance</a></p><pre>'+escape(_json(summary).decode())+'</pre></html>')
        payloads['index.html'] = html.encode()
        modules = ('models.four_chamber_m1', 'simulation.four_chamber_m1',
            'ontology.four_chamber_m1_manifest', 'experiments.four_chamber_m1_demo',
            'models.cardiovascular', 'simulation._hybrid')
        source_hashes = {name.replace('.', '/')+'.py':
            sha256(Path(import_module('physiosim.'+name).__file__).read_bytes()).hexdigest()
            for name in modules}
        source_hashes['ontology/anatomy_nodes_v2.json'] = sha256(
            files('physiosim.ontology').joinpath('anatomy_nodes_v2.json').read_bytes()).hexdigest()
        run={'parameters':asdict(p),'settings':effective,'simulation':config['simulation'],
            'config':config,'config_sha256':sha256(_json(config)).hexdigest(),
            'source_sha256':source_hashes,
            'source_hash_scope':'Package-relative observed runtime bytes; not proof of semantic or physiological validity.',
            'python':platform.python_version(),'dependencies':{name:version(name) for name in ('numpy','scipy','matplotlib','pint')},
            'output_sha256':{name:sha256(data).hexdigest() for name,data in payloads.items()},
            'hash_scope':'All four output files other than manifest.json; manifest excludes its own hash.',
            'replay_scope':'Same implementation and environment; no timestamps or stochastic input.'}
        payloads['manifest.json'] = _json({'semantic_contract':manifest,'run':run})
        _publish(output.absolute(), payloads)
    finally:
        os.umask(previous_umask)
    return summary


def main(argv=None):
    parser=argparse.ArgumentParser(description='SYNTHETIC/EXPLORATORY passive-atria M1; not clinically validated')
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--cycles',type=int)
    parser.add_argument('--samples-per-cycle',type=int)
    parser.add_argument('--config',type=Path,help='Local synthetic JSON: required parameters, optional simulation and solver objects')
    args=parser.parse_args(argv)
    parameters=None; simulation={'cycles':30,'samples_per_cycle':400}; solver=None
    if args.config:
        config=json.loads(args.config.read_text())
        if not isinstance(config,dict) or set(config)-{'parameters','simulation','solver'} or 'parameters' not in config:
            raise ValueError('config requires parameters, with only simulation and solver optional')
        parameters=FourChamberM1Parameters(**config['parameters'])
        if set(config.get('simulation',{}))-set(simulation): raise ValueError('unknown simulation controls')
        simulation.update(config.get('simulation',{}))
        solver=SolverSettings(**config.get('solver',{}))
    if args.cycles is not None: simulation['cycles']=args.cycles
    if args.samples_per_cycle is not None: simulation['samples_per_cycle']=args.samples_per_cycle
    run_demo(args.output,parameters=parameters,settings=solver,**simulation)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
