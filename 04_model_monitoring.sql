/* Outcome monitoring after the next-week observation window has matured. */
DECLARE @model_version varchar(64) = 't_learner_rf_v1';
DECLARE @scoring_run_id varchar(64) = 'replace_with_run_id';

WITH matched AS (
    SELECT
        s.model_version,
        s.recommended_top20,
        e.treatment,
        e.trips_next_week,
        s.predicted_uplift_trips,
        s.expected_net_value_toman
    FROM incentive.UpliftScore s
    INNER JOIN incentive.ExperimentDriver e
      ON e.campaign_id = s.campaign_id AND e.driver_id = s.driver_id
    WHERE s.model_version = @model_version
      AND s.scoring_run_id = @scoring_run_id
      AND e.trips_next_week IS NOT NULL
)
SELECT
    model_version,
    recommended_top20,
    treatment,
    COUNT_BIG(*) AS driver_n,
    AVG(CAST(trips_next_week AS float)) AS mean_observed_trips,
    AVG(predicted_uplift_trips) AS mean_predicted_uplift,
    AVG(expected_net_value_toman) AS mean_predicted_net_value_toman
FROM matched
GROUP BY model_version, recommended_top20, treatment
ORDER BY recommended_top20 DESC, treatment DESC;
GO

/* Basic data-quality guardrails to run after each score batch. */
SELECT
    COUNT_BIG(*) AS scored_rows,
    COUNT(DISTINCT driver_id) AS distinct_drivers,
    SUM(CASE WHEN predicted_uplift_trips IS NULL THEN 1 ELSE 0 END) AS null_uplift_rows,
    SUM(CASE WHEN expected_cost_toman < 0 THEN 1 ELSE 0 END) AS negative_cost_rows,
    SUM(CASE WHEN recommendation_rank <= 0 THEN 1 ELSE 0 END) AS invalid_rank_rows
FROM incentive.UpliftScore
WHERE scoring_run_id = @scoring_run_id;
GO
