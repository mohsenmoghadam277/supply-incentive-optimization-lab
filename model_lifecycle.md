# Model lifecycle and production-readiness plan

## Implemented locally

1. **Training data:** pre-treatment driver attributes joined to a randomized experiment outcome table; candidate pool is scored separately and has no outcomes.
2. **Feature engineering:** numeric imputation; one-hot encoding for zone and daypart; no post-treatment outcomes in model inputs.
3. **Model:** T-learner with two `RandomForestRegressor` pipelines. One estimates outcomes under control, the other under treatment.
4. **Validation:** fixed random 80/20 split stratified by assignment; MAE/RMSE/R² reported independently by arm; treatment-control lift checked in holdout and within score bands.
5. **Artifact:** serialized model bundle under `artifacts/uplift_model.joblib`.
6. **Serving demo:** FastAPI `/health`, `/score`, and `/score/batch` endpoints.
7. **Drift snapshot:** PSI-style population checks on numeric input features from reference experiment to candidate pool.

## Required before a real production launch

- Replace synthetic sources with reviewed, permissioned warehouse views and a versioned feature contract; verify driver-level grain, timestamp cutoffs, identity joins, data freshness, missingness, duplicates, and treatment leakage.
- Obtain Finance-approved incremental contribution margin and incentive cost definitions.
- Run an experiment power calculation and write a pre-analysis plan; account for interference and repeated campaign exposures.
- Keep model versions, training-data window/hash, code revision, parameters, feature schema, validation results, and approver status in a model registry.
- Deploy first in shadow mode; compare the API output with offline batch output and add latency, schema, null, range, and failure alerts.
- Randomize policy assignment among score bands. Assess overall ATE, uplift by score band, incremental cost per trip, ROI with uncertainty, and guardrails.
- Monitor outcome delay, calibration of both outcome models, population/feature drift, ranking stability, cost distribution, subgroup behavior, and realized policy value. PSI alone does not mean performance degraded.
- Define a rollback model, approval process, retraining criteria, and incident owner before production; none is configured in this portfolio demo.

## Monitoring interpretation

`monitoring_snapshot.json` is an offline baseline check produced from synthetic data. It is not evidence of ongoing monitoring, it has no live serving traffic, and it has no mature production outcomes to calculate real degradation.
