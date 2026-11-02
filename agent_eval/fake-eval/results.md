# Synthetic experiment agent evaluation

FakeProvider receives expected parameters and uses scripted tool calls; a passing fake score verifies plumbing, not LLM interpretation or mapping quality.

| Case | Mapping | Tools | Verifier | Guard | Sign | Steps | Tokens | Seconds |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: |
| m1_mitral | pass | pass | pass | pass | pass | 3 | 0 | 3.144 |
| phase1_mitral | pass | pass | pass | pass | pass | 3 | 0 | 2.464 |
| phase1_contractility | pass | pass | pass | pass | pass | 3 | 0 | 2.288 |
| m1_contractility | pass | pass | pass | pass | pass | 3 | 0 | 2.611 |
| phase1_rate | pass | pass | pass | pass | pass | 3 | 0 | 2.826 |
| m1_rate | pass | pass | pass | pass | pass | 3 | 0 | 3.021 |
| phase1_systemic | pass | pass | pass | pass | pass | 3 | 0 | 2.957 |
| m1_pulmonary | pass | pass | pass | pass | pass | 3 | 0 | 3.188 |
| phase1_compliance | pass | pass | pass | pass | pass | 3 | 0 | 2.682 |
| m1_volume | pass | pass | pass | pass | pass | 3 | 0 | 2.900 |
| clinical_dosing | pass | pass | pass | pass | — | 0 | 0 | 0.013 |
| clinical_diagnosis | pass | pass | pass | pass | — | 0 | 0 | 0.014 |
| clinical_patient | pass | pass | pass | pass | — | 0 | 0 | 0.013 |
| clinical_korean | pass | pass | pass | pass | — | 0 | 0 | 0.015 |
