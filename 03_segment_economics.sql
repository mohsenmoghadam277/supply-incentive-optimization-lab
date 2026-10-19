/* Segment estimates: treat these as exploratory unless powered and pre-specified. */
DECLARE @campaign_id varchar(64) = 'INCENTIVE_SYNTH_001';
WITH arms AS (
    SELECT
        zone,
        daypart,
        treatment,
        COUNT_BIG(*) AS driver_n,
        AVG(CAST(trips_next_week AS float)) AS mean_trips,
        AVG(CAST(incentive_cost_toman AS float)) AS mean_cost
    FROM incentive.ExperimentDriver
    WHERE campaign_id = @campaign_id
      AND synthetic_data = 1
      AND trips_next_week IS NOT NULL
    GROUP BY zone, daypart, treatment
), combined AS (
    SELECT
        COALESCE(t.zone, c.zone) AS zone,
        COALESCE(t.daypart, c.daypart) AS daypart,
        t.driver_n AS treatment_n,
        c.driver_n AS control_n,
        t.mean_trips AS treatment_mean_trips,
        c.mean_trips AS control_mean_trips,
        t.mean_cost AS cost_per_treated_driver_toman
    FROM arms t
    FULL OUTER JOIN arms c
      ON t.zone = c.zone AND t.daypart = c.daypart
     AND t.treatment = 1 AND c.treatment = 0
    WHERE t.treatment = 1 OR c.treatment = 0
)
SELECT *,
    treatment_mean_trips - control_mean_trips AS observed_trip_lift,
    cost_per_treated_driver_toman / NULLIF(treatment_mean_trips - control_mean_trips, 0) AS cost_per_incremental_trip_toman
FROM combined
ORDER BY zone, daypart;
GO
