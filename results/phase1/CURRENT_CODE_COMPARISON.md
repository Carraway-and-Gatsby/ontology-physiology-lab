# Phase 1 results and the current code (comparison of 2026-11-03)

The files in this folder were produced by the initial commit of 2026-10-31. They are kept unchanged as the recorded
result of that run. The engine changed afterwards the same day (event-based integration across valve transitions,
`src/physiosim/simulation/_hybrid.py`), and the ontology annotations moved to the node specification v2 on 2026-11-01
(`docs/decisions.md`). Running `python -m physiosim --config experiments/phase1.json` with the current code gives
slightly different trajectories and different annotations. These code changes are the relevant provenance; the
comparison changes code and environment together and is not a controlled experiment that isolates either change.
Comparison on 2026-11-03 of the 2026-10-31 files with a current-code run (macOS, Python 3.11.15, NumPy 2.4.6, SciPy
1.17.1; the regenerated files are not committed):

| File | Committed vs current code |
| --- | --- |
| `baseline.csv` | max absolute difference 0.133902 (largest in a valve flow column, mL/s), max relative difference 0.000448, 24001 rows |
| `partial_contractility_restoration.csv` | max absolute difference 0.171321 (largest in a valve flow column, mL/s), max relative difference 0.00237, 24001 rows |
| `reduced_contractility.csv` | max absolute difference 0.104182 (largest in a valve flow column, mL/s), max relative difference 0.00173, 24001 rows |
| `summary.json` | 45 fields differ; cardiac output differs by less than 1e-6 L/min in every scenario (baseline 7.699313 L/min in both); all three scenarios `periodic_within_declared_gate` in both |
| `variables.json`, `annotations.trig` | annotations follow the v2 node specification (for example Uberon instead of FMA as the primary anatomy IRI, added `xref` and `occurs_in`) |
| `manifest.json` | source hashes differ for the changed modules; `_hybrid.py` and the agent, M1 and applied-demo modules did not exist at the time of this run |

Byte-identical reproduction is a property of the same host with fixed code and dependencies
(`results/reproducibility.json`). Three `baseline.csv` byte streams exist: the 2026-10-31 snapshot (`1820f3a3...`) and
two current-code outputs of 2026-11-03, on macOS (`77209d70...`) and on the Linux CI runner (`96c2e194...`); two runs on
the same host with the same code were byte-identical.
