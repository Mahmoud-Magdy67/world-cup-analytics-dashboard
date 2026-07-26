# Quick Data Migration - World Cup Analytics Dashboard

## The Issue
Your Streamlit app shows "Connected to AWS Athena" but all data tables are empty because the World Cup data was never migrated from BigQuery.

## Quick Fix (5 Steps)

### 1. Export Data from BigQuery
```bash
# Set your GCP credentials
export GCP_SERVICE_ACCOUNT_KEY="your_base64_encoded_key_here"
export GCP_PROJECT_ID="project-2f1e456e-b1be-4551-92b"

# Run export script
python export_bigquery_data.py
```
This creates `exported_data/*.parquet` files.

### 2. Upload to S3
```bash
# Set your S3 bucket
export S3_DATA_BUCKET="wc2026-simulation-data"

# Upload files
aws s3 cp exported_data/ s3://$S3_DATA_BUCKET/worldcup-data/ --recursive
```

### 3. Create Athena Tables
Go to AWS Athena console and run CREATE TABLE statements for each table:

**Teams table:**
```sql
CREATE EXTERNAL TABLE worldcup_2026.wc26_dashboard_v16_live_july4 (
    team_name STRING,
    group_name STRING,
    winner_rank INT,
    championship_probability DOUBLE,
    elo_rating INT,
    total_market_value_eur DOUBLE,
    contender_tier STRING,
    round32_probability DOUBLE,
    round16_probability DOUBLE,
    quarterfinal_probability DOUBLE,
    semifinal_probability DOUBLE,
    final_probability DOUBLE,
    elimination_stage STRING,
    tournament_status STRING
)
STORED AS PARQUET
LOCATION 's3://wc2026-simulation-data/worldcup-data/wc26_dashboard_v16_live_july4.parquet';
```

**Repeat for:**
- v_winner_prediction_dashboard_v15_live_10m
- v_real_player_rows_enriched_v8
- v_team_schedule
- v_teams_clean

### 4. Verify Data
```sql
SELECT COUNT(*) FROM worldcup_2026.wc26_dashboard_v16_live_july4;
```
Should return 48 (not 0).

### 5. Test Streamlit App
Refresh your Streamlit app - it should now show real data instead of mock data.

## Need Help with Table Schemas?
Look at the SQL comments in `data/athena.py` - they show the expected columns for each table.

## Still Stuck?
1. Check AWS permissions
2. Verify S3 paths match your uploads
3. Ensure column names/types match exactly