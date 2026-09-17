# Engineering Delivery Intelligence Platform

An analytics platform that evaluates how efficiently and reliably software
moves through the engineering delivery lifecycle — from commit through
pull request, review, merge, deployment, and (where an incident occurs)
recovery.

> **Status:** Phase 1 (Project Setup) — this README is a placeholder and
> will be expanded into a full project write-up in a later phase.

## Business questions this project answers

1. Where are the biggest bottlenecks in the software delivery process?
2. How quickly is software being delivered?
3. Is engineering becoming faster without becoming less reliable?
4. What engineering factors are associated with longer delivery times or
   higher failure rates?
5. How do repositories differ in delivery performance?
6. What signals should engineering leadership investigate?

## Data sources

- **GHPR dataset** — public GitHub pull-request data (repository, PR
  timestamps, commits, comments, review comments, additions/deletions,
  changed files). This is the primary development-activity dataset.
- **DORA / Four Keys–style model** — deployment and incident data,
  modelled on the Google DORA framework, used to demonstrate a
  reliability layer (deployment frequency, change failure rate, time to
  restore).

The development data and the deployment/reliability data are **not**
presented as coming from the same real company. This project instead
demonstrates how development activity and deployment/reliability data
*can be integrated* to evaluate software delivery performance — full
source details, access dates, and limitations will be documented as each
dataset is added (Phase 2 onward).

## Architecture

```
Public GitHub Data
        |
Python Data Cleaning
        |
PostgreSQL
        |
SQL Analytics Layer
        |
Python Feature Engineering / Analysis
        |
Power BI
        |
Engineering Insights & Bottleneck Detection
```

## Repository structure

```
engineering-delivery-intelligence/
|
├── data/
│   ├── raw/            # original, unmodified source data (gitignored)
│   └── processed/      # cleaned data (gitignored)
|
├── sql/
│   ├── 01_data_quality.sql
│   ├── 02_delivery_metrics.sql
│   ├── 03_pr_analysis.sql
│   ├── 04_deployment_analysis.sql
│   └── 05_incident_analysis.sql
|
├── src/
│   ├── cleaning.py
│   ├── feature_engineering.py
│   └── analysis.py
|
├── notebooks/
│   └── exploratory_analysis.ipynb
|
├── dashboard/
│   └── screenshots/
|
├── README.md
├── requirements.txt
├── .env.example
└── .gitignore
```

Raw and processed data are not committed to this repository (see
`.gitignore`); instructions for obtaining the data are documented in
`data/raw/` once Phase 2 (Data Acquisition) is complete.

## Tech stack

Python (pandas, NumPy, SQLAlchemy), PostgreSQL, SQL, Power BI, Git/GitHub.

## How to reproduce (setup)

1. Clone this repository.
2. Create and activate a virtual environment:
   ```
   python3 -m venv .venv
   source .venv/bin/activate      # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Create a local PostgreSQL database:
   ```sql
   CREATE DATABASE engineering_delivery;
   ```
4. Copy `.env.example` to `.env` and fill in your local PostgreSQL
   credentials.
5. (Later phases) Run the scripts in `sql/` against the database, then
   run the notebooks/scripts in `src/` and `notebooks/`.
6. Power BI connects directly to the `engineering_delivery` PostgreSQL
   database (Get Data → Database → PostgreSQL database) once the SQL
   analytics layer exists (Phase 12).

Full methodology, metric definitions, findings, and limitations will be
documented here as each phase is completed.

## License / attribution

Public GitHub data is used under its respective public licensing terms;
sources and access dates are recorded alongside the data once acquired.
