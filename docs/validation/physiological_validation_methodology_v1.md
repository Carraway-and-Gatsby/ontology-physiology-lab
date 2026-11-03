# Physiological Validation Methodology, Version 1 (design only, 2026-11-03)

**Status.** Read-only methodology for independent review. Nothing in the model, the numerical verification programme, the tests or the canonical results was changed. No dataset was downloaded, no software installed and no new simulation executed. The only external query beyond literature and documentation pages was the public VitalDB track index (`https://api.vitaldb.net/trks`, case id / track name / track id), retained as `docs/evidence/e_vitaldb_track_case_counts_2026-11-03.tsv`; it contains no physiological samples.

**Baseline under review.** `main@7b9e2e8`. Model: `src/physiosim/models/cardiovascular.py`; canonical outputs: `results/phase1/summary.json`. This document is independent of, and must not be inferred from, the numerical verification methodology of the same date (`docs/verification/model_verification_methodology_v1.md`): that document covers whether the equations are solved correctly; this one covers whether the equations, with some parameter set, predict measured physiology. Passing every verification gate implies nothing here.

**Framework.** The structure follows the risk-informed credibility approach of ASME V&V 40-2018 as summarised by the FDA final guidance *Assessing the Credibility of Computational Modeling and Simulation in Medical Device Submissions* (CDRH, November 2023, docket FDA-2021-D-0980) and its January 2024 FDA webinar (nine-step framework; eight credibility-evidence categories: code verification, model calibration evidence, bench validation, in vivo validation, population-based validation, emergent model behaviour, model plausibility, calculation verification/UQ with COU inputs). Credibility goals are set prospectively (step 6) and judged afterwards (step 8). **No regulatory compliance is claimed or sought.** The model is research software with no clinical decision in its context of use, so model risk under that framework is low; this lowers the required rigour, it does not license unsupported claims.

**Governing rule for every threshold below.** Either a published source is cited for the number or for the procedure that yields it, or the test is report-only with no pass mark. Thresholds are fixed in this document before any dataset is opened (pre-registration); any later change must be recorded as an amendment with its date and reason.

---

## 1. Physiological context-of-use statement

### 1.1 Question of interest

Does the six-compartment ideal-diode elastance model, with parameters estimated from a declared subset of a subject's measurements, predict the subject's *other* beat-averaged haemodynamic measurements, and the *direction and magnitude of change* of those measurements under perturbations that the model represents mathematically?

### 1.2 Context of use (COU)

The model is used to predict, for an individual anaesthetised or resting adult human (or anaesthetised pig) whose heart rate is measured and imposed, over windows of a few minutes in which conditions are stationary:

- beat-averaged systemic arterial pressures (mean, diastolic; systolic with a declared site caveat);
- stroke volume and cardiac output;
- left-ventricular end-diastolic and end-systolic volumes and ejection fraction;
- mean pulmonary arterial pressure, a lumped pulmonary venous reservoir pressure, and a lumped systemic venous reservoir pressure;
- the change in those quantities between two stationary windows separated by one of the following perturbations: a change in heart rate, a change in circulating blood volume, a change in systemic or pulmonary vascular resistance, a change in venous unstressed volume, a change in ventricular peak elastance.

Everything outside this list is outside the COU (Section 1.6).

### 1.3 What the equations represent

Six states, all total compartment volumes: LV, systemic arteries (`sa`), systemic veins (`sv`), RV, pulmonary arteries (`pa`), pulmonary veins (`pv`). Pressures are linear in stressed volume with a prescribed cosine elastance pulse for both ventricles (shared phase, width `systolic_fraction`). Four flows are ideal diodes (`max((P_up - P_down)/R, 0)`), two are linear resistors. Total blood volume is conserved exactly. Heart rate is an imposed input, not a state. Full equations: `docs/physiology.md`.

### 1.4 Classification of model quantities

| Class | Quantities | Comment |
|---|---|---|
| **Observable model outputs** (directly comparable to a measurement, with a declared location mapping) | `P_sa` waveform and its mean/min/max; `P_pa` mean; `P_sv` mean; `P_pv` mean; `Q_aortic` waveform; SV (integral of `Q_aortic`); CO; LV EDV, ESV, EF; RV EDV, ESV, EF (computable from `V_rv` though not currently reported by `metrics()`) | Site and reference caveats in Section 4 |
| **Latent states** (never measured directly in any candidate dataset) | `V_sa`, `V_sv`, `V_pa`, `V_pv` absolute volumes; instantaneous `P_lv`, `P_rv` (measured only in catheter-lab or animal studies; not in VitalDB) | Only differences `V - V0` affect pressures; absolute values are not identifiable from pressures alone |
| **Exploratory parameters** (all 18 fields; none fitted; see `docs/physiology.md`) | `heart_rate`, `emin_lv`, `emax_lv`, `emin_rv`, `emax_rv`, `systolic_fraction`, four compliances, six resistances, six unstressed volumes, six initial volumes | `heart_rate` becomes a measured input under this COU; `initial_volumes` only set total volume and the transient (Section 5.3) |
| **Mechanisms absent from the equations** | atria and atrial contraction; septal and pericardial interaction; intrathoracic pressure and its respiratory modulation; valve inertia, regurgitation and stenosis dynamics (open-on-pressure/close-on-flow law of Smith 2004 deliberately not implemented); nonlinear passive ventricular (and vascular) pressure-volume relations; arterial wave propagation, inertance, reflections and the dicrotic notch; baroreflex and all autonomic control; renal and hormonal volume regulation; coronary circulation; oxygen transport; pharmacokinetics/pharmacodynamics; heart-rate dependence of systolic duration | Any observation whose explanation requires one of these is *not* a validation target for this model; it is an expected-failure diagnostic (Section 6) |

### 1.5 Model inputs required for a patient-specific prediction

Heart rate (measured); at least one systemic arterial pressure signal; one independent flow or volume measurement (thermodilution/Fick CO, Doppler flow, or imaging volumes); and, for right-sided predictions, at least one right-sided pressure. Without an independent flow or volume measurement, no patient-specific validation claim is permitted (Section 5.5).

### 1.6 Outside the intended scope

Spontaneously breathing subjects with large respiratory pressure swings (unless beat-averaging over whole respiratory cycles is declared); exercise; any transient faster than the settling time of the model (tens of beats); arrhythmia; valve disease; paediatric subjects; shock states with active reflex compensation (these may be *probed* as falsification experiments, Section 3.D, but never claimed as validated); wave-shape indices that depend on propagation (augmentation index, pulse-wave velocity, dicrotic-notch timing); pulmonary oedema or any clinical diagnosis; any drug effect.

### 1.7 Baseline parameter set relative to published reference ranges (plausibility, not validation)

Baseline final-beat metrics from `results/phase1/summary.json`, set against published population references (FDA category 7, model plausibility; this does not validate anything):

| Quantity | Baseline | Published reference | Reading |
|---|---:|---|---|
| Systemic SBP/DBP (mmHg) | 163.0 / 104.7 | Normal <120/<80; stage 2 hypertension >=140 or >=90 (2017 ACC/AHA, Whelton 2018) | Baseline is a hypertensive-range computational state, as the README states |
| Mean PAP (mmHg) | 23.8 | Healthy resting mean 14.0 +/- 3.3 mmHg, 1,187 subjects, 47 RHC studies (Kovacs 2009); PH defined as mPAP > 20 mmHg (2022 ESC/ERS, Humbert 2022) | Above the healthy range and above the PH threshold |
| CO (L/min) | 7.70 | Healthy adult CMR SV 103 (61-145) mL men, 83 (52-114) women (Kawel-Boehm 2020, papillary in mass); at HR 75 the implied CO ranges are 4.6-10.9 / 3.9-8.6 | High-normal at this heart rate |
| LV EDV / ESV (mL) | 177.7 / 75.1 | 155 (95-215) / 55 (25-85) men; 123 (78-167) / 43 (21-64) women (Kawel-Boehm 2020) | Within the male range |
| LV EF | 0.577 | 64 (49-79) % men, 66 (52-79) % women (Kawel-Boehm 2020) | Within range |

The baseline is therefore not "a healthy adult" and must be calibrated per subject before any comparison; the baseline values themselves are never a validation target.

---

## 2. Observable-output mapping matrix

