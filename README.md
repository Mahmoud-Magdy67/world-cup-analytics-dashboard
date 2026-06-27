# World Cup Analytics Dashboard

Production-ready Streamlit multipage source code for a World Cup analytics dashboard. First commit uses mock data only.

## Pages
1. Tournament Overview
2. Team Performance
3. Player Analysis
4. Match Analysis
5. Predictions / Model Results
6. Data & Methodology

Each page renders a title, short description, KPI cards, and at least one Plotly chart.

## Local-independent deployment requirements
This repository stores only source code. It is not live until connected to a Streamlit-compatible hosting provider. A deployment environment needs Python 3.11+, packages from `requirements.txt`, and `streamlit run app.py`. No BigQuery credentials are needed for the first mock-data release.

## Data policy
Future BigQuery access must be implemented in `data/bigquery.py`, must be read-only SELECT queries, and must not perform destructive operations.

## Hermes / Gitea automation
Hermes can update this dashboard by editing repository files through the Gitea API on branch `main`. For existing files, retrieve the current file SHA before sending changes.

## Local test
```bash
pip install -r requirements.txt
pytest -q
streamlit run app.py
```
