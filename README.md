# SQL reference scripts

These files use Microsoft SQL Server T-SQL. They are reference code and have **not** been executed against a connected database in this project.

Recommended order:

1. Execute `01_schema.sql` in an approved development database.
2. Load `data/raw/experiment_data.csv` into `incentive.ExperimentDriver` using SQL Server Import Wizard or a reviewed ETL/`BULK INSERT` process. CSV paths and server permissions vary by environment.
3. Execute `02_experiment_analysis.sql` and `03_segment_economics.sql` after declaring the correct `@campaign_id`.
4. Load scored batches into `incentive.UpliftScore`, add approved model metadata to `incentive.ModelRegistry`, and use `04_model_monitoring.sql` with the correct run ID after outcomes mature.

Before real use, change the synthetic-data filter only as part of a reviewed data-access and metric-governance process. The example intentionally does not contain credentials, production endpoints, or a live connection.