The matrix lists each observable model output, the measured quantity it is mapped to, the measurement location and device per candidate dataset, the known mismatch between model and measurement, and the uncertainty source. Device-level numbers are from the cited sources; where a figure was not retrieved in primary text it is marked (secondary).

| Model output | Measured quantity (unit) | Datasets, device, location, rate | Model-to-measurement mismatch | Measurement uncertainty |
|---|---|---|---|---|
| `P_sa(t)` waveform | Invasive arterial pressure (mmHg) | VitalDB `SNUADC/ART` 500 Hz, radial (femoral renamed `SNUADC/FEM`, 127 cases); MIMIC-III/IV `ABP` 125 Hz, site not documented; SCG-RHC Mac-Lab ABP; porcine aortic root and femoral 2 kHz; Autonomic Aging and CVES: non-invasive finger pressure (CNAP, Portapres) | Model `P_sa` is a lumped Windkessel pressure with no propagation: no dicrotic notch, no peripheral amplification. Radial/femoral systolic pressure is amplified relative to central pressure; mean and diastolic pressure transfer better (Charlton 2019 site-resolved simulated waveforms; VitalDB does not document transducer zeroing or damping) | Catheter-transducer damping/resonance (unquantified in VitalDB); zero drift; blood-sampling artefacts (VitalDB documents these); finger-pressure devices add vascular-unloading bias |
| `P_sa` mean, min, max | MAP, DBP, SBP (mmHg) | VitalDB `Solar8000/ART_MBP/SBP/DBP` 2 s numerics (3,724 cases) and from `SNUADC/ART`; MIMIC numerics 1 s or 1 min | As above; MAP primary, DBP secondary, SBP site-biased | As above |
| `P_pa` mean | Mean PAP (mmHg), pulmonary artery catheter | VitalDB `Solar8000/PA_MBP` 2 s, 81 cases; SCG-RHC PAP 250 Hz, 83 procedures; porcine: not recorded | Lumped pulmonary arterial reservoir; PA catheter pressure includes intrathoracic pressure (ventilated subjects) which the model lacks | Transducer level; respiratory swings; end-expiratory reading convention not applied in continuous data |
| `P_pv` mean | Pulmonary capillary wedge pressure or LA pressure (mmHg) | SCG-RHC PCWP (wedge); porcine LA/wedge 2 kHz; VitalDB: absent (no wedge track) | Model has no atrium; `P_pv` is a reservoir upstream of the mitral diode. PCWP approximates LA pressure, not pulmonary venous pressure, and contains v-waves the model cannot produce | Wedge quality; intrathoracic pressure |
| `P_sv` mean | CVP / right atrial pressure (mmHg) | VitalDB `SNUADC/CVP` wave 500 Hz (1,586 cases), `Solar8000/CVP` numerics (1,608); SCG-RHC RAP; porcine RA 2 kHz | Model has no RA; `P_sv` is a lumped venous reservoir upstream of the tricuspid diode; measured CVP includes atrial waves and intrathoracic pressure | As for PAP; CVP transducer level errors are of the same order as the signal |
| `Q_aortic(t)`, SV, CO | Aortic flow / stroke volume / cardiac output (mL/s, mL, L/min) | **Independent of pressure:** VitalDB `Vigilance/CO` continuous thermodilution (65 cases; 60 with ART and PA_MBP), `CardioQ/FLOW` oesophageal Doppler descending-aortic velocity waveform 180 Hz + `CardioQ/SV`, `CardioQ/CO` (29 cases, 27 with ART); SCG-RHC CO by Fick and thermodilution. **Not independent of pressure:** VitalDB `EV1000/CO`, `Vigileo/CO` (617 and 323 cases) are uncalibrated pulse-contour estimates computed from the same arterial waveform | Model SV is forward aortic flow per beat; Doppler measures descending-aortic velocity (a fraction of total flow, scaled by a nomogram); thermodilution is right-sided and beat-averaged; pulse-contour CO is a function of the pressure waveform and must not be used as an independent flow reference | Thermodilution precision assumed +/-20 % (Critchley 1999); uncalibrated pulse-contour %error 30 % or more depending on software version and vascular tone (Slagt 2014 systematic review); Doppler %error +/-65 % across historical studies (Critchley 1999) |
| LV EDV, ESV, EF | Imaging volumes (mL, %) | EchoNet-Dynamic (10,030 videos with EDV, ESV, EF; no pressure); CMR reference ranges (population only); SCG-RHC and VitalDB: not measured | Population-level only unless imaging is simultaneous with pressure (no candidate dataset provides this) | Expert EF inter-observer variability; CMR population SD (Kawel-Boehm 2020) |
| RV EDV, ESV, EF | Continuous thermodilution RV volumetrics (mL, %) | VitalDB `Vigilance/EDV`, `ESV`, `RVEF` (49, 49, 48 cases) | Model RV is a linear elastance chamber with no atrium; device RVEF is derived from thermodilution washout | Device-specific; not retrieved in primary text (secondary) |
| Heart rate | HR (bpm) | All datasets (ECG, `Solar8000/HR`) | Model input, not output; beat-to-beat variability is averaged | Negligible for the COU |

Entries marked "not measured" are gaps carried into Section 4.

---

## 3. Candidate experimental dataset inventory

Only datasets with independently measured cardiovascular quantities are candidates for validation. Simulation-generated databases are excluded as validation targets and listed only as baselines (3.11). Facts below were read from the cited dataset landing pages or papers on 2026-11-03; items I could not confirm in primary text are marked.

### 3.1 VitalDB (PhysioNet `vitaldb` 1.0.0; Lee et al., Sci Data 2022)

- **Population and conditions.** 6,388 non-cardiac surgical cases (general 4,930, thoracic 1,111, gynaecology 230, urology 117) at Seoul National University Hospital, Aug 2016 to Jun 2017; median age 59 (IQR 48-68), 50.8 % male; general anaesthesia 94.6 %, mechanically ventilated; propofol/remifentanil TCI; single centre, single ethnicity (the authors warn of overfitting). IRB H-1408-101-605; NCT02914444; consent waived (anonymised).
- **Measurements, units, rate.** Up to 12 waveform tracks at 62.5-500 Hz and up to 184 numeric tracks at 1-7 s. Track-index counts (cases with the track, from the public index retained in `docs/evidence/`): `SNUADC/ART` 3,645; `SNUADC/CVP` 1,586; `SNUADC/FEM` 127; `Solar8000/ART_MBP` 3,724; `Solar8000/PA_MBP` 81; `EV1000/CO` 617; `Vigileo/CO` 323; `Vigilance/CO` 65 (`EDV`/`ESV` 49, `RVEF` 48); `CardioQ/CO` 29 (`FLOW` waveform 29, `ABP` 29). Co-occurrence: ART + `Vigilance/CO` + `PA_MBP` 60 cases; ART + `CardioQ/FLOW` 27; ART + CVP wave + (EV1000 or Vigileo CO) 485. Drug infusion tracks (rate, volume): phenylephrine 127, norepinephrine 88, nitroglycerin 32, dopamine 33, PGE1 90, propofol 3,512, remifentanil 4,773. Ventilator tracks (TV, PEEP, mean airway pressure) in roughly 6,000 cases.
- **Location.** Radial arterial line (femoral renamed FEM); CVP via central line; PA pressures via PA catheter in the 81 cases.
- **Quality and uncertainty.** Not preprocessed; artefacts (blood sampling, flushing) retained by design; anaesthesia/operation times from the EMR at 5-minute granularity; transducer zeroing, levelling and damping not documented; visual verification by four anaesthesiologists; tracks with <10 samples deleted.
- **Simultaneous pressure and flow.** Yes, in three forms: pulse-contour CO (not independent), continuous thermodilution CO (65 cases), oesophageal Doppler flow waveform at 180 Hz with simultaneous `CardioQ/ABP` (29 cases).
- **Compatibility.** Highest of any candidate for systemic pressure, CVP, and right-sided pressure plus independent CO in a subset. No LV volumes, no wedge pressure, no LV pressure. Perturbations are uncontrolled clinical events (vasopressor infusions, blood loss, fluid, positioning) with timing known only from infusion-pump tracks and EMR fields.
- **Licensing and access.** PhysioNet: open access, CC BY 4.0, no credentialing. vitaldb.net: users must agree to a Data Use Agreement before use (the examples repository states this; DUA text not retrieved here). Both routes must be recorded when the dataset is opened.

