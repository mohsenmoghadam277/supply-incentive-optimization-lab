/* SQL Server T-SQL. Portfolio schema only; no live Snapp connection is assumed. */
IF SCHEMA_ID('incentive') IS NULL EXEC('CREATE SCHEMA incentive');
GO

CREATE TABLE incentive.ExperimentDriver (
    driver_id              varchar(16)  NOT NULL,
    campaign_id             varchar(64)  NOT NULL,
    assignment_date         date         NOT NULL,
    zone                    varchar(16)  NOT NULL,
    daypart                 varchar(16)  NOT NULL,
    avg_online_hours_4w     decimal(8,2) NOT NULL,
    avg_trips_4w            decimal(8,2) NOT NULL,
    cancellation_rate       decimal(8,5) NOT NULL,
    demand_index            decimal(8,4) NOT NULL,
    acceptance_rate         decimal(8,5) NOT NULL,
    tenure_days             int          NOT NULL,
    is_active_pre           bit          NOT NULL,
    treatment               bit          NOT NULL,
    trips_next_week         int          NULL,
    online_hours_next_week  decimal(8,2) NULL,
    active_next_week        bit          NULL,
    incentive_cost_toman    bigint       NOT NULL CONSTRAINT DF_ExperimentDriver_Cost DEFAULT (0),
    synthetic_data          bit          NOT NULL CONSTRAINT DF_ExperimentDriver_Synthetic DEFAULT (1),
    ingested_at_utc         datetime2(0) NOT NULL CONSTRAINT DF_ExperimentDriver_Ingested DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT PK_ExperimentDriver PRIMARY KEY (campaign_id, driver_id),
    CONSTRAINT CK_ExperimentDriver_Rates CHECK (cancellation_rate BETWEEN 0 AND 1 AND acceptance_rate BETWEEN 0 AND 1),
    CONSTRAINT CK_ExperimentDriver_Cost CHECK (incentive_cost_toman >= 0)
);
GO

CREATE TABLE incentive.UpliftScore (
    scoring_run_id          varchar(64)  NOT NULL,
    model_version           varchar(64)  NOT NULL,
    scoring_date            date         NOT NULL,
    driver_id               varchar(16)  NOT NULL,
    campaign_id             varchar(64)  NOT NULL,
    pred_trips_control      decimal(10,4) NOT NULL,
    pred_trips_treatment    decimal(10,4) NOT NULL,
    predicted_uplift_trips  decimal(10,4) NOT NULL,
    expected_cost_toman     bigint       NOT NULL,
    assumed_margin_toman    bigint       NOT NULL,
    expected_net_value_toman decimal(14,2) NOT NULL,
    recommendation_rank    int          NOT NULL,
    recommended_top20       bit          NOT NULL,
    scored_at_utc           datetime2(0) NOT NULL CONSTRAINT DF_UpliftScore_Scored DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT PK_UpliftScore PRIMARY KEY (scoring_run_id, driver_id),
    CONSTRAINT CK_UpliftScore_Cost CHECK (expected_cost_toman >= 0)
);
GO

CREATE TABLE incentive.ModelRegistry (
    model_version           varchar(64) NOT NULL PRIMARY KEY,
    model_type              varchar(64) NOT NULL,
    trained_at_utc          datetime2(0) NOT NULL,
    training_start_date     date NULL,
    training_end_date       date NULL,
    training_rows           int NOT NULL,
    artifact_uri            nvarchar(512) NULL,
    validation_mae_control  decimal(10,4) NULL,
    validation_mae_treatment decimal(10,4) NULL,
    status                  varchar(20) NOT NULL,
    data_classification     varchar(40) NOT NULL,
    notes                   nvarchar(1000) NULL,
    CONSTRAINT CK_ModelRegistry_Status CHECK (status IN ('candidate','shadow','approved','retired'))
);
GO
