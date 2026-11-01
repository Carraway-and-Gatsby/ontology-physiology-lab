"""Event-aware M1 integration, adapted from _hybrid without changing legacy code.

Only eight volumes are physical states. Eight auxiliary flow integrals restart
at every smooth regime, preserving useful absolute-error scales in mL.
"""
from dataclasses import dataclass
import numpy as np
from scipy.integrate import solve_ivp, trapezoid
from physiosim.models.four_chamber_m1 import (
    COMPARTMENTS, EDGE_NAMES, INCIDENCE, SOURCE, TARGET, VALVE_INDICES,
    FourChamberM1Parameters, positive_scalar, pressures, edge_flows, resistances,
)


@dataclass(frozen=True)
class SolverSettings:
    """Numerical controls only: rtol dimensionless; atol mL; max_step seconds.

    None selects period/100. Scalar atol applies to volumes and local integrals.
    """
    method: str = 'DOP853'
    rtol: float = 1e-9
    atol: float = 1e-10
    max_step: float | None = None

    def __post_init__(self):
        if self.method not in ('DOP853','RK45','Radau'):
            raise ValueError('method must be DOP853, RK45 or Radau')
        for name in ('rtol','atol','max_step'):
            value = getattr(self,name)
            if name == 'max_step' and value is None:
                continue
            positive_scalar(value,name)
            object.__setattr__(self,name,float(value))


@dataclass
class FourChamberM1Result:
    time: np.ndarray
    volumes: np.ndarray
    pressures: np.ndarray
    flows: np.ndarray
    cumulative_flows: np.ndarray
    parameters: FourChamberM1Parameters
    settings: SolverSettings
    cycles: int
    samples_per_cycle: int
    compartment_names: tuple[str,...] = COMPARTMENTS
    edge_names: tuple[str,...] = EDGE_NAMES

    @staticmethod
    def _column(names,name):
        if name not in names:
            raise KeyError(name)
        return names.index(name)

    def volume(self,name):
        return self.volumes[:,self._column(self.compartment_names,name)]

    def pressure(self,name):
        return self.pressures[:,self._column(self.compartment_names,name)]

    def flow(self,name):
        return self.flows[:,self._column(self.edge_names,name)]

    @property
    def final_beat(self):
        return slice(-self.samples_per_cycle-1,None)

    def conservation(self):
        """Local balance checks wiring/roundoff, not independent quadrature."""
        residual = self.volumes-self.volumes[0]-self.cumulative_flows@INCIDENCE.T
        return {'total_initial_volume_ml':float(sum(self.parameters.initial_volumes)),
                'total_volume_drift_ml':float(np.max(np.abs(self.volumes.sum(axis=1)-self.volumes[0].sum()))),
                'local_balance_residual_ml':float(np.max(np.abs(residual)))}

    def periodicity(self):
        n=self.samples_per_cycle
        diff = np.max(np.abs(self.volumes[-n-1:]-self.volumes[-2*n-1:-n]),axis=0) if self.cycles >= 2 else None
        return {'per_compartment_ml':None if diff is None else dict(zip(COMPARTMENTS,map(float,diff))),
                'max_difference_ml':None if diff is None else float(np.max(diff)),
                'interpretation':'Fixed cycle count does not prove steady state; sampled final/prior beat differences only.'}

    def metrics(self):
        """Final beat: integrated forward SV/CO; sampled extrema and means.

        EF describes volume excursion, not necessarily ejected throughput when
        filling/ejection overlap or the beat is not periodic.
        """
        beat=self.final_beat
        t=self.time[beat]; v=self.volumes[beat]; pr=self.pressures[beat]
        duration=t[-1]-t[0]
        result={}
        for chamber,edge in [('lv','aortic'),('rv','pulmonary_valve')]:
            i=COMPARTMENTS.index(chamber); j=EDGE_NAMES.index(edge)
            sv=float(self.cumulative_flows[-1,j]-self.cumulative_flows[beat.start,j])
            edv=float(v[:,i].max()); esv=float(v[:,i].min())
            result.update({chamber+'_stroke_volume_ml':sv,
                chamber+'_cardiac_output_ml_s':sv/duration,
                chamber+'_cardiac_output_l_min':sv/duration*60/1000,
                chamber+'_edv_sample_ml':edv, chamber+'_esv_sample_ml':esv,
                chamber+'_ejection_fraction_sample':(edv-esv)/edv})
        for c in ('la','ra','sa','pa'):
            i=COMPARTMENTS.index(c)
            result.update({c+'_pressure_min_mmhg':float(pr[:,i].min()),
                c+'_pressure_max_mmhg':float(pr[:,i].max()),
                c+'_pressure_mean_mmhg':float(trapezoid(pr[:,i],t)/duration)})
            if c in ('la','ra'):
                result.update({c+'_volume_min_ml':float(v[:,i].min()),
                    c+'_volume_max_ml':float(v[:,i].max()),
                    c+'_volume_mean_ml':float(trapezoid(v[:,i],t)/duration)})
        return result


def _gaps(time,volume,p):
    pressure=pressures(time,volume,p)
    return pressure[SOURCE[VALVE_INDICES]]-pressure[TARGET[VALVE_INDICES]]