### 3.2 MIMIC-III Waveform Database Matched Subset (PhysioNet 1.0, 2020)

- **Population.** Adult and neonatal ICU patients, Beth Israel Deaconess Medical Center; 22,317 waveform records, 22,247 numerics records, 10,282 patients matched to MIMIC-III Clinical Database v1.4 (about 34 % of all waveform records could be matched).
- **Measurements.** ECG, ABP, respiration, PPG at 125 Hz with 8-12-bit resolution (parent database page); numerics (HR, SpO2, NIBP, etc.) at 1 s or 1 min. PAP and CVP channels are not documented on the landing pages and must be enumerated from headers at intake.
- **Quality.** Signals not all simultaneous; record boundaries do not match ICU stays; surrogate dates; manual identifier entry.
- **Flow.** No independent flow measurement in the waveform database; cardiac output appears only as sparse clinical-chart entries (thermodilution) in the clinical database, which requires credentialed access (CITI training and DUA), unlike the waveform data (ODbL v1.0, open).
- **Compatibility.** Useful for systemic pressure waveform morphology and MAP/DBP at scale; perturbation timing requires linking to the clinical database.

### 3.3 MIMIC-IV Waveform Database (PhysioNet 0.1.0, technical preview)

200 records, 198 patients; ECG, PPG, respiration, invasive and non-invasive BP; ODbL v1.0; FLAC-compressed; linked to MIMIC-IV v2.0 by `subject_id`/`hadm_id`; a release of about 10,000 records is announced. Same compatibility profile as 3.2; too small today to be a primary source.

### 3.4 SCG-RHC (PhysioNet `scg-rhc-wearable-database` 1.0.0; Chan, Klein, Fan, Inan 2023; Shandhi et al. IEEE TBME 2022)

- **Population and conditions.** 73 patients (14 inpatient, 59 outpatient), ages 26-84, 24 female, referred for haemodynamic evaluation of heart-failure status; 83 right-heart catheterisations at UCSF (IRB 16-20442, written consent). Baseline, then systemic vasodilator at physician discretion: sublingual nitroglycerin 400 or 800 mcg, or IV nitroprusside from 0.3 mcg/kg/min titrated every 5 min.
- **Measurements.** Catheter pressures (PAP, PCWP, RAP, RVP) at 250 Hz from the Mac-Lab, plus arterial pressure, 12-lead ECG, pleth, respiration; wearable ECG 1 kHz and SCG 500 Hz; processed WFDB files resampled to 500 Hz. CO by Fick and by thermodilution. Stroke volume derivation not stated.
- **Simultaneous pressure and flow.** Yes: right-sided pressures, arterial pressure and thermodilution/Fick CO, before and after a documented vasodilator intervention.
- **Compatibility.** The only human candidate with wedge pressure, RAP, PAP and independent CO in the same record, and with a controlled perturbation of the kind the model represents (systemic resistance and venous unstressed-volume change). Population is heart-failure referral, not healthy; sedation state and ventilation not documented on the page.
- **Licensing.** Open Data Commons Attribution License v1.0.

### 3.5 Porcine progressive exsanguination (IEEE DataPort, DOI 10.21227/qk4m-wy09; Zia, Kimball, Hahn, Rolfes, Inan 2020)

