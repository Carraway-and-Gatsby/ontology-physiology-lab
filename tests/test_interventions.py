"""Parameter protocols are mechanistic scenarios, never dose-response models."""
from dataclasses import dataclass
import importlib.util
import pytest


def test_parameter_change_is_immutable_and_auditable():
    assert importlib.util.find_spec('physiosim.interventions') is not None, 'Missing intervention mechanism'
    from physiosim.interventions import ParameterChange

    @dataclass(frozen=True)
    class ModelParameters:
        emax_lv: float = 2.5

    original = ModelParameters()
    change = ParameterChange(name='illustrative inotropy', target='emax_lv', factor=1.2,
                             mechanism='LV maximum elastance', rationale='Exploratory, not a drug model')
    altered, record = change.apply(original, time_s=12.0)
    assert altered.emax_lv == pytest.approx(3.0)
    assert original.emax_lv == 2.5
    assert record['before'] == 2.5
    assert record['after'] == pytest.approx(3.0)
    assert record['time_s'] == 12.0
    assert record['target'] == 'emax_lv'
    assert 'not' in record['limitations']


@pytest.mark.parametrize('factor', [0.0, -1.0, float('nan'), float('inf')])
def test_invalid_factor_rejected(factor):
    from physiosim.interventions import ParameterChange
    with pytest.raises(ValueError):
        ParameterChange('bad', 'emax_lv', factor, 'contractility', 'test')


@pytest.mark.parametrize('time_s', [-1.0, float('nan'), float('inf')])
def test_invalid_event_time_rejected(time_s):
    from physiosim.interventions import ParameterChange
    @dataclass(frozen=True)
    class ModelParameters:
        emax_lv: float = 2.5
    with pytest.raises(ValueError):
        ParameterChange('bad', 'emax_lv', 1.2, 'contractility', 'test').apply(ModelParameters(), time_s=time_s)
