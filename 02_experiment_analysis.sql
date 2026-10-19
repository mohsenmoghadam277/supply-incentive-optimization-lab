/* A/B test summary. Cost is reported descriptively; it is not an outcome tested for efficacy. */
DECLARE @campaign_id varchar(64) = 'INCENTIVE_SYNTH_001';
WITH arm AS (
    SELECT
        treatment,
        COUNT_BIG(*) AS driver_n,
        AVG(CAST(trips_next_week AS float)) AS mean_trips_next_week,
        STDEV(CAST(trips_next_week AS float)) AS sd_trips_next_week,
        AVG(CAST(online_hours_next_week AS float)) AS mean_online_hours_next_week,
        AVG(CAST(active_next_week AS float)) AS active_rate,
        AVG(CAST(incentive_cost_toman AS float)) AS mean_incentive_cost_toman
    FROM incentive.ExperimentDriver
    WHERE campaign_id = @campaign_id
      AND synthetic_data = 1 /* replace with approved real-data scope in production */
      AND trips_next_week IS NOT NULL
    GROUP BY treatment
), paired AS (
    SELECT
        MAX(CASE WHEN treatment = 1 THEN driver_n END) AS treatment_n,
        MAX(CASE WHEN treatment = 0 THEN driver_n END) AS control_n,
        MAX(CASE WHEN treatment = 1 THEN mean_trips_next_week END) AS treatment_mean,
        MAX(CASE WHEN treatment = 0 THEN mean_trips_next_week END) AS control_mean,
        MAX(CASE WHEN treatment = 1 THEN sd_trips_next_week END) AS treatment_sd,
        MAX(CASE WHEN treatment = 0 THEN sd_trips_next_week END) AS control_sd,
        MAX(CASE WHEN treatment = 1 THEN mean_online_hours_next_week END) AS treatment_online_hours,
        MAX(CASE WHEN treatment = 0 THEN mean_online_hours_next_week END) AS control_online_hours,
        MAX(CASE WHEN treatment = 1 THEN active_rate END) AS treatment_active_rate,
        MAX(CASE WHEN treatment = 0 THEN active_rate END) AS control_active_rate,
        MAX(CASE WHEN treatment = 1 THEN mean_incentive_cost_toman END) AS treatment_cost_per_treated_driver
    FROM arm
)
SELECT *,
    treatment_mean - control_mean AS trip_lift,
    SQRT(POWER(treatment_sd, 2) / NULLIF(treatment_n, 0) + POWER(control_sd, 2) / NULLIF(control_n, 0)) AS trip_lift_se,
    (treatment_mean - control_mean)
      - 1.96 * SQRT(POWER(treatment_sd, 2) / NULLIF(treatment_n, 0) + POWER(control_sd, 2) / NULLIF(control_n, 0)) AS trip_lift_ci95_low_approx,
    (treatment_mean - control_mean)
      + 1.96 * SQRT(POWER(treatment_sd, 2) / NULLIF(treatment_n, 0) + POWER(control_sd, 2) / NULLIF(control_n, 0)) AS trip_lift_ci95_high_approx
FROM paired;
GO
