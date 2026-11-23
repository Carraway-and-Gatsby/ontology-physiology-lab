# About this public copy of the E1 records (2026-11-23)

The files of `docs/validation/e1_vitaldb/`, `experiments/e1_vitaldb/` and `results/e1_vitaldb/` were copied from the
private repository after the experiment was finished. Read them with the following in mind.

- **The order of events cannot be checked in this repository.** The records say that the pre-registration was sealed
  before any recording was opened and that the code was frozen before the test recordings were read. In the private
  repository these are separate commits (`057d2f4` seal, `74e1928` code freeze, `2706496` results, `3718a9e` and
  `0b9f72b` review follow-up). Those hashes refer to the private history; they do not exist here. In this public
  history all files arrive together, so this repository alone does not prove the order.
- **Changes made for the public copy** (see also `REDACTIONS.md`):
  - `experiments/e1_vitaldb/run_e1.py`: the default data directory, a local path, is replaced by `<local path>`. Set
    the environment variable `E1_DATA_DIR` to run it.
  - `RESULTS_E1.md`, `POSTHOC_E1.md`: "PR #11" is written as "PR #11 of [private repository]".
  - `case_lists.json`: 13 case ids of the development pool that are known only from the vitaldb.net track index are
    omitted; every case id that remains had its tracks read from the PhysioNet files. The list of cases with RV
    volumetrics is given as read from the PhysioNet files (48 cases; the index lists 49).
  - Nothing else differs from the private files.
- **Later addition (2026-11-23).** `FAILURE_ANALYSIS_E1.md`, the four `posthoc_*.py` scripts, the files under
  `results/e1_vitaldb/posthoc_failure_analysis/` and a correction paragraph in `RESULTS_E1.md` section 4 were copied
  unchanged from the private commit `3f9ab52` (a hash of the private history).
- **Data.** No recording is included. The numbers under `results/e1_vitaldb/` are derived from VitalDB recordings
  obtained from PhysioNet (version 1.0.0, CC BY 4.0); attribution is in `NOTICE.md`.
- **Review status.** The analysis and the texts were written by an AI system (Claude) and checked by an automated
  cross-provider review only. No human has reviewed them.