def _right_hand_modes(time,volume,p,modes,boundary):
    pressure=pressures(time,volume,p)
    gaps=pressure[SOURCE[VALVE_INDICES]]-pressure[TARGET[VALVE_INDICES]]
    eps=np.finfo(float).eps
    resolution=np.full(4,64*eps*max(1.,float(np.max(np.abs(pressure)))))
    delta=min(np.sqrt(eps)*p.period,(boundary-time)/2)
    future=gaps
    if delta>0 and time+delta>time:
        probe=volume+delta*(INCIDENCE@edge_flows(pressure,p))
        future=_gaps(time+delta,probe,p)
        resolution+=8*eps*(1+abs(time))*np.abs(future-gaps)/delta
    tied=np.abs(gaps)<=resolution
    modes=np.where(tied,modes,gaps>0).copy()
    decided=tied & (np.abs(future)>resolution)
    modes[decided]=future[decided]>0
    return modes


def _integrate(p,times,cycles,settings):
    resistance=resistances(p)
    volume=np.array(p.initial_volumes)
    offset=np.zeros(8); output=np.empty((len(times),16))
    current=float(times[0]); next_sample=0; zero_length_events=0
    modes=_gaps(current,volume,p)>0
    # Each preceding beat end is the next activation start. The peak checkpoint
    # prevents an opening plus closing from being skipped by a long trial step.
    boundaries=[x for beat in range(cycles) for x in (
        (beat+p.systolic_fraction/2)*p.period,
        (beat+p.systolic_fraction)*p.period,(beat+1)*p.period)]
    boundaries[-1]=float(times[-1])
    for boundary in boundaries:
        boundary=min(float(boundary),float(times[-1]))
        while current<boundary:
            modes=_right_hand_modes(current,volume,p,modes,boundary)
            regime=modes.copy()

            def derivative(time,state):
                pressure=pressures(time,state[:8],p)
                q=(pressure[SOURCE]-pressure[TARGET])/resistance
                q[VALVE_INDICES[~regime]]=0.
                return np.concatenate((INCIDENCE@q,q))

            events=[]
            for edge,opened in zip(VALVE_INDICES,regime):
                def event(time,state,edge=int(edge),opened=bool(opened)):
                    pressure=pressures(time,state[:8],p)
                    gap=float(pressure[SOURCE[edge]]-pressure[TARGET[edge]])
                    return gap if gap != 0 else (np.finfo(float).eps if opened else -np.finfo(float).eps)
                event.terminal=True
                event.direction=-1 if opened else 1
                events.append(event)
            for i in range(8):
                def volume_event(time,state,i=i):
                    return state[i]
                volume_event.terminal=True
                volume_event.direction=-1
                events.append(volume_event)
            solution=solve_ivp(derivative,(current,boundary),np.concatenate((volume,np.zeros(8))),
                method=settings.method,rtol=settings.rtol,atol=settings.atol,
                max_step=p.period/100 if settings.max_step is None else settings.max_step,
                dense_output=True,events=events)
            if not solution.success:
                raise RuntimeError('M1 integration failed: '+solution.message)
            if any(len(found) for found in solution.t_events[4:]) or np.any(solution.y[:8]<=0):
                raise RuntimeError('M1 compartment volume reached zero')
            if not np.isfinite(solution.y).all():
                raise RuntimeError('M1 nonfinite accepted state')
            end=float(solution.t[-1]); end_state=solution.y[:,-1]
            end_sample=int(np.searchsorted(times,end,side='right'))
            if end_sample>next_sample:
                values=solution.sol(times[next_sample:end_sample]).T
                if not np.isfinite(values).all() or np.any(values[:,:8]<=0):
                    raise RuntimeError('M1 invalid dense-output volume')
                output[next_sample:end_sample,:8]=values[:,:8]
                output[next_sample:end_sample,8:]=values[:,8:]+offset
                next_sample=end_sample
            volume=end_state[:8].copy(); offset=offset+end_state[8:]
            if solution.status==1:
                for i,found in enumerate(solution.t_events[:4]):
                    if len(found): modes[i]=not modes[i]
            if end<=current:
                zero_length_events+=1
                if solution.status!=1 or zero_length_events>8:
                    raise RuntimeError('M1 valve events failed to advance time')
            else:
                zero_length_events=0
            current=end
    if next_sample!=len(times):
        raise RuntimeError('M1 integration did not cover requested samples')
    return output[:,:8],output[:,8:]


def simulate_m1(parameters, cycles=30, samples_per_cycle=400, settings=None):
    """No normalization/projection; fixed duration is not a steady-state claim."""
    if not isinstance(parameters,FourChamberM1Parameters):
        raise TypeError('parameters must be explicit FourChamberM1Parameters')
    if settings is None: settings=SolverSettings()
    if not isinstance(settings,SolverSettings): raise TypeError('invalid settings')
    for name,value,minimum in [('cycles',cycles,1),('samples_per_cycle',samples_per_cycle,4)]:
        if isinstance(value,(bool,np.bool_)) or not isinstance(value,(int,np.integer)) or value<minimum:
            raise ValueError(f'{name} must be integer >= {minimum}')
    duration=cycles*parameters.period
    if not np.isfinite(duration) or duration<=0:
        raise ValueError('simulation duration must be finite and positive')
    times=np.linspace(0.,duration,cycles*samples_per_cycle+1)
    if not np.all(np.diff(times)>0): raise ValueError('sample times must advance')
    volumes,cumulative=_integrate(parameters,times,cycles,settings)
    pressure=np.array([pressures(t,v,parameters) for t,v in zip(times,volumes)])
    flow=np.array([edge_flows(pr,parameters) for pr in pressure])
    return FourChamberM1Result(times,volumes,pressure,flow,cumulative,parameters,settings,cycles,samples_per_cycle)
