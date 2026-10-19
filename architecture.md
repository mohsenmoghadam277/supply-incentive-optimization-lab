# Architecture

```text
Synthetic randomized experiment (12,000 rows) ──┬──> A/B analysis + CI/p-values ──> experiment_summary.csv
                                                  ├──> segment & campaign economics ──> segment_summary.csv / campaign_economics.json
                                                  └──> T-learner training (80/20 holdout)
                                                          ├──> arm-specific outcome metrics / score-band checks
                                                          ├──> final refit on historical randomized experiment
                                                          └──> model artifact

Independent candidate pool (3,000 rows; no outcomes) ──> model artifact ──> uplift / net-value scores
                                                                        ├──> scored_candidates.csv
                                                                        ├──> interactive HTML dashboard snapshot
                                                                        └──> FastAPI /score endpoint

SQL Server reference layer: schema + A/B summaries + segment economics + outcome monitoring queries
```

Data is local and synthetic. No Snapp production API, warehouse, or SQL Server connection is present in this ZIP. SQL scripts are reference T-SQL and should be deployed only after source review, table mapping, and data-access approval.
