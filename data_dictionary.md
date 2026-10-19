# Data dictionary — Incentive Lab

**Classification:** every row in this portfolio is synthetic. IDs, campaign, assignments, and outcomes are artificial and do not represent actual Snapp data.

## Experiment data (`data/raw/experiment_data.csv`)

Grain: one driver per randomized assignment for the illustrative campaign.

| Field | Meaning | Role | Notes |
|---|---|---|---|
| `driver_id` | Synthetic driver identifier | Key | No real identity is encoded |
| `campaign_id` | Campaign key | Join / filter | `INCENTIVE_SYNTH_001` |
| `assignment_date` | Assignment date | Time | Fixed synthetic date for reproducibility |
| `zone` | Operating zone | Feature / segment | central, east, north, south, west |
| `daypart` | Main operating time band | Feature / segment | morning, afternoon, evening, late_night |
| `avg_online_hours_4w` | Average weekly online hours in pre-period | Feature | Pre-treatment only |
| `avg_trips_4w` | Average weekly trips in pre-period | Feature | Pre-treatment only |
| `cancellation_rate` | Pre-period cancellation rate | Feature | 0–1 proportion |
| `demand_index` | Synthetic relative-demand index | Feature | Not a real operational KPI |
| `acceptance_rate` | Pre-period acceptance rate | Feature | 0–1 proportion |
| `tenure_days` | Driver tenure | Feature | Synthetic days |
| `is_active_pre` | Activity before assignment | Feature | 0/1 |
| `treatment` | Randomized incentive assignment | Treatment indicator | 1=treatment, 0=control |
| `trips_next_week` | Trips during outcome window | Primary outcome | Used for A/B and ML outcome model |
| `online_hours_next_week` | Online hours during outcome window | Secondary outcome | Post-treatment; never used as a model input |
| `active_next_week` | Active in outcome window | Secondary outcome | Post-treatment; never used as a model input |
| `incentive_cost_toman` | Incentive amount spent | Economics | Zero for control by design |
| `synthetic_data` | Synthetic-data flag | Governance | Always 1 in this package |

## Candidate pool (`data/raw/candidate_pool.csv`)

Grain: one eligible synthetic driver to be scored. It contains pre-treatment features only and **does not contain campaign outcomes or a treatment assignment**. Model predictions are saved to `project_outputs/scored_candidates.csv`.

## Generated outputs

- `experiment_summary.csv`: arm means, treatment-control differences, 95% confidence intervals and Welch p-values for outcome measures. The cost row is descriptive only; its CI and p-value are intentionally blank.
- `segment_summary.csv`: zone/daypart subgroup estimates. These are exploratory and should not automatically trigger budget allocation without adequate power and a pre-specified decision rule.
- `campaign_economics.json`: scenario economics under a user-specified assumed gross margin per incremental trip.
- `model_validation.json`: out-of-sample arm-specific outcome prediction metrics, holdout experiment lift, and top/bottom score-band checks.
- `uplift_decile_summary.csv`: holdout score bands compared with observed randomized outcomes. Small-band estimates are noisy.
- `scored_candidates.csv` / `uplift_recommendations.csv`: candidate predictions, cost scenario, expected net value and rank.
- `feature_importance.csv`: predictive importance from the two outcome models; not a causal explanation.
- `monitoring_snapshot.json`: synthetic baseline-to-candidate feature drift snapshot, not live monitoring.
