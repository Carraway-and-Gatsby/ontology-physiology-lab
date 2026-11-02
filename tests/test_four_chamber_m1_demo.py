"""Demo artifacts are private, strict JSON, deterministic, and clearly synthetic."""
from dataclasses import asdict
import csv
import json
from pathlib import Path
import numpy as np
import pytest
from physiosim.experiments.four_chamber_m1_demo import run_demo, synthetic_fixture, main
from physiosim.ontology.four_chamber_m1_manifest import validate_m1_manifest


def test_serialization_replay_and_private_outputs(tmp_path):
    p=synthetic_fixture()
    assert sum(p.initial_volumes)==5120
    for directory in [tmp_path/'one',tmp_path/'two']:
        run_demo(directory,cycles=2,samples_per_cycle=40)
        expected={'summary.json','manifest.json','trajectories.csv','figure.png','index.html'}
        assert set(x.name for x in directory.iterdir())==expected
        assert directory.stat().st_mode & 0o777 == 0o700
        for name in expected:
            assert (directory/name).stat().st_mode & 0o777 == 0o600
        summary=json.loads((directory/'summary.json').read_text(),parse_constant=lambda s:pytest.fail(s))
        manifest=json.loads((directory/'manifest.json').read_text(),parse_constant=lambda s:pytest.fail(s))
        validate_m1_manifest(manifest['semantic_contract'])
        assert summary['parameters']==json.loads(json.dumps(asdict(p)))
        assert 'SYNTHETIC' in summary['provenance']
        assert 'not clinically validated' in summary['limitations']
        assert manifest['run']['source_sha256'] and manifest['run']['config_sha256']
        assert summary['settings']['max_step']==p.period/200
        data=np.genfromtxt(directory/'trajectories.csv',delimiter=',',names=True)
        assert len(data)==81 and len(data.dtype.names)==33
        assert (directory/'figure.png').read_bytes().startswith(b'\x89PNG')
        assert 'SYNTHETIC' in (directory/'index.html').read_text()
    for f in (tmp_path/'one').iterdir():
        assert f.read_bytes()==(tmp_path/'two'/f.name).read_bytes()
    with pytest.raises(FileExistsError): run_demo(tmp_path/'one',cycles=1)


def test_cli_config_and_failure(tmp_path):
    config=tmp_path/'config.json'
    config.write_text(json.dumps({'parameters':asdict(synthetic_fixture()),'simulation':{'cycles':1,'samples_per_cycle':4},'solver':{'method':'RK45'}}))
    assert main(['--output',str(tmp_path/'configured'),'--config',str(config)])==0
    summary=json.loads((tmp_path/'configured'/'summary.json').read_text())
    assert summary['periodicity']['per_compartment_ml'] is None
    assert summary['settings']['method']=='RK45'
    config.write_text('{"unexpected":1}')
    with pytest.raises(ValueError): main(['--output',str(tmp_path/'bad'),'--config',str(config)])
    with pytest.raises(SystemExit): main([])


@pytest.mark.parametrize('caller_config', [False, True])
def test_figure_preserves_environment_and_live_matplotlib_config(monkeypatch, tmp_path, caller_config):
    import os
    from physiosim.experiments.four_chamber_m1_demo import _figure
    from physiosim.simulation.four_chamber_m1 import simulate_m1

    import matplotlib
    from matplotlib.figure import Figure
    configdir = matplotlib.get_configdir()
    cachedir = matplotlib.get_cachedir()
    if caller_config:
        monkeypatch.setenv('MPLCONFIGDIR', str(tmp_path/'caller-cache'))
    else:
        monkeypatch.delenv('MPLCONFIGDIR', raising=False)
    changes = []
    original = dict(os.environ)
    renders = []
    savefig = Figure.savefig

    def record_savefig(figure, *args, **kwargs):
        renders.append((matplotlib.get_configdir(), matplotlib.get_cachedir(), dict(os.environ)))
        return savefig(figure, *args, **kwargs)

    monkeypatch.setattr(Figure, 'savefig', record_savefig)

    class Environment(dict):
        def __setitem__(self, key, value):
            changes.append(key)
            super().__setitem__(key, value)

        def pop(self, key, *default):
            changes.append(key)
            return super().pop(key, *default)

        def __delitem__(self, key):
            changes.append(key)
            super().__delitem__(key)

    monkeypatch.setattr(os, 'environ', Environment(original))
    result = simulate_m1(synthetic_fixture(), cycles=1, samples_per_cycle=4)
    assert _figure(result).startswith(b'\x89PNG')
    assert renders == [(configdir, cachedir, original)]
    assert matplotlib.get_configdir() == configdir
    assert matplotlib.get_cachedir() == cachedir
    assert 'MPLCONFIGDIR' not in changes
    assert dict(os.environ) == original
    assert Path(matplotlib.get_configdir()).is_dir()
    assert Path(matplotlib.get_cachedir()).is_dir()
