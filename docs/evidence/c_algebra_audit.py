"""Research algebra sanity checks only; no core implementation is imported."""
from fractions import Fraction as F
from pathlib import Path
import json
import random

names = ['LV', 'SA', 'SV', 'RV', 'PA', 'PV']
edges = [(0,1), (1,2), (2,3), (3,4), (4,5), (5,0)]
B = [[int(i == v) - int(i == u) for u,v in edges] for i in range(6)]
assert all(sum(B[i][j] for i in range(6)) == 0 for j in range(6))
rng = random.Random(729)
for _ in range(100):
    pressure = [F(rng.randint(-10, 100), 3) for i in range(6)]
    flow = [F(rng.randint(-100, 100), 7) for j in range(6)]
    derivative = [sum(B[i][j] * flow[j] for j in range(6)) for i in range(6)]
    assert sum(derivative) == 0
    # Telescoping identity used in the proposed energy-balance derivation.
    storage_power = sum(pressure[i] * derivative[i] for i in range(6))
    edge_power = sum(flow[j]*(pressure[u]-pressure[v]) for j,(u,v) in enumerate(edges))
    assert storage_power == -edge_power
# For x'=Qin-Qout, unit conversion is independent of any solver.
ml_per_second_to_l_per_minute = F(60,1000)
assert ml_per_second_to_l_per_minute == F(3,50)
# If x=V1-V01 and total stressed volume S=x+y, then
# deltaP=x/C1-(S-x)/C2; x'=-deltaP/R implies exponential decay.
R,C1,C2 = F(3),F(2),F(5)
coefficient = (1/C1+1/C2)/R
assert coefficient > 0
report = {
    'scope': 'Research algebra sanity checks; not verification of project or third-party model code',
    'state_order': names,
    'incidence_matrix': B,
    'incidence_column_sums': [sum(B[i][j] for i in range(6)) for j in range(6)],
    'exact_rational_conservation_and_power_cases': 100,
    'all_exact_identities_passed': True,
    'flow_unit_conversion_mL_per_s_to_L_per_min': str(ml_per_second_to_l_per_minute),
    'seed': 729
}
path = Path(__file__).with_name('c_algebra_audit.json')
path.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
