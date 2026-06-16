# notebooks/ — paper reproduction

Each notebook regenerates one part of the paper from **already-computed** data
(no Java re-run). Run from anywhere: a bootstrap cell `cd`s to the repo root.

| Notebook | Paper artifact | Data source |
|---|---|---|
| `00_build_summary.ipynb` | *(data-prep, usually not run)* builds `results/summary/**` from raw `results/run_*` | raw runs |
| `01_network_metrics.ipynb` | **Table 3** (network metrics) | self-contained (networkx) |
| `02_empirical_validation.ipynb` | **§4.2 SF1–SF3** | `emp-valid/stylized_facts_comparison.csv` (recompute guarded off) |
| `03_backfire_appearance.ipynb` | **Fig 1** | `results/summary/HolmeKim/A_1_m_3_pt_0.3/63f67d05/` |
| `04_backfire_mechanism.ipynb` | **Table 4 + §4.4** | same `63f67d05` condition |
| `05_sensitivity_dose_response.ipynb` | **Fig 2, Fig 3, Table 5** | `results/summary/*/*/*/` |

Notes:
- `results/` is git-ignored; `results/summary/**` holds the paper's curated batch and must be present for 03–05.
- The structural rows of Table 4 (λ₂, betweenness, modularity, follower cRate) were
  precomputed into the summary CSVs by `compute_connectivity.py` and `regen_mechanism_*.py` (kept at repo root).
