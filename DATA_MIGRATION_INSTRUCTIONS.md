# World Cup Analytics Dashboard - Data Migration Instructions

## Problem
The Streamlit app has been migrated from BigQuery to AWS Athena, but the actual World Cup data has not been transferred. All Athena tables are currently empty.

## Solution Overview
This document provides step-by-step instructions to migrate the World Cup 2026 data from BigQuery to AWS Athena.

## Prerequisites
1. GCP Service Account credentials with BigQuery access
2. AWS credentials with S3 and Athena permissions
3. Python 3.8+ with required packages

## Step 1: Export Data from BigQuery

1. Set environment variables:
```bash
export GCP_SERVICE_ACCOUNT_KEY="your_base64_encoded_service_account_key"
export GCP_PROJECT_ID="project-2f1e456e-b1be-4551-92b"
```

2. Run the export script:
```bash
cd /path/to/world-cup-analytics-dashboard
python export_bigquery_data.py
```

3. This will create a `exported_data` directory with CSV and Parquet files for each table.

## Step 2: Upload Data to S3

1. Create an S3 bucket (or use existing one):
```bash
export S3_DATA_BUCKET="wc2026-simulation-data"
```

2. Upload the exported files to S3 using AWS CLI:
```bash
# Create a folder for the migrated data
aws s3 mkdir s3://$S3_DATA_BUCKET/migrated-from-bigquery/

# Upload all files
aws s3 cp exported_data/ s3://$S3_DATA_BUCKET/migrated-from-bigquery/ --recursive
```

## Step 3: Create Athena Tables

1. Go to AWS Athena console
2. Select the `worldcup_2026` database
3. For each table, create an external table pointing to the S3 location:

### Example for wc26_dashboard_v16_live_july4:
```sql
CREATE EXTERNAL TABLE IF NOT EXISTS worldcup_2026.wc26_dashboard_v16_live_july4 (
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
LOCATION 's3://wc2026-simulation-data/migrated-from-bigquery/wc26_dashboard_v16_live_july4.parquet';
```

Repeat this for all tables:
- v_winner_prediction_dashboard_v15_live_10m
- v_real_player_rows_enriched_v8
- v_team_schedule
- v_teams_clean

Note: You'll need to adjust the column definitions based on the actual schema of each table.

## Step 4: Verify Data Migration

1. Test a simple query in Athena:
```sql
SELECT COUNT(*) as cnt FROM worldcup_2026.wc26_dashboard_v16_live_july4;
```

2. The result should show the actual number of rows (48 for teams table), not 0.

## Step 5: Test Streamlit App

1. Redeploy or restart the Streamlit app
2. Navigate to the app and verify that:
   - Data is loading (no more empty tables)
   - Charts are displaying actual data
   - No more mock data warnings

## Troubleshooting

### If you see "Access Denied" errors:
- Check that your AWS credentials have the necessary permissions
- Verify the S3 bucket policies allow Athena to read the data

### If tables are still showing 0 rows:
- Verify the S3 paths in your CREATE TABLE statements
- Check that the Parquet files were uploaded correctly
- Ensure the file formats match what you're declaring in the table schema

### If you get column mismatch errors:
- Examine the actual schema of your exported data
- Adjust the CREATE TABLE statements to match the actual columns and data types

## Important Notes

1. **Schema Matching**: The column names and data types in your Athena tables must exactly match what the Streamlit app expects (as defined in `data/athena.py`).

2. **Permissions**: Your AWS credentials need:
   - S3 read access to the bucket containing your data
   - Athena query execution permissions
   - Glue Data Catalog read permissions (to view tables)

3. **Costs**: Athena charges per query volume, so larger queries will cost more.

4. **Performance**: Using Parquet format will provide better query performance than CSV.

## Next Steps After Migration

1. Set up automated data refresh if needed
2. Add monitoring for data quality
3. Optimize table partitions for frequently queried dimensions
4. Set up alerts for query performance or cost monitoring