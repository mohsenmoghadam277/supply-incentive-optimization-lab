# Supply Incentive Optimization Lab

**An End-to-End Data Science Portfolio Project for Marketplace Supply Incentive Optimization**

[![Python](https://img.shields.io/badge/Python-3.13-blue)](https://www.python.org/)
[![Machine Learning](https://img.shields.io/badge/Machine%20Learning-Uplift%20Modeling-orange)](https://scikit-learn.org/)
[![API](https://img.shields.io/badge/API-FastAPI-009688)](https://fastapi.tiangolo.com/)
[![Tests](https://img.shields.io/badge/Tests-9%20passed-success)](https://pytest.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> An independent Data Science portfolio project exploring how A/B testing, causal reasoning, uplift modeling, and campaign economics can support smarter incentive allocation in marketplace businesses.

**Data disclaimer:** All data and reported results are synthetic and illustrative. This project is not affiliated with or endorsed by Snapp, does not use real Snapp data, and is not deployed in any real marketplace.

## Table of Contents

- [Overview](#overview)
- [Business Problem](#business-problem)
- [Objectives](#objectives)
- [Methodology](#methodology)
- [Experiment Design](#experiment-design)
- [Data](#data)
- [Illustrative Results](#illustrative-results)
- [Campaign Economics](#campaign-economics)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Run the Pipeline and Tests](#run-the-pipeline-and-tests)
- [API](#api)
- [SQL Analysis](#sql-analysis)
- [Dashboard](#dashboard)
- [Limitations and Future Work](#limitations-and-future-work)
- [Author](#author)
- [License](#license)

## Overview

Marketplace businesses often use financial incentives to increase driver activity and improve supply availability. However, incentives create costs, and offering them to everyone may not be the most efficient strategy.

This project builds a reproducible analytical workflow to investigate two questions:

1. Does an incentive increase driver activity on average?
2. Can machine learning help identify drivers who may respond more strongly to an incentive?

The project combines randomized experiment analysis, uplift modeling, economic evaluation, candidate scoring, SQL templates, a FastAPI service, automated tests, and a standalone dashboard.

The objective is to demonstrate an end-to-end Data Science workflow, from synthetic data generation to analytical evaluation and model serving.

## Business Problem

A driver who completes many trips after receiving an incentive is not necessarily a driver whose activity increased because of it. The driver might have completed those trips without any incentive.

Evaluating campaigns using post-campaign activity alone can therefore overestimate their impact.

A more rigorous approach distinguishes between:

- **Observed outcomes:** What happened after the campaign.
- **Incremental impact:** The effect attributable to treatment under an appropriate experimental design.
- **Treatment heterogeneity:** How the treatment effect may differ across driver profiles.
- **Economic efficiency:** Whether incremental contribution justifies incentive expenditure.

The project uses A/B testing to estimate the average treatment effect and uplift modeling to explore differences in potential treatment effects across candidates.

## Objectives

- Estimate the average treatment effect using randomized synthetic experiment data.
- Quantify statistical uncertainty with confidence intervals and hypothesis testing.
- Implement a T-Learner using two Random Forest outcome models.
- Score and rank an independent pool of synthetic candidate drivers.
- Estimate campaign economics under explicit financial assumptions.
- Expose candidate-scoring functionality through FastAPI.
- Provide SQL templates for experiment analysis, segment economics, and monitoring.
- Include automated tests, analytical outputs, documentation, and a dashboard.

## Methodology

### 1. Synthetic Data Generation

Generate an experiment dataset and a separate candidate pool with driver activity, historical performance, operating zones, demand indicators, treatment assignment, outcomes, and incentive costs.

### 2. Data Quality Checks

Check key fields, duplicate records, missing values, and basic data constraints before running the analytical pipeline.

### 3. A/B Testing

Estimate the intention-to-treat effect as the difference between mean outcomes in the treatment and control groups:

\[
\widehat{ATE}=\bar{Y}_{T}-\bar{Y}_{C}
\]

The analysis includes a Welch confidence interval, a hypothesis test, and a secondary OLS analysis with HC3 robust standard errors.

### 4. Uplift Modeling

The project implements a T-Learner with two `RandomForestRegressor` models:

- A treatment model estimates the expected outcome under treatment.
- A control model estimates the expected outcome under control.

For candidate features \(x\), predicted uplift is:

\[
\hat{\tau}(x)=\hat{\mu}_1(x)-\hat{\mu}_0(x)
\]

Candidates are ranked by predicted uplift to explore how incentive budgets might be targeted.

Predicted individual uplift is an estimate, not an observed fact. Its usefulness must be evaluated with appropriate holdout analysis, calibration, and prospective experiments.

### 5. Economic Evaluation

Translate incremental trips and incentive expenditure into illustrative business metrics, including cost per incremental trip, incremental contribution, and return on investment.

### 6. Model Serving and Reporting

Expose scoring endpoints through FastAPI and generate analytical outputs, monitoring snapshots, and a standalone HTML dashboard.

## Experiment Design

| Component | Description |
|---|---|
| Unit of analysis | One driver per campaign |
| Treatment | Incentive offer |
| Control | No incentive offer |
| Pre-treatment window | Four weeks |
| Outcome window | Seven days |
| Primary outcome | Trips completed during the outcome window |
| Secondary outcomes | Online hours and activity status |
| Primary analysis | Intention-to-treat effect |
| Statistical uncertainty | Welch confidence interval and hypothesis test |
| Secondary analysis | OLS with HC3 robust standard errors |

The synthetic assignment procedure is randomized. However, the experiment has not been power-calculated or conducted in a real marketplace.

## Data

### Experiment Dataset

`data/raw/experiment_data.csv`

The current synthetic dataset contains 12,000 driver-campaign records:

- 5,899 treatment records
- 6,101 control records

Example features include:

| Feature | Description |
|---|---|
| `driver_id` | Synthetic driver identifier |
| `campaign_id` | Campaign identifier |
| `assignment_date` | Assignment date |
| `zone` | Synthetic operating zone |
| `daypart` | Time-of-day segment |
| `avg_online_hours_4w` | Historical online-hours measure |
| `avg_trips_4w` | Historical trips measure |
| `cancellation_rate` | Historical cancellation rate |
| `acceptance_rate` | Historical acceptance rate |
| `demand_index` | Synthetic demand indicator |
| `tenure_days` | Driver tenure |
| `is_active_pre` | Pre-treatment activity status |
| `treatment` | Treatment assignment |
| `trips_next_week` | Outcome-window trips |
| `online_hours_next_week` | Outcome-window online hours |
| `active_next_week` | Outcome-window activity status |
| `incentive_cost_toman` | Simulated incentive cost |
| `synthetic_data` | Synthetic-data indicator |

### Candidate Pool

`data/raw/candidate_pool.csv`

A separate pool of 3,000 synthetic candidates is used to demonstrate model scoring and ranking. The top 20% of candidates corresponds to 600 records in the current run.

### Leakage Prevention

Only pre-treatment features should be used for training and scoring. Post-treatment outcomes must not be included as model inputs.

In a real deployment, feature timestamps, availability, and treatment-assignment timing would need to be validated explicitly.

## Illustrative Results

The following results come from the current synthetic simulation and are not real business outcomes.

| Metric | Illustrative result |
|---|---:|
| Experiment records | 12,000 |
| Treatment records | 5,899 |
| Control records | 6,101 |
| Estimated average treatment effect | +1.996 trips per assigned driver |
| 95% confidence interval | 1.626 to 2.365 trips |
| Candidate pool | 3,000 |
| Candidates in top 20% ranking | 600 |
| Mean predicted uplift in selected group | Approximately 4.47 trips |
| Observed holdout uplift in selected group | Approximately 2.41 trips |
| Approximate 95% confidence interval for holdout uplift | 0.67 to 4.14 trips |

The simulated experiment shows a positive average treatment effect. However, the difference between predicted and observed uplift highlights uncertainty in the targeting model.

These results do not establish that a targeted policy will outperform a broad incentive campaign in practice. That claim would require stronger validation and a prospective policy experiment.

## Campaign Economics

The illustrative financial scenario assumes a contribution margin of **50,000 toman per incremental trip**.

The simplified ROI calculation is:

\[
ROI=
\frac{\text{Incremental Contribution}-\text{Incentive Cost}}
{\text{Incentive Cost}}\times100\%
\]

Under the current simulation assumptions:

- Illustrative scenario ROI: approximately **+16.5%**
- Break-even contribution margin: approximately **42,935 toman per incremental trip**

These values depend on synthetic outcomes, simulated costs, and assumed contribution margins. They are not actual company results, financial forecasts, or guarantees of savings.

## Technology Stack

- Python
- Pandas and NumPy
- SciPy and Statsmodels
- scikit-learn
- Matplotlib
- FastAPI
- Pytest
- SQL analysis templates
- HTML and JavaScript dashboard
- GitHub Actions

## Project Structure

```text
supply-incentive-optimization-lab/
├── .github/
│   └── workflows/
├── api/
│   └── app.py
├── data/
│   └── raw/
├── docs/
├── outputs/
├── sql/
├── src/
├── tests/
├── README.md
├── README_FA.md
├── requirements.txt
└── LICENSE
```

The repository may contain additional generated artifacts and documentation beyond this simplified overview.

## Getting Started

### Prerequisites

- Python 3.13
- Git
- PowerShell on Windows, or a compatible terminal

### 1. Clone the Repository

```bash
git clone https://github.com/mohsenmoghadam277/supply-incentive-optimization-lab.git
cd supply-incentive-optimization-lab
```

### 2. Create a Virtual Environment

**Windows PowerShell:**

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Run the Pipeline

```bash
python -m src.run_pipeline
```

The pipeline generates synthetic data, runs quality checks and experiment analysis, trains and evaluates the modeling workflow, scores candidates, and produces supported analytical outputs.

## Run the Pipeline and Tests

Run the automated test suite:

```bash
python -m pytest -q
```

The current test suite has passed **9 tests** in the tested environment. Run it locally to verify your own setup.

## API

Start the local FastAPI development server:

```bash
uvicorn api.app:app --reload
```

Base URL:

`http://127.0.0.1:8000`

| Endpoint | Purpose |
|---|---|
| `GET /health` | Health check |
| `POST /score` | Score one candidate |
| `POST /score/batch` | Score multiple candidates |

Interactive API documentation:

`http://127.0.0.1:8000/docs`

Inspect the request and response schemas in the interactive documentation before sending requests.

The API is a local prototype. It has not been validated or deployed as a production service.

## SQL Analysis

The `sql/` directory contains templates for experiment analysis, segment economics, and model monitoring.

The SQL is intended as a SQL Server-style reference and has not been tested against a live database. Review and adapt it before using another database engine, including PostgreSQL.

## Dashboard

The repository includes a standalone dashboard:

`snapp_incentive_dashboard_v3.html`

Open the file in a modern browser to explore the supported dashboard views without deploying a separate web application.

All displayed figures should be interpreted as illustrative simulation results.

## Limitations and Future Work

This project is a portfolio prototype, not a production incentive decision system.

Key limitations include:

1. All data are synthetic.
2. Experiment results depend on the data-generation assumptions.
3. The assignment design has not been power-calculated or validated in a field experiment.
4. Individual treatment effects cannot be observed directly.
5. Uplift predictions require additional calibration and evaluation.
6. No prospective experiment has established the value of the targeting policy.
7. Financial assumptions require validation against real operational and finance data.
8. SQL templates have not been executed against a live database.
9. Production deployment, access controls, monitoring, and operational reliability have not been validated.

Potential next steps include:

- Power-calculated experiment design.
- Evaluation of alternative uplift algorithms.
- Qini curves, uplift curves, and policy-value analysis.
- Prospective randomized evaluation of targeted versus broad incentive policies.
- Budget-constrained targeting and sensitivity analysis.
- Database integration and SQL integration tests.
- Model versioning, drift monitoring, and production API controls.

## Author

**Mohsen Moghadam**

GitHub: [@mohsenmoghadam277](https://github.com/mohsenmoghadam277)

Repository: [Supply Incentive Optimization Lab](https://github.com/mohsenmoghadam277/supply-incentive-optimization-lab)

## License

This project is distributed under the MIT License. See [LICENSE](LICENSE) for details.