- **Animals and conditions.** 6 Yorkshire swine, 51.5-71.4 kg, 114-150 days; xylazine/Telazol induction, isoflurane maintenance, mechanical ventilation; heparin as needed; atropine given to one animal.
- **Protocol.** Blood drained via arterial line in 7 % steps of estimated total blood volume (Evans blue): baseline, 7, 14, 21, 28 %, with 5-10 min stabilisation per level; termination at a 20 % fall in mean aortic pressure (collapse at 21 % in three animals, 28 % in two, 14 % in one). Re-infusion not described.
- **Measurements.** Aortic root, femoral, right atrial and left atrial (wedge) pressures at 2 kHz; ECG, SCG, PPG at 2 kHz. **No cardiac output or aortic flow.**
- **Compatibility.** The only candidate where the perturbation (volume removal) maps one-to-one onto a model input (total blood volume) with known magnitude, and where aortic-root pressure (the model's `P_sa` site) is measured directly. Lacking flow, SV must be treated as unobserved; the experiment becomes a pressure-response falsification test (Section 10, E2). Intact baroreflex is a known, dominant confound (Section 6).
- **Licensing.** Listed as open access to logged-in users with a free IEEE account; the page also says a subscription is required; no licence named. Must be clarified in writing before use.

### 3.6 Autonomic Aging (PhysioNet 1.0.0)

1,121 healthy volunteers, 18-92 years (released in 15 age groups), Jena University Hospital; ECG and continuous non-invasive BP (CNSystems CNAP 500 or Task Force Monitor) at 1,000 Hz; supine rest 8-45 min; ODbL v1.0. No flow, no invasive pressure, no perturbation. Use: healthy-population distribution of non-invasive MAP/DBP/HR and pulse shape for population-based plausibility only.

### 3.7 Cerebral Vasoregulation in Elderly with Stroke (PhysioNet `cves` 1.0.0, DOI 10.13026/C2DW96)

60 ischaemic-stroke and 60 control subjects; head-up tilt and sit-to-stand with ABP (non-invasive), ECG and transcranial Doppler at 500 Hz; ODC-By. No CO. Use: orthostatic perturbation in conscious humans, which the model cannot represent without a reflex; falsification-only.

### 3.8 EchoNet-Dynamic (Stanford AIMI; Ouyang et al., Nature 2020)

10,030 apical-four-chamber echocardiogram videos with expert EF, EDV, ESV and endocardial tracings, Stanford 2016-2018. Research Use Agreement: non-commercial, no redistribution, no derivative works, individual registration. No pressure, no flow. Use: population distribution of LV volumes and EF for plausibility; not for patient-specific validation.

### 3.9 Published population reference values (literature, no data access)

- Kawel-Boehm et al. 2020 CMR reference ranges (pooled, by sex and age decile): LV and RV EDV/ESV/SV/EF (Section 1.7).
- Kovacs et al. 2009: resting mPAP 14.0 +/- 3.3 mmHg in 1,187 healthy subjects; mild-exercise values by age.
- 2022 ESC/ERS pulmonary-hypertension definitions (Humbert 2022).
- 2017 ACC/AHA blood-pressure categories (Whelton 2018).
- Cattermole et al. 2017: USCOM Doppler normal ranges, 2,218 healthy subjects aged 0.5-89 (numeric ranges not retrieved here).

### 3.10 Prior model-specific animal validation (data not public)

Revie et al. 2013 (CMPB 109:197) validated subject-specific Smith-family models in five pigs with acute pulmonary embolism using continuous aortic and PA pressure plus LV/RV pressure-volume catheters; inputs (GEDV, SV, Pao, Ppa) matched to <0.5 % error and held-out ventricular pressures/volumes predicted to within stated percentage errors. Revie et al. 2013 (porcine septic shock, PMC3621159) reports held-out LV/RV EDV and peak pressures within 20 % percentage error, R^2 > 0.76. These establish precedent for the calibrate-on-subset/predict-the-rest design (Section 5) and the magnitude of error achieved by a richer model with the same lineage; they are not reusable data.

### 3.11 Simulation-generated databases (excluded as validation targets)

Charlton et al. 2019 pulse-wave database: 4,374 virtual subjects, pressure/flow/area/PPG at several sites, 500 Hz, generated by a 1-D model; database licence not stated on the project page. Permitted use here: a *baseline* for site-transfer assumptions and a sanity check of how a lumped model's waveform differs from a propagating one. Agreement with it is model-to-model agreement and is never counted as validation (task restriction and FDA category distinctions).

---

## 4. Measurement compatibility and gap analysis

### 4.1 Compatibility by observable

| Observable | Best human source | Best animal source | Independent? | Gap |
|---|---|---|---|---|
| MAP, DBP, arterial waveform | VitalDB ART (3,645), MIMIC ABP | Porcine aortic root | Yes | Site transfer radial to central not identifiable from the data; use MAP/DBP as primary |
| SV, CO | VitalDB Vigilance (65), CardioQ (29); SCG-RHC thermodilution/Fick (83) | none in candidates | Yes (these three); No (EV1000/Vigileo) | Beat-resolved aortic flow is available only as Doppler velocity in 27 cases |
| Mean PAP | VitalDB PA_MBP (81); SCG-RHC | none | Yes | Small n; intrathoracic pressure not measured |
| PCWP / `P_pv` | SCG-RHC | Porcine LA | Yes | No atrium in model; VitalDB lacks wedge |
| CVP / `P_sv` | VitalDB CVP (1,586); SCG-RHC RAP | Porcine RA | Yes | Transducer level error comparable to signal |
| LV EDV/ESV/EF | none simultaneous with pressure | none | - | **Gap:** no candidate provides LV volumes with pressure; patient-specific LV volume validation is not possible with current candidates |
| RV EDV/ESV/EF | VitalDB Vigilance volumetrics (49) | none | Yes | Device method; small n |
| LV, RV pressure waveform | none | none in candidates (Revie-type data not public) | - | **Gap:** ventricular pressure is unobservable; `emin`/`emax` are identified only through their downstream effects |
| Controlled perturbation with known magnitude | SCG-RHC vasodilator (dose known, parameter change unknown) | Porcine graded hemorrhage (volume removed known) | Yes | Human volume or resistance changes of known magnitude do not exist in the candidates |

### 4.2 Structural gaps that no candidate dataset closes

1. No human dataset has simultaneous aortic-root pressure, aortic flow and ventricular volume. Patient-specific validation of the LV pressure-volume loop is therefore impossible; only its projections (SV, EDV/ESV population ranges) are testable.
2. No candidate measures intrathoracic pressure; all invasive ventilated recordings contain a respiratory component the model cannot represent. All comparisons must be beat-averaged over whole ventilatory cycles, declared in advance.
3. Independent CO in VitalDB exists in 65 + 29 cases; everything at larger n uses pulse-contour CO derived from the pressure waveform. Any experiment using pulse-contour CO must label it as a transformed pressure observation, not a flow observation.
4. Absolute unstressed volumes and absolute compartment volumes are unobservable in every candidate; only stressed volume (`V_total - sum(V0)`) can be constrained (Section 5).

---

## 5. Parameter identifiability and calibration strategy

### 5.1 Parameters, inputs, and what measurements constrain them

With HR imposed, 17 free quantities remain: `emin_lv`, `emax_lv`, `emin_rv`, `emax_rv`, `systolic_fraction`, `C_sa`, `C_sv`, `C_pa`, `C_pv`, `R_aortic`, `R_systemic`, `R_tricuspid`, `R_pulmonary_valve`, `R_pulmonary`, `R_mitral`, six `V0` and total volume. Known structural facts (from the equations, not from data):

- Pressures depend on `V_i - V0_i`; with total volume fixed, a shift of volume between `V0_i` entries and initial volumes leaves the periodic solution unchanged. Only total stressed volume is structurally identifiable from pressures; the six `V0` are not separately identifiable. This is the same conclusion reached for the seven-parameter Smith-derivative model (Pironet 2019: total stressed blood volume is the identifiable quantity) and for a closed-loop systemic model (Bjørdalsbakke 2022: `C_sv` and `V_tot` least identifiable without venous pressure).
- Valve resistances (default 0.01 mmHg s/mL) produce pressure drops of about 1 mmHg at peak flow; they are expected to be practically non-identifiable from pressure data and must be fixed a priori, not estimated.
- Right-sided parameters (`emin_rv`, `emax_rv`, `C_pa`, `C_pv`, `R_pulmonary`) are unidentifiable from systemic pressure and CO alone; they require PAP and/or wedge/CVP.
- `systolic_fraction` and `emax_lv` both shape the ejection; separability requires either the pressure waveform (timing of upstroke and end of ejection) or a flow waveform.

### 5.2 Identifiability procedure (to be executed before any calibration)

1. **Structural identifiability** of the periodic-solution map from the chosen observable set, by symbolic or differential-algebra analysis on the smooth-regime equations (precedent: IFAC 2014 structural analysis of the Smith-family model; Marquis 2018: structural identifiability is a prerequisite for practical identifiability). Output: the identifiable parameter combinations per observable set, recorded before data are opened.
2. **Local sensitivity and collinearity** of the observables to each parameter at several nominal points, followed by subset selection (Marquis 2018 workflow; Bjørdalsbakke 2022 step-wise subset reduction).
3. **Practical identifiability** by profile likelihood on synthetic data generated by the model itself with the measurement noise model of Section 7 (Pironet 2019). Synthetic-data recovery is a calibration-method check, not validation; it is FDA category 2 evidence at most.
4. **Prior fixing.** Parameters found non-identifiable are fixed at declared values with a declared source, and their effect is carried as input uncertainty (Section 7), never tuned to data.

Expected result, stated now so it can be refuted: from VitalDB-type data (ART waveform, CVP, independent CO), the identifiable subset is of order five to seven parameters (`emax_lv`, `systolic_fraction`, `C_sa`, `R_systemic`, total stressed volume, and with CVP, `C_sv`; with PAP, `R_pulmonary` and `emax_rv`), in line with Pironet 2019 (four of seven identifiable from pressures plus SV) and Bjørdalsbakke 2022 (five most sensitive parameters to within 10 % at 5 % noise).

### 5.3 Initial conditions and transient

Initial volumes are not calibration parameters: the first beats are an initialisation transient. Every calibration and prediction uses only beats after the periodicity criterion of `docs/verification_protocol.md` is met at the fine solver settings recorded in `docs/physiology.md`. The numerical settling error must be at least one order of magnitude below the measurement uncertainty of the compared quantity; otherwise the comparison is INCONCLUSIVE, not a pass.

### 5.4 Four distinct activities, never conflated

| Activity | Data used | Output | Claim permitted |
|---|---|---|---|
| Parameter estimation | Calibration window of subject *i* | Parameter estimates with uncertainty | "The model can be fitted"; no predictive claim |
| Calibration fit | Same window | Residuals of the fitted quantities | Goodness of fit only; FDA category 2 (model calibration evidence) |
| Independent validation | Held-out window or held-out quantity of subject *i*, or held-out subject | Prediction error with uncertainty | Predictive performance within the COU |
| Extrapolation | Conditions outside the calibration ranges or outside Section 1.2 | Reported separately, labelled extrapolation | None beyond "observed behaviour" |

### 5.5 Separation rules (pre-registered)

- **Within-subject temporal split:** calibrate on window W1 (stationary, declared by rule: no infusion change, no EMR event, HR within +/-5 % for at least 60 s), predict on W2 after a perturbation. The perturbation input to the model is *measured* (HR, removed blood volume) or *estimated from a single declared observable* (for vasodilator: `R_systemic` and `V0_sv` from the MAP and CVP change only), and the prediction is scored on the remaining observables.
- **Within-subject quantity split:** calibrate on pressures, predict independent CO; never calibrate on CO and score pressures in the same report without labelling both directions.
- **Between-subject split:** population-level parameter priors are learned on subject set S1 and applied to subject set S2 (leave-one-subject-out); subject-level dependence is respected in all intervals (Section 7).
- **Sealing:** window definitions, subject lists and all thresholds are hashed and recorded before any trajectory is simulated against data.
- **Patient-specific claim gate:** a patient-specific validation claim requires at least HR, arterial pressure and one independent flow measurement (Section 1.5). VitalDB cases with only pulse-contour CO support waveform-level validation only.

---

## 6. Independent validation protocol: experiments A to F

Each experiment specifies the eleven required elements. Acceptance criteria are sourced or explicitly report-only. "Baseline" means the comparator model against which the physics model must do better to be considered informative.

### A. Baseline haemodynamic behaviour (per-subject, stationary)

- **Hypothesis.** With parameters estimated from a subject's arterial pressure waveform and CVP in window W1, the model predicts the subject's independently measured CO in W1 within the agreement expected of an accepted clinical CO technique.
- **Observables.** CO (primary); MAP, DBP (fit diagnostics); mPAP where available.
- **Reference data.** VitalDB cases with ART + CVP + `Vigilance/CO` (up to 60 with PA pressures) and ART + `CardioQ/CO` (27); SCG-RHC baseline segments (83).
- **Conditions.** Anaesthetised, ventilated (VitalDB) or catheter-lab (SCG-RHC); stationary window rule of 5.5; HR imposed from the record.
- **Mapping.** `P_sa` mean and min to radial MAP and DBP; `P_sv` mean to CVP mean; CO to thermodilution/Fick/Doppler CO averaged over the same window.
- **Calibration parameters.** The identifiable subset from 5.2; all others fixed with declared values.
- **Held-out procedure.** CO is never used in calibration; quantity split (5.5).
- **Metrics.** Bland-Altman bias and 95 % limits of agreement for CO across subjects with subject-level clustering (Bland and Altman 1999 repeated-measures extension; mixed-effects limits of agreement, Parker 2016); percentage error = 1.96 SD / mean reference CO (Critchley 1999); MAE and RMSE of MAP/DBP as fit diagnostics.
- **Measurement uncertainty.** Thermodilution +/-20 % precision assumed (Critchley 1999); Doppler wider; CO averaging interval declared.
- **Model discrepancy.** Reported as the residual after subtracting the measurement variance (Section 7).
- **Acceptance / failure (pre-registered).** Percentage error for CO <= 30 % (Critchley 1999 limit; the 2009 Critical Care critique notes this depends on reference precision, so the reference's precision is reported alongside). Failure: percentage error > 30 % or bias whose 95 % CI excludes zero and exceeds the reference precision. The threshold is a device-agreement criterion borrowed as the only published quantitative CO criterion; it is not a claim that the model is a device.

### B. Arterial pressure waveform agreement

- **Hypothesis.** The model's `P_sa(t)`, after per-subject calibration, reproduces the beat-averaged radial waveform better than a two-element Windkessel driven by the measured flow (baseline 1) and better than the subject's own mean-shape template from W1 applied to W2 (baseline 2).
- **Observables.** Ensemble-averaged beat waveform in W2; systolic upstroke time, ejection duration (from Doppler `CardioQ/FTc` where present), pulse pressure.
- **Reference data.** VitalDB ART 500 Hz; MIMIC ABP 125 Hz (morphology at scale); porcine aortic root (the only site matching the model's lumped arterial node).
- **Conditions.** As A; beats ensemble-averaged over integer ventilatory cycles.
- **Mapping.** Radial waveform compared on MAP-aligned, time-normalised beats; central (porcine aortic-root) waveform compared directly.
- **Calibration parameters.** As A, estimated on W1 beats.
- **Held-out procedure.** Temporal split W1 -> W2.
- **Metrics.** RMSE and normalised RMSE of the ensemble beat; timing error of the systolic peak and of ejection end; explicit statement that the dicrotic notch is absent by construction (not scored); dynamic-time-warping distance as a secondary report-only shape metric.
- **Measurement uncertainty.** Transducer damping unquantified; sampling 500 Hz adequate.
- **Model discrepancy.** Expected systematic: missing notch, missing amplification, triangular ejection shape from the cosine pulse.
- **Acceptance / failure (pre-registered).** No published absolute waveform threshold exists for a lumped model. Criterion: the model's nRMSE must be lower than both baselines in at least the declared majority of subjects (binomial test, alpha 0.05, pre-registered); otherwise REFUTED for waveform morphology. Absolute nRMSE is report-only.

### C. Cardiac output and stroke-volume agreement (population and site)

- **Hypothesis.** Across subjects, the model's SV from calibrated pressure data agrees with independent SV within the device-agreement limit, and its EDV/ESV fall within published population ranges.
- **Observables.** SV, CO; LV EDV, ESV, EF (population only); RV EDV, ESV, RVEF (VitalDB Vigilance).
- **Reference data.** As A for SV/CO; Kawel-Boehm 2020 CMR ranges and EchoNet-Dynamic for population EF/EDV/ESV distributions; `Vigilance/EDV`, `ESV`, `RVEF` (49 cases).
- **Conditions, mapping, calibration, held-out.** As A; RV volumetrics are never used in calibration.
- **Metrics.** Bland-Altman with subject clustering and percentage error (A); fraction of subjects whose predicted LV EDV/ESV/EF lie inside the sex-specific CMR 95 % ranges (population plausibility, FDA category 7); RV EDV/ESV MAE and RMSE report-only.
- **Measurement uncertainty.** As A; CMR ranges carry pooled SD; device RVEF uncertainty not retrieved (secondary).
- **Model discrepancy.** No atria; linear passive law.
- **Acceptance / failure.** SV/CO: as A. LV volumes: report-only (no simultaneous measurement exists; population range inclusion is plausibility, not validation). RV: report-only.

### D. Responses to physiological perturbations (trending)

- **Hypothesis D1 (volume).** Removing the measured blood volume, with measured HR imposed, predicts the direction and magnitude of change of mean aortic pressure, RA and LA pressure at each hemorrhage level (porcine). **D2 (vasodilator).** With `R_systemic` and `V0_sv` re-estimated from the MAP and RAP change only, the model predicts the direction and magnitude of change of PCWP, mPAP and CO (SCG-RHC). **D3 (vasopressor).** With `R_systemic` re-estimated from the MAP change only during a phenylephrine or norepinephrine infusion, the model predicts the CVP and (where present) CO change (VitalDB).
- **Observables.** Deltas of the named quantities between stationary windows.
- **Reference data.** Porcine exsanguination (6 animals, up to 4 levels); SCG-RHC (83 procedures); VitalDB infusion tracks (phenylephrine 127, norepinephrine 88, NTG 32).
- **Conditions.** Stationary windows before and after; perturbation magnitude from protocol (porcine) or inferred from one declared observable (human).
- **Mapping.** As Sections 2 and 4; porcine aortic root maps directly to `P_sa`.
- **Calibration parameters.** Identifiable subset on the pre-window; only the declared perturbation parameter(s) change.
- **Held-out procedure.** Every scored observable is excluded from the perturbation-parameter inference.
- **Metrics.** Four-quadrant concordance rate with the published exclusion zone (changes < 0.5 L/min or < 10 % excluded) and polar-plot mean angle and radial limits (Critchley 2010, 2011); sign agreement per subject and level; magnitude error as bias and limits of agreement of deltas.
- **Measurement uncertainty.** As A; hemorrhage volume uncertainty from the Evans-blue estimate (not retrieved; to be taken from the dataset documentation).
- **Model discrepancy.** Dominant and expected: intact baroreflex and venoconstriction in animals and humans. Burkhoff and Tyberg 1993 showed, in a reflex-free elastance model of the same family, that a 50 % Ees reduction raised pulmonary venous pressure only from 12 to about 15 mmHg, and that large rises required venous unstressed-volume reduction; the present model will show the same behaviour, so a measured PCWP rise larger than predicted is an expected, documented discrepancy, not evidence for or against the model's pump mechanics.
- **Acceptance / failure (pre-registered).** Trending: concordance >= 90-95 % outside the exclusion zone and polar radial limits within +/-30 degrees with mean angle within +/-5 degrees (Critchley 2011). D1 is additionally a falsification test: because HR is imposed from the animal and systemic resistance is held at its pre-hemorrhage value, the model is *expected* to over-predict the MAP fall at 21-28 % loss; the pre-registered success condition is correct sign at every level and magnitude agreement only at the first level (7 %), with the divergence at higher levels reported as the quantified effect of the missing reflex. Any result in which the reflex-free model matches late-stage MAP would itself be suspicious and must be investigated, not celebrated.

### E. Reproducibility across independent subjects and experiments

- **Hypothesis.** Validation performance (A, C, D) is stable across subjects, surgical departments, devices and datasets, and the identifiable parameters are more variable between subjects than within a subject across windows.
- **Observables.** Per-subject metrics from A to D; parameter estimates across repeated stationary windows within a case.
- **Reference data.** VitalDB stratified by department and CO device; SCG-RHC; MIMIC for pressure-only replication; porcine for animal replication.
- **Conditions.** As the parent experiments.
- **Mapping, calibration.** As parent experiments; between-subject split of 5.5 for priors.
- **Held-out procedure.** Leave-one-subject-out for priors; replication on a second dataset after the first is sealed.
- **Metrics.** Interquartile ratio of within-subject versus between-subject parameter estimates (Bjørdalsbakke 2023 precedent); heterogeneity of per-subject bias across strata (mixed-effects variance components, Parker 2016, 2020).
- **Measurement uncertainty, discrepancy.** Inherited.
- **Acceptance / failure.** Report-only for heterogeneity; failure if the A/D criteria pass in one dataset and fail in the replication dataset (declared REFUTED for generalisation).

### F. Sensitivity to parameter and measurement uncertainty

- **Hypothesis.** The prediction intervals produced by propagating parameter and input uncertainty (Section 7) are calibrated: the declared coverage is achieved on held-out observations.
- **Observables.** Coverage of 95 % prediction intervals for CO, MAP, mPAP deltas.
- **Reference data.** Held-out windows and subjects from A to D.
- **Metrics.** Empirical coverage with Wilson interval; Sobol first-order and total indices of each observable to each parameter (Eck 2016 six-step guide; Monte Carlo or polynomial chaos).
- **Acceptance / failure.** Coverage CI must include the nominal 95 %; under-coverage means the uncertainty model is REFUTED and must be widened (not the thresholds).

---

## 7. Uncertainty quantification methodology

1. **Measurement uncertainty model** (per observable, declared before data are opened): thermodilution CO relative SD from the +/-20 % precision assumption (Critchley 1999); pulse-contour CO treated as non-independent and not used as a reference; arterial pressure transducer uncertainty taken from the dataset documentation where available, otherwise a declared conservative value with its source; CVP/PAP level uncertainty declared; respiratory variation removed by whole-cycle averaging and the residual carried as uncertainty.
2. **Parameter uncertainty:** from profile likelihood or Bayesian posterior at calibration (Pironet 2019; Marquis 2018 frequentist and Bayesian UQ), including fixed non-identifiable parameters with declared prior ranges.
3. **Propagation:** Monte Carlo or polynomial chaos through the model to prediction intervals (Eck 2016); global variance-based sensitivity (Sobol) reported per observable.
4. **Numerical uncertainty:** the solver settling and tolerance uncertainties already characterised in `docs/physiology.md` and `docs/verification/model_verification_methodology_v1.md` are added in quadrature and must be negligible relative to 1 and 2 for each quantity; if not, INCONCLUSIVE.
5. **Model discrepancy:** an explicit per-observable discrepancy term (the residual variance not explained by 1, 2 and 4), reported separately so that missing physics is visible rather than absorbed into parameters. No numeric target.
6. **Calibration of uncertainty:** empirical coverage on held-out data (Experiment F). Intervals that are too narrow are a failure of the uncertainty model, which is corrected by widening the declared inputs, never by relaxing acceptance thresholds.
7. **Dependence:** all intervals across subjects use subject as a random effect (Bland and Altman 1999; Parker 2016, 2020); beats within a window are not independent and are ensemble-averaged, not counted.

---

## 8. Quantitative acceptance criteria (pre-registered, sourced)

| Quantity | Criterion | Source of the number or procedure | Status |
|---|---|---|---|
| CO / SV agreement vs thermodilution or Fick (A, C) | Percentage error (1.96 SD of difference / mean reference) <= 30 %; bias CI reported with reference precision | Critchley and Critchley 1999 (limits up to +/-30 % acceptable given +/-20 % reference precision); caveat from Cecconi et al. 2009 (PE depends on reference precision) | Sourced; borrowed device criterion |
| CO trending under perturbation (D) | Four-quadrant concordance >= 90-95 % with exclusion zone < 0.5 L/min or < 10 %; polar mean angle within +/-5 degrees, radial limits +/-30 degrees | Critchley 2010 review; Critchley 2011 polar-plot criteria | Sourced |
| MAP / DBP agreement (A, B) | Report-only: bias and SD of differences, with subject clustering | No published model-vs-measurement threshold. The non-invasive sphygmomanometer standard ISO 81060-2 (criterion 1: mean difference within +/-5 mmHg, SD <= 8 mmHg, n >= 85 subjects) was seen only in secondary sources this session and is a device standard; it is listed as a *candidate* benchmark to be adopted only after the standard's text is read | Candidate, not adopted |
| Waveform morphology (B) | Model nRMSE lower than both declared baselines in a pre-registered majority of subjects (binomial test, alpha 0.05) | Comparison-to-baseline principle (FDA guidance credibility factors; Bjørdalsbakke 2022 waveform versus index cost functions) | Sourced procedure, no absolute number |
| LV EDV / ESV / EF plausibility (C) | Fraction inside sex-specific CMR mean +/- 2 SD ranges, report-only | Kawel-Boehm 2020 | Reference range; plausibility only |
| mPAP plausibility (healthy-population checks) | Within 14.0 +/- 2 x 3.3 mmHg for healthy subjects; PH threshold > 20 mmHg | Kovacs 2009; Humbert 2022 | Reference range; plausibility only |
| Prediction-interval coverage (F) | Wilson 95 % CI of empirical coverage includes 0.95 | Standard coverage test; nominal level declared here | Procedure sourced; level declared |
| Numerical adequacy for any comparison | Settling plus tolerance uncertainty at least 10x smaller than measurement uncertainty of the compared quantity, else INCONCLUSIVE | Project rule consistent with decisions.md entry of 2026-11-01 (no universal verification threshold; level set by context of use) | Project rule, declared here |

Nothing in this table may be altered after results are seen. Any experiment whose quantity has no sourced threshold is reported with its metric and uncertainty and the word "report-only"; it is never described as passed.

---

## 9. Scientific limitations and unsupported claims

**Exploratory, unfitted parameters.** Every default is an author choice (`docs/physiology.md`). Consequence: the baseline run carries no evidential weight; all validation is on per-subject calibrated parameter sets, and the identifiable subset is expected to be small (5.2). Non-identifiable parameters fixed at defaults inject unquantified structural bias, which is why they are carried as input uncertainty.

**Elevated-pressure baseline.** 163/105 mmHg systemic, mPAP 23.8 mmHg: a hypertensive, mildly pulmonary-hypertensive computational state. It is a starting point for calibration only; any plot of baseline waveforms against human data would compare a non-subject to a subject and is forbidden by this protocol.

**Ideal-diode valves.** No inertia, no regurgitation, no gradual opening; no dicrotic notch; instantaneous closure. Consequence: ejection-end timing, early-diastolic pressure morphology and valve-event timing are excluded from scored metrics (B) and declared as expected discrepancy. Smith 2004's open-on-pressure/close-on-flow law is explicitly not implemented, so agreement with Smith-family results on valve-timing quantities is not expected.

**Simplified compartment structure.** No atria (so CVP, PCWP map to reservoirs, not chambers); one systemic arterial node (no site specificity); shared LV/RV activation phase and width; linear passive laws (no end-diastolic stiffening, so EDV predictions at high filling pressure will be biased).

**Missing feedback.** No baroreflex, no venous tone control, no renal volume regulation, no respiration. Consequence: every perturbation experiment in intact subjects (D) tests the model *and* the missing reflex together; the design separates them only by imposing measured HR and by pre-registering the expected divergence. Agreement under hemorrhage beyond the first level would be anomalous.

**Location differences.** Radial versus central pressure (amplification, notch); PCWP versus pulmonary venous reservoir; CVP versus lumped veins; descending-aortic Doppler versus total aortic flow; right-sided thermodilution versus left-sided ejection. Each is declared in Section 2 and limits the scored quantity (MAP/DBP primary, SBP site-biased).

**Clinical versus simulated conditions.** Anaesthesia, positive-pressure ventilation, surgical stimulation, vasoactive infusions, fluid shifts, temperature; none is in the model. VitalDB and MIMIC perturbations are uncontrolled and their timing is known only approximately (EMR at 5-minute granularity).

**Unsupported claims (must not appear in any downstream text).** "The model is physiologically validated"; "the baseline represents a healthy adult"; "reduced-contractility scenario represents heart failure"; "the pulmonary venous pressure rise indicates pulmonary oedema"; "agreement with Smith 2004 / Charlton 2019 / Pulse / CircAdapt validates the model" (model-to-model agreement is not empirical validation); "patient-specific prediction" for any VitalDB case lacking independent CO; "regulatory-grade credibility" or "V&V 40 compliant"; any claim about drug effects.

**Plausible-looking waveforms and passing tests** are explicitly disqualified as evidence (task restriction; FDA categories: those are at best model plausibility and code verification).

---

## 10. Three minimal, high-information validation experiments

Ranked by information per unit of resource. Each can refute a specific claim.

### E1. VitalDB Vigilance subset: calibrate on pressures, predict thermodilution CO and right-ventricular volumetrics

- **What it tests.** Experiments A and C in their strongest human form: up to 60 cases with 500 Hz radial ART, CVP (subset), PA pressures (2 s), continuous-thermodilution CO, and RV EDV/ESV/RVEF (about 49 cases), none of which is derived from the pressure waveform.
- **Design.** Per case: stationary W1 (rule of 5.5) -> estimate the identifiable subset from ART waveform, CVP mean, PA mean -> predict CO (never used in fitting) and RV EDV/ESV -> score with percentage error and Bland-Altman with case clustering. Replicate on a later stationary W2 for within-case reproducibility (E).
- **Claims it can refute.** "Calibrated pressures predict flow within clinical-device agreement" (PE > 30 %); "the right ventricle is representable by a linear elastance chamber" (RV volume error report).
- **Prerequisites.** Identifiability analysis of 5.2 completed and sealed; window rule, subject list and thresholds hashed; VitalDB DUA acknowledged and PhysioNet CC BY attribution recorded; beat segmentation and artefact rejection code written and tested on synthetic data; ventilatory-cycle averaging implemented; a declared measurement-uncertainty table.
- **Resources.** About 60 cases x roughly 2.8 million data points per case (VitalDB average) of local storage, a few GB; thousands of 60-cycle model solves per case for calibration and UQ (seconds each at the fine settings), feasible on one workstation; a physiologist or anaesthesiologist to adjudicate window selection blind to model output; the `vitaldb` Python client or WFDB tooling (an installation, which this task forbids and which therefore gates the experiment).

### E2. Porcine graded hemorrhage: known volume removed, measured HR imposed, predict aortic-root, RA and LA pressure changes

- **What it tests.** Experiment D1: the only candidate in which the perturbation is a model input of known magnitude and the arterial site matches the model node exactly. It is designed to *fail at high blood loss* in a quantified way, measuring the contribution of the missing reflex.
- **Design.** Per animal: calibrate on baseline aortic-root waveform, RA and LA mean pressures (HR from ECG); for each level, reduce total volume by the protocol fraction, impose the measured HR, hold all other parameters; predict MAP, RA, LA changes; score sign per level and magnitude at 7 %; report the divergence trajectory at 14-28 % against the reflex-free expectation.
- **Claims it can refute.** "A conserved-volume elastance model predicts the first-level pressure response to volume loss" (sign or magnitude failure at 7 %); and, informatively, it bounds the reflex effect that any future baroreflex module must reproduce.
- **Prerequisites.** Written clarification of the IEEE DataPort licence (page is contradictory) and a free IEEE account; the Evans-blue volume uncertainty from the dataset documentation; 2 kHz processing pipeline; declaration that SV is unobserved (no flow channel) so CO predictions are report-only.
- **Resources.** Six animals, at most 24 level-windows: small data (tens of GB at 2 kHz over hours; subsample to windows); negligible compute; one reviewer to confirm level timings from the pressure trace blind to model output.

### E3. SCG-RHC vasodilator challenge: infer resistance change from MAP and RAP, predict PCWP, mPAP and CO change

- **What it tests.** Experiment D2 in the only human dataset with wedge, RA, PA and independent (Fick and thermodilution) CO around a documented pharmacological perturbation. Heart-failure population: a stress test of the no-atrium, linear-passive assumptions at high filling pressures.
- **Design.** Per procedure: calibrate on baseline PAP, PCWP, RAP, ABP and CO (CO used here because the scored quantity is its *change*; the within-quantity split is on deltas); infer the vasodilator's effect as changes in `R_systemic` and `V0_sv` from MAP and RAP deltas only; predict PCWP, mPAP and CO deltas; score by concordance, polar plot and delta limits of agreement.
- **Claims it can refute.** "Vasodilator responses of left-sided filling pressure follow from systemic resistance and venous capacitance changes in a lumped model" (concordance < 90 %); it also quantifies the PCWP discrepancy that Burkhoff and Tyberg 1993 attributed to venous unstressed-volume shifts.
- **Prerequisites.** Pressure-channel inventory of the Mac-Lab files (confirm ABP presence per procedure); declared end-expiratory or whole-cycle averaging rule; ODC-By attribution; the identifiability result for the right-sided parameter subset with PAP and PCWP available.
- **Resources.** 83 procedures at 500 Hz processed WFDB, modest storage; compute as E1; a cardiologist or physiologist to adjudicate baseline/post windows and vasodilator timing blind to model output.

**Deliberately not proposed as minimal experiments:** pulse-contour-CO-based studies at large n (non-independent); MIMIC-based studies before PAP/CVP channel inventory; any use of the Charlton 2019 database as a target; any LV pressure-volume loop comparison (no data).

---

## 11. Review checklist for the independent reviewer

1. Is every scored observable in Section 6 mapped in Section 2 with a declared site and reference caveat?
2. Is every numeric criterion in Section 8 traceable to a cited source or marked report-only?
3. Is any dataset in Section 3 described from secondary sources only? (Marked where so: Vigilance RVEF uncertainty; ISO 81060-2 criteria; Cattermole ranges; porcine Evans-blue uncertainty.)
4. Does any experiment use the same observation for calibration and scoring? (Intended answer: no; E3 uses CO level in calibration and CO *delta* in scoring, which the reviewer should confirm is acceptable or require removal of CO from calibration.)
5. Is the expected failure of D1/E2 at high blood loss stated before data are seen? (Yes, Sections 6.D and 10.E2.)

---

## Sources

Dataset and documentation pages (read 2026-11-03):

- VitalDB on PhysioNet: https://physionet.org/content/vitaldb/1.0.0/ (CC BY 4.0; cohort, device, IRB, quality statements). VitalDB documentation: https://vitaldb.net/dataset/ (device table, dataset summary). VitalDB examples repository README (Data Use Agreement requirement): https://raw.githubusercontent.com/vitaldb/examples/master/README.md. Track index: https://api.vitaldb.net/trks (retained counts in `docs/evidence/e_vitaldb_track_case_counts_2026-11-03.tsv`).
- Lee HC, Park Y, Yoon SB, et al. VitalDB, a high-fidelity multi-parameter vital signs database in surgical patients. Sci Data 2022;9:279. https://doi.org/10.1038/s41597-022-01411-5 (PubMed metadata).
- MIMIC-III Waveform Database Matched Subset 1.0: https://physionet.org/content/mimic3wdb-matched/1.0/ ; parent database (125 Hz, numerics interval): https://physionet.org/content/mimic3wdb/1.0/
- MIMIC-IV Waveform Database 0.1.0: https://physionet.org/content/mimic4wdb/0.1.0/
- SCG-RHC 1.0.0: https://physionet.org/content/scg-rhc-wearable-database/1.0.0/ (DOI 10.13026/133d-pk11). Shandhi MMH, et al. IEEE Trans Biomed Eng 2022;69(8):2443-2455, https://doi.org/10.1109/TBME.2022.3147066 (seen via search summary and PMC listing; not read in full).
- Porcine exsanguination dataset: https://ieee-dataport.org/open-access/wearable-and-catheter-based-cardiovascular-signals-during-progressive-exsanguination (DOI 10.21227/qk4m-wy09).
- Autonomic Aging 1.0.0: https://physionet.org/content/autonomic-aging-cardiovascular/1.0.0/
- Cerebral Vasoregulation in Elderly with Stroke 1.0.0: https://physionet.org/content/cves/1.0.0/
- EchoNet-Dynamic: https://echonet.github.io/dynamic/ ; Ouyang D, et al. Nature 2020;580:252-256, https://doi.org/10.1038/s41586-020-2145-8 (PubMed metadata).
- Charlton PH, et al. Am J Physiol Heart Circ Physiol 2019;317(5):H1062-H1085, https://doi.org/10.1152/ajpheart.00218.2019 (PubMed metadata); project page https://peterhcharlton.github.io/pwdb/ (no licence stated).

Frameworks and guidance:

- FDA, Assessing the Credibility of Computational Modeling and Simulation in Medical Device Submissions, final guidance, CDRH, November 2023, docket FDA-2021-D-0980: https://www.fda.gov/regulatory-information/search-fda-guidance-documents/assessing-credibility-computational-modeling-and-simulation-medical-device-submissions. FDA webinar slides, 11 January 2024 (nine-step framework, eight evidence categories, ASME V&V 40-2018 definitions): https://www.fda.gov/media/175363/download (text extracted locally this session; the guidance PDF itself was not parsed).
- ASME V&V 40-2018, Assessing Credibility of Computational Modeling through Verification and Validation: Application to Medical Devices (cited through the FDA guidance; the ASME page was not reachable this session).
- Pathmanathan P, Gray RA, Romero VJ, Morrison TM. Applicability analysis of validation evidence for biomedical computational models. J Verif Valid Uncert 2017;2(2), https://doi.org/10.1115/1.4037671 (citation from OSTI record).
- Viceconti M, et al. In silico trials: verification, validation and uncertainty quantification of predictive models used in the regulatory evaluation of biomedical products. Methods 2021;185:120-127, https://doi.org/10.1016/j.ymeth.2020.01.011 (PubMed abstract).
- Erdemir A, et al. Credible practice of modeling and simulation in healthcare: ten rules from a multidisciplinary perspective. J Transl Med 2020;18:369, https://doi.org/10.1186/s12967-020-02540-4 (PubMed abstract).

Identifiability, calibration and uncertainty:

- Pironet A, Docherty PD, Dauby PC, Chase JG, Desaive T. Practical identifiability analysis of a minimal cardiovascular system model. Comput Methods Programs Biomed 2019;171:53-65, https://doi.org/10.1016/j.cmpb.2017.01.005 (PubMed abstract: four of seven parameters identifiable from arterial and venous pressures plus SV).
- Marquis AD, Arnold A, Dean-Bernhoft C, Carlson BE, Olufsen MS. Practical identifiability and uncertainty quantification of a pulsatile cardiovascular model. Math Biosci 2018;304:9-24, https://doi.org/10.1016/j.mbs.2018.07.001 (PubMed abstract).
- Bjørdalsbakke NL, Sturdy JT, Hose DR, Hellevik LR. Parameter estimation for closed-loop lumped parameter models of the systemic circulation using synthetic data. Math Biosci 2022;343:108731, https://doi.org/10.1016/j.mbs.2021.108731 (PubMed abstract).
- Bjørdalsbakke NL, Sturdy J, Ingeström EML, Hellevik LR. Monitoring variability in parameter estimates for lumped parameter models of the systemic circulation using longitudinal hemodynamic measurements. Biomed Eng Online 2023;22:34, https://doi.org/10.1186/s12938-023-01086-y (PMC full text, CC BY 4.0).
- Eck VG, Donders WP, Sturdy J, Feinberg J, Delhaas T, Hellevik LR. A guide to uncertainty quantification and sensitivity analysis for cardiovascular applications. Int J Numer Method Biomed Eng 2016;32(8):e02755, https://doi.org/10.1002/cnm.2755 (PubMed abstract).
- Revie JA, Stevenson DJ, Chase JG, et al. Validation of subject-specific cardiovascular system models from porcine measurements. Comput Methods Programs Biomed 2013;109(2):197-210, https://doi.org/10.1016/j.cmpb.2011.10.013 (PubMed abstract). Revie JA, et al. Evaluation of a model-based hemodynamic monitoring method in a porcine study of septic shock. Comput Math Methods Med 2013 (PMC3621159; full text retained in `docs/evidence/`).
- Burkhoff D, Tyberg JV. Why does pulmonary venous pressure rise after onset of LV dysfunction: a theoretical analysis. Am J Physiol 1993;265(5):H1819-H1828, https://doi.org/10.1152/ajpheart.1993.265.5.H1819 (PubMed abstract).
- Smith BW, Chase JG, Nokes RI, Shaw GM, Wake G. Minimal haemodynamic system model including ventricular interaction and valve dynamics. Med Eng Phys 2004;26(2):131-139, https://doi.org/10.1016/j.medengphy.2003.10.001 (PubMed abstract).
- Hann CE, Chase JG, Shaw GM. Efficient implementation of non-linear valve law and ventricular interaction dynamics in the minimal cardiac model. Comput Methods Programs Biomed 2005;80(1):65-74, https://doi.org/10.1016/j.cmpb.2005.06.003 (PubMed abstract).

Agreement statistics and acceptance criteria:

- Critchley LA, Critchley JA. A meta-analysis of studies using bias and precision statistics to compare cardiac output measurement techniques. J Clin Monit Comput 1999;15(2):85-91, https://doi.org/10.1023/a:1009982611386 (PubMed abstract: limits of agreement up to +/-30 % acceptable).
- Cecconi M, Rhodes A, Poloniecki J, Della Rocca G, Grounds RM. Bench-to-bedside review: the importance of the precision of the reference technique in method comparison studies. Crit Care 2009;13:201 (PMC2688094; seen via search summary).
- Critchley LA, Lee A, Ho AM. A critical review of the ability of continuous cardiac output monitors to measure trends in cardiac output. Anesth Analg 2010;111(5):1180-1192, https://doi.org/10.1213/ANE.0b013e3181f08a5b (PubMed abstract).
- Critchley LA, Yang XX, Lee A. Assessment of trending ability of cardiac output monitors by polar plot methodology. J Cardiothorac Vasc Anesth 2011;25(3):536-546, https://doi.org/10.1053/j.jvca.2011.01.003 (PubMed abstract: +/-5 degrees mean angle, +/-30 degrees radial limits, exclusion zone < 0.5 L/min or < 10 %).
- Slagt C, Malagon I, Groeneveld AB. Systematic review of uncalibrated arterial pressure waveform analysis to determine cardiac output and stroke volume variation. Br J Anaesth 2014;112(4):626-637, https://doi.org/10.1093/bja/aet429 (PubMed abstract).
- Bland JM, Altman DG. Measuring agreement in method comparison studies. Stat Methods Med Res 1999;8(2):135-160, https://doi.org/10.1177/096228029900800204 (PubMed abstract: repeated-measures extension).
- Parker RA, et al. Application of mixed effects limits of agreement in the presence of multiple sources of variability. PLoS One 2016 (seen via search summary; DOI not resolved this session). Parker RA, et al. BMC Med Res Methodol 2020;20:... (tutorial; https://doi.org/10.1186/s12874-020-01022-x, seen via search summary).
- ISO 81060-2 (AAMI/ESH/ISO universal standard) criterion 1 (+/-5 mmHg mean, <= 8 mmHg SD): seen only in secondary sources (trial registrations, FDA 510(k) summaries); not adopted.

Reference physiology:

- Kovacs G, Berghold A, Scheidl S, Olschewski H. Pulmonary arterial pressure during rest and exercise in healthy subjects: a systematic review. Eur Respir J 2009;34(4):888-894, https://doi.org/10.1183/09031936.00145608 (PubMed abstract).
- Humbert M, Kovacs G, Hoeper MM, et al. 2022 ESC/ERS Guidelines for the diagnosis and treatment of pulmonary hypertension. Eur Heart J 2022;43(38):3618-3731, https://doi.org/10.1093/eurheartj/ehac237 (PubMed metadata; PH threshold mPAP > 20 mmHg from general knowledge of the guideline, not re-read this session).
- Whelton PK, et al. 2017 ACC/AHA/AAPA/ABC/ACPM/AGS/APhA/ASH/ASPC/NMA/PCNA guideline for high blood pressure in adults. Hypertension 2018;71(6):e13-e115, https://doi.org/10.1161/HYP.0000000000000065 (PubMed metadata; categories from AHA summaries).
- Kawel-Boehm N, et al. Reference ranges ("normal values") for cardiovascular magnetic resonance (CMR) in adults and children: 2020 update. J Cardiovasc Magn Reson 2020;22:87, https://doi.org/10.1186/s12968-020-00683-3 (PMC7734766 full text, Tables 2, 5, 10).
- Cattermole GN, et al. The normal ranges of cardiovascular parameters measured using the ultrasonic cardiac output monitor. Physiol Rep 2017;5(6):e13195, https://doi.org/10.14814/phy2.13195 (PubMed abstract; numeric ranges not retrieved).

PubMed records above were retrieved through the PubMed connector; DOIs are given for each.
