# World Cup Analytics Dashboard - BigQuery to AWS Athena Migration

This repository contains scripts and documentation for migrating the World Cup Analytics Dashboard data from Google BigQuery to AWS Athena.

## Overview

The migration involves three main phases:
1. Exporting data from BigQuery to Amazon S3 in Parquet format
2. Setting up Athena tables to query the data in S3
3. Validating the migration and ensuring data integrity

## Prerequisites

### GCP Setup
- Service account with BigQuery read permissions
- BigQuery datasets containing World Cup analytics data

### AWS Setup
- AWS account with appropriate permissions
- S3 bucket for storing Parquet files
- S3 bucket for Athena query results
- Athena access permissions

### Local Environment
- Python 3.7+
- Required Python packages:
  ```bash
  pip install google-cloud-bigquery boto3 pandas pyarrow
  ```

## Migration Process

### 1. Check Current Export Status

First, check which tables have already been exported:

```bash
python check_status.py \
  --project-id your-gcp-project-id \
  --credentials /path/to/gcp-credentials.json \
  --bucket your-s3-bucket-name \
  --datasets world_cup_2026 world_cup_historical world_cup_player_stats world_cup_team_stats
```

This generates:
- `all_bq_tables.txt`: List of all BigQuery tables
- `s3_parquet_tables.txt`: List of tables already in S3
- `missing_tables.txt`: Tables that still need to be exported
- `migration_status.json`: Machine-readable status report

### 2. Export Data from BigQuery to S3

Export the remaining tables:

```bash
# Export all tables
python export_script.py

# Or export only critical tables for pilot testing
python export_script.py --pilot-mode

# Preview what tables would be exported without actually exporting
python export_script.py --dry-run
```

The export script will:
- Process tables in batches to avoid rate limiting
- Implement retry mechanisms for failed exports
- Save logs to `world_cup_migration.log`
- Generate `failed_tables.txt` if any exports fail

### 3. Set Up Athena Tables

Once data is in S3, create Athena tables:

```bash
python setup_athena.py \
  --region us-east-1 \
  --database world_cup_analytics \
  --s3-bucket your-data-bucket \
  --query-results-bucket your-query-results-bucket
```

This script will:
- Create the Athena database if it doesn't exist
- Discover Parquet files in S3
- Create external tables for each file
- Validate that tables can be queried

### 4. Validate Migration

After setup, validate the migration:

1. Check that all tables were created:
   ```bash
   python check_status.py --datasets world_cup_analytics
   ```

2. Run sample queries in Athena to verify data integrity

3. Compare row counts between BigQuery source and Athena tables

## Configuration

### Export Script Configuration

Update these values in `export_script.py`:

```python
# GCP Configuration
GCP_PROJECT_ID = "your-worldcup-project-id"
GCP_CREDENTIALS_PATH = "/path/to/gcp-service-account.json"

# AWS Configuration
AWS_BUCKET_NAME = "world-cup-analytics-data"
AWS_QUERY_RESULTS_BUCKET = "world-cup-analytics-query-results"
AWS_S3_PREFIX = "input/"
AWS_REGION = "us-east-1"

# Processing Configuration
BATCH_SIZE = 20
MAX_RETRIES = 5
```

### Athena Setup Configuration

The Athena setup script accepts command-line parameters:

```bash
python setup_athena.py \
  --region us-east-1 \
  --database world_cup_analytics \
  --s3-bucket your-data-bucket \
  --s3-prefix input/ \
  --query-results-bucket your-query-results-bucket
```

## Monitoring and Troubleshooting

### Logs
- `world_cup_migration.log`: Detailed export process logs
- Console output: Real-time progress information

### Common Issues

1. **Authentication Errors**
   - Verify GCP service account credentials
   - Check AWS credentials and permissions
   - Ensure buckets exist and are accessible

2. **Rate Limiting**
   - Reduce BATCH_SIZE
   - Increase DELAY_BETWEEN_TABLES and DELAY_BETWEEN_BATCHES

3. **Memory Issues with Large Tables**
   - The script automatically handles large tables with pagination
   - Monitor system resources during export

4. **Schema Mapping Problems**
   - Athena and BigQuery have different type systems
   - Check type mappings in `setup_athena.py`

## Performance Optimization

### For Faster Exports
- Increase batch size (monitor for rate limiting)
- Run during off-peak hours
- Use multiple instances for parallel processing of different datasets

### For Cost Optimization
- Use appropriate S3 storage classes
- Partition data logically to reduce query costs
- Monitor and clean up query result files periodically

## Security Considerations

- Store credentials securely (use IAM roles when possible)
- Encrypt data in transit and at rest
- Apply least privilege principles to service accounts
- Regularly rotate credentials

## Rollback Plan

In case of issues:
1. Revert application to use BigQuery backend
2. Preserve S3 data as backup
3. Address root cause of failure
4. Re-attempt migration with fixes

## Support

For issues with these scripts, contact the Data Engineering team.