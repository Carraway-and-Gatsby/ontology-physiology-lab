"""Synthetic portability regressions; isolated children cannot read checkout docs."""
from hashlib import sha256
from importlib.resources import files
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]


def isolated_package(tmp_path, code):
    import physiosim
    target = tmp_path/'isolated'
    target.mkdir()
    shutil.copytree(Path(physiosim.__file__).parent, target/'physiosim',
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    command = [sys.executable, '-I', '-B', '-c',
               'import sys; sys.path.insert(0, '+repr(str(target))+'); '+code]
    run = subprocess.run(command, cwd=target, capture_output=True, text=True)
    assert run.returncode == 0, run.stdout+run.stderr
    return run.stdout


def test_default_anatomy_loads_without_repository_docs(tmp_path):
    result = isolated_package(tmp_path,
        'from physiosim.ontology.four_chamber_m1_manifest import build_m1_manifest; '
        'print(build_m1_manifest()["source"]["path"])')
    assert result.strip() == 'docs/evidence_review/anatomy_nodes_v2.json'


def _assert_resource_bytes(actual, expected):
    assert actual == expected


def test_runtime_anatomy_resource_bytes_equal_docs_original(tmp_path):
    resource = files('physiosim.ontology').joinpath('anatomy_nodes_v2.json').read_bytes()
    original = (ROOT/'docs/evidence_review/anatomy_nodes_v2.json').read_bytes()
    _assert_resource_bytes(resource, original)
    with pytest.raises(AssertionError):
        _assert_resource_bytes(resource+b'\n', original)
    from physiosim.ontology.four_chamber_m1_manifest import load_anatomy_v2
    explicit = tmp_path/'anatomy.json'
    explicit.write_bytes(original)
    assert load_anatomy_v2(explicit) == json.loads(original)


def test_law_contract_builds_without_docs_or_pins(tmp_path):
    result = isolated_package(tmp_path,
        'from physiosim.ontology.applied_la_mitral_lv import build_applied_sidecar, validate_applied_sidecar; '
        's=build_applied_sidecar(); validate_applied_sidecar(s); '
        'print(s["model_source"]["declared_contract"])')
    assert result.strip() == 'four_chamber_m1@1.0.0:la-mitral-lv-laws-v1'


def test_law_contract_rejects_m1_version_or_topology_mutation(monkeypatch):
    from dataclasses import replace
    from physiosim.models import four_chamber_m1 as m
    from physiosim.ontology import applied_la_mitral_lv as a
    # Expected semantics are independent of the runtime contract declaration.
    laws, deps = a._law_contract()
    assert {k:v['inputs'] for k,v in laws.items()} == {
        'activation':['heart_rate','systolic_fraction'],
        'E_lv(t)':['emin_lv','emax_lv','activation'], 'P_lv':['E_lv(t)','V_lv','V0_lv'],
        'P_la':['elastance_la','V_la','V0_la'],
        'Q_mitral':['P_la','P_lv','resistance_mitral'], 'Q_cum_mitral':['Q_mitral','time_s']}
    assert [(d['dependent'], d.get('coefficient')) for d in deps if d['kind']=='conservation'] == [('V_la',-1),('V_lv',1)]
    assert laws['activation']['implementation'] == 'physiosim.models.cardiovascular.elastance'
    for key, value in [
        ('MODEL_ID','other'), ('MODEL_VERSION','2.0.0'), ('PRESSURE_REFERENCE','absolute'),
        ('EDGES',tuple(replace(e,source='lv',target='la') if e.name=='mitral' else e for e in m.EDGES)),
        ('EDGES',tuple(replace(e,kind='resistor') if e.name=='mitral' else e for e in m.EDGES)),
        ('COMPARTMENTS',tuple(reversed(m.COMPARTMENTS))),
        ('FourChamberM1Parameters',type('MissingParameters',(),{}))]:
        with monkeypatch.context() as patch:
            patch.setattr(m,key,value)
            with pytest.raises(ValueError, match='M1 law contract'):
                a._law_contract()


def test_m1_demo_source_hashes_from_installed_runtime(tmp_path):
    output = tmp_path/'demo'
    result = isolated_package(tmp_path,
        'from physiosim.experiments.four_chamber_m1_demo import run_demo; '
        'import json; from pathlib import Path; '
        f'output=Path({str(output)!r}); run_demo(output,cycles=1,samples_per_cycle=4); '
        'print((output/"manifest.json").read_text())')
    run = json.loads(result)['run']
    assert 'observed runtime bytes' in run['source_hash_scope']
    assert 'not proof' in run['source_hash_scope']
    assert set(run['source_sha256']) == {
        'models/four_chamber_m1.py', 'simulation/four_chamber_m1.py',
        'ontology/four_chamber_m1_manifest.py', 'experiments/four_chamber_m1_demo.py',
        'models/cardiovascular.py', 'simulation/_hybrid.py', 'ontology/anatomy_nodes_v2.json'}
    for name, digest in run['source_sha256'].items():
        assert digest == sha256((tmp_path/'isolated/physiosim'/name).read_bytes()).hexdigest()


def test_four_chamber_script_uses_own_checkout_src(tmp_path):
    fake = tmp_path/'ambient'; fake.mkdir()
    package = fake/'physiosim'; package.mkdir()
    (package/'__init__.py').write_text('raise RuntimeError("WRONG AMBIENT PACKAGE")\n')
    for name, pythonpath in [('absent',None), ('wrong',str(fake))]:
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        if pythonpath is None:
            env.pop('PYTHONPATH',None)
        else:
            env['PYTHONPATH'] = pythonpath
        output = tmp_path/name
        run = subprocess.run([sys.executable, str(ROOT/'scripts/run_four_chamber_m1.py'),
            '--cycles','1','--samples-per-cycle','4','--output',str(output)],
            cwd=tmp_path, env=env, capture_output=True, text=True)
        assert run.returncode == 0, run.stdout+run.stderr
        manifest = json.loads((output/'manifest.json').read_text())
        assert 'ontology/anatomy_nodes_v2.json' in manifest['run']['source_sha256'], 'CLI imported stale ambient code'
        for relative, digest in manifest['run']['source_sha256'].items():
            assert digest == sha256((ROOT/'src/physiosim'/relative).read_bytes()).hexdigest()


def test_m1_demo_generation_failure_leaves_no_output(tmp_path, monkeypatch):
    from physiosim.experiments import four_chamber_m1_demo as demo
    def fail(*args, **kwargs):
        raise RuntimeError('synthetic generation failure')
    for phase in ('figure','dependency','manifest'):
        for existing in (False,True):
            target = tmp_path/f'{phase}-{existing}'
            if existing:
                target.mkdir()
            previous_umask = os.umask(0o022); os.umask(previous_umask)
            with monkeypatch.context() as patch:
                if phase == 'figure':
                    patch.setattr(demo,'_figure',fail)
                elif phase == 'dependency':
                    patch.setattr(demo,'version',fail)
                else:
                    original = demo._json
                    def serialize(data):
                        if 'semantic_contract' in data:
                            fail()
                        return original(data)
                    patch.setattr(demo,'_json',serialize)
                with pytest.raises(RuntimeError, match='synthetic generation failure'):
                    demo.run_demo(target,cycles=1,samples_per_cycle=4)
            assert os.umask(previous_umask) == previous_umask
            assert target.exists() == existing
            if existing:
                assert list(target.iterdir()) == []


def test_m1_demo_write_failure_rolls_back_and_preserves_nonempty(tmp_path, monkeypatch):
    from physiosim.experiments import four_chamber_m1_demo as demo
    original_fdopen = demo.os.fdopen
    class BrokenStream:
        def __init__(self, fd, *args, **kwargs):
            self.stream = original_fdopen(fd, *args, **kwargs)
        def __enter__(self):
            return self
        def __exit__(self, *args):
            self.stream.close()
        def write(self, data):
            self.stream.write(data[:10])
            raise OSError('synthetic disk failure')
    for existing in (False,True):
        for fail_at in (1,3,5):
            target = tmp_path/f'write-{existing}-{fail_at}'
            if existing:
                target.mkdir()
            count = 0
            def fdopen(fd, *args, **kwargs):
                nonlocal count
                count += 1
                return (BrokenStream if count == fail_at else original_fdopen)(fd, *args, **kwargs)
            with monkeypatch.context() as patch:
                patch.setattr(demo.os,'fdopen',fdopen)
                with pytest.raises(OSError, match='synthetic disk failure'):
                    demo.run_demo(target,cycles=1,samples_per_cycle=4)
            assert target.exists() == existing
            if existing:
                assert list(target.iterdir()) == []
    occupied = tmp_path/'occupied'; occupied.mkdir()
    (occupied/'keep').write_bytes(b'SYNTHETIC existing result')
    with pytest.raises(FileExistsError):
        demo.run_demo(occupied,cycles=1,samples_per_cycle=4)
    assert list(p.name for p in occupied.iterdir()) == ['keep']
    assert (occupied/'keep').read_bytes() == b'SYNTHETIC existing result'
    empty = tmp_path/'empty'; empty.mkdir()
    link = tmp_path/'link'; link.symlink_to(empty, target_is_directory=True)
    with pytest.raises(ValueError, match='symlink'):
        demo.run_demo(link,cycles=1,samples_per_cycle=4)
    assert list(empty.iterdir()) == []


def test_m1_plot_cache_restores_environment(tmp_path, monkeypatch):
    from physiosim.experiments import four_chamber_m1_demo as demo
    from matplotlib.figure import Figure
    from tempfile import TemporaryDirectory
    caches = []
    class Cache(TemporaryDirectory):
        def __enter__(self):
            path = super().__enter__()
            caches.append(Path(path))
            assert Path(path).stat().st_mode & 0o777 == 0o700
            return path
    def fail(*args, **kwargs):
        raise RuntimeError('synthetic render failure')
    for previous in (None,str(tmp_path/'caller-cache')):
        for failing in (False,True):
            target = tmp_path/f'cache-{previous is None}-{failing}'
            with monkeypatch.context() as patch:
                if previous is None:
                    patch.delenv('MPLCONFIGDIR',raising=False)
                else:
                    patch.setenv('MPLCONFIGDIR',previous)
                patch.setattr(demo,'TemporaryDirectory',Cache)
                if failing:
                    patch.setattr(Figure,'savefig',fail)
                    with pytest.raises(RuntimeError, match='synthetic render failure'):
                        demo.run_demo(target,cycles=1,samples_per_cycle=4)
                    assert not target.exists()
                else:
                    demo.run_demo(target,cycles=1,samples_per_cycle=4)
                assert os.environ.get('MPLCONFIGDIR') == previous
                assert all(not p.exists() for p in caches)


def test_publication_rechecks_final_component_and_exclusive_entries(tmp_path, monkeypatch):
    from physiosim.experiments import four_chamber_m1_demo as m1
    from physiosim.experiments import applied_la_mitral_lv_demo as applied
    # A final component replaced after preflight must still fail at open().
    real = tmp_path/'real'; real.mkdir()
    final = tmp_path/'applied'; final.mkdir()
    original_open = os.open
    def swap_final(path, flags, *args, **kwargs):
        if Path(path) == final:
            final.rmdir(); final.symlink_to(real, target_is_directory=True)
        return original_open(path, flags, *args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(applied.os,'open',swap_final)
        with pytest.raises(OSError):
            applied._output_directory(final)
    assert final.is_symlink() and list(real.iterdir()) == []
    with pytest.raises(OSError):
        m1._publish(final, {'result.json': b'{}'})
    assert list(real.iterdir()) == []
    # Insert a final-file symlink after the empty-directory check: never follow
    # or overwrite it, and roll back earlier files without removing this entry.
    output = tmp_path/'exclusive'; output.mkdir()
    other = tmp_path/'other.json'; other.write_bytes(b'SYNTHETIC sentinel')
    def insert_file(path, flags, *args, **kwargs):
        if path == 'second.json':
            (output/'second.json').symlink_to(other)
        return original_open(path, flags, *args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(m1.os,'open',insert_file)
        with pytest.raises(FileExistsError):
            m1._publish(output, {'first.json': b'{}', 'second.json': b'{}'})
    assert [p.name for p in output.iterdir()] == ['second.json']
    assert (output/'second.json').is_symlink()
    assert other.read_bytes() == b'SYNTHETIC sentinel'
    # M1 also accepts a legitimate symlink ancestor for a new target.
    ancestor = tmp_path/'ancestor'; ancestor.symlink_to(real, target_is_directory=True)
    m1._publish(ancestor/'new', {'result.json': b'{}'})
    assert (real/'new/result.json').read_bytes() == b'{}'
