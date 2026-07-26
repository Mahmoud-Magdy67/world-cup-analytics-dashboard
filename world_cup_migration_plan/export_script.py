#!/usr/bin/env python3
"""
World Cup Analytics Dashboard - BigQuery to S3 Export Script

This script implements the data migration from BigQuery to S3 as outlined in the 
migration plan. It follows the best practices identified in the bigquery-s3-export skill
and incorporates lessons learned from the World Cup migration reference.

Usage:
1. Update CONFIGURATION section with your settings
2. Ensure authentication is set up
3. Run the script

Features:
- Batch processing with configurable batch size
- Exponential backoff retry mechanism
- Rate limiting avoidance with delays
- Comprehensive logging
- Error handling and reporting
- Progress tracking
"""

import os
import boto3
import pandas as pd
from google.cloud import bigquery
import time
import logging
from typing import List, Tuple
import argparse

# Set up logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("world_cup_migration.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

###############################################################################
# CONFIGURATION - UPDATE THESE VALUES FOR YOUR USE CASE
###############################################################################

# GCP Configuration
GCP_PROJECT_ID = "your-worldcup-project-id"
GCP_CREDENTIALS_PATH = "/path/to/gcp-service-account.json"

# AWS Configuration
AWS_BUCKET_NAME = "world-cup-analytics-data"
AWS_QUERY_RESULTS_BUCKET = "world-cup-analytics-query-results"
AWS_S3_PREFIX = "input/"  # Prefix for S3 keys
AWS_REGION = "us-east-1"

# Processing Configuration
BATCH_SIZE = 20  # Optimized for World Cup data volume
MAX_RETRIES = 5
MAX_ROWS_PER_EXPORT = 100000
DELAY_BETWEEN_TABLES = 1.0  # seconds
DELAY_BETWEEN_BATCHES = 3.0  # seconds

# Table Selection (update based on assessment phase)
DATASETS_TO_EXPORT = [
    "world_cup_2026",
    "world_cup_historical",
    "world_cup_player_stats",
    "world_cup_team_stats"
]

# Critical tables that should be processed first
CRITICAL_TABLES = [
    "world_cup_2026.matches",
    "world_cup_2026.teams",
    "world_cup_2026.players",
    "world_cup_historical.champions",
]

###############################################################################
# UTILITY FUNCTIONS
###############################################################################

def setup_authentication():
    """Set up authentication for GCP and AWS"""
    # Set GCP credentials
    if os.path.exists(GCP_CREDENTIALS_PATH):
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = GCP_CREDENTIALS_PATH
        logger.info("GCP authentication configured")
    else:
        logger.warning(f"GCP credentials file not found: {GCP_CREDENTIALS_PATH}")
    
    # AWS credentials should be configured in ~/.aws/credentials or via environment variables

def initialize_clients():
    """Initialize BigQuery and S3 clients"""
    try:
        bq_client = bigquery.Client(project=GCP_PROJECT_ID)
        s3_client = boto3.client('s3', region_name=AWS_REGION)
        logger.info("Clients initialized successfully")
        return bq_client, s3_client
    except Exception as e:
        logger.error(f"Error initializing clients: {e}")
        raise

def list_bigquery_tables(bq_client) -> List[str]:
    """
    List all tables in specified BigQuery datasets
    
    Returns:
        List of table names in format "dataset.table_name"
    """
    all_tables = []
    
    for dataset_id in DATASETS_TO_EXPORT:
        try:
            dataset_ref = bq_client.dataset(dataset_id)
            tables = list(bq_client.list_tables(dataset_ref))
            for table in tables:
                all_tables.append(f"{dataset_id}.{table.table_id}")
                logger.debug(f"Found table: {dataset_id}.{table.table_id}")
        except Exception as e:
            logger.error(f"Error accessing dataset '{dataset_id}': {e}")
    
    logger.info(f"Discovered {len(all_tables)} tables across {len(DATASETS_TO_EXPORT)} datasets")
    return all_tables

def validate_prerequisites(s3_client):
    """Validate that required S3 buckets exist"""
    required_buckets = [AWS_BUCKET_NAME, AWS_QUERY_RESULTS_BUCKET]
    for bucket in required_buckets:
        try:
            s3_client.head_bucket(Bucket=bucket)
            logger.info(f"S3 bucket '{bucket}' exists and is accessible")
        except Exception as e:
            logger.error(f"S3 bucket '{bucket}' is not accessible: {e}")
            raise

###############################################################################
# EXPORT FUNCTIONS
###############################################################################

def export_table_to_s3(bq_client, s3_client, dataset, table):
    """
    Export a single table from BigQuery to S3 as parquet
    """
    try:
        logger.info(f"Exporting {dataset}.{table}")
        
        # Get table information
        table_ref = bq_client.dataset(dataset).table(table)
        table_obj = bq_client.get_table(table_ref)
        logger.info(f"Table has {table_obj.num_rows} rows and {len(table_obj.schema)} columns")
        
        # For very large tables, handle with pagination
        if table_obj.num_rows > MAX_ROWS_PER_EXPORT:
            logger.info(f"Handling large table with pagination ({table_obj.num_rows} rows)")
            return export_large_table_with_pagination(bq_client, s3_client, dataset, table, table_obj)
        
        # Export table to DataFrame
        query = f"SELECT * FROM `{table_obj.project}.{table_obj.dataset_id}.{table_obj.table_id}`"
        logger.debug(f"Executing query: {query}")
        df = bq_client.query(query).result().to_dataframe()
        logger.info(f"Downloaded DataFrame with shape: {df.shape}")
        
        # Save as parquet locally
        local_file = f"{table}.parquet"
        df.to_parquet(local_file, index=False, compression='snappy')
        file_size = os.path.getsize(local_file)
        logger.info(f"Saved as parquet file: {local_file} ({file_size} bytes)")
        
        # Upload to S3
        s3_key = f"{AWS_S3_PREFIX}{table}.parquet"
        s3_client.upload_file(local_file, AWS_BUCKET_NAME, s3_key)
        logger.info(f"Successfully uploaded {local_file} to s3://{AWS_BUCKET_NAME}/{s3_key}")
        
        # Clean up local file
        os.remove(local_file)
        logger.info("Cleaned up local file")
        
        return True
        
    except Exception as e:
        logger.error(f"Error exporting {dataset}.{table}: {e}")
        return False

def export_large_table_with_pagination(bq_client, s3_client, dataset, table, table_obj):
    """
    Export large tables by reading them in chunks
    """
    try:
        logger.info(f"Exporting large table {dataset}.{table} with pagination")
        
        # Process table in chunks
        chunk_size = 50000  # Process 50K rows at a time
        total_rows = table_obj.num_rows
        offset = 0
        all_dataframes = []
        
        while offset < total_rows:
            # Query with pagination
            query = f"""
                SELECT * FROM `{table_obj.project}.{table_obj.dataset_id}.{table_obj.table_id}`
                LIMIT {chunk_size} OFFSET {offset}
            """
            
            logger.debug(f"Exporting chunk {offset//chunk_size + 1} with query: {query}")
            df_chunk = bq_client.query(query).result().to_dataframe()
            all_dataframes.append(df_chunk)
            
            logger.info(f"Exported chunk {offset//chunk_size + 1}: {len(df_chunk)} rows")
            offset += chunk_size
            
            # Add delay to avoid rate limiting
            time.sleep(0.5)
        
        # Combine all chunks
        df = pd.concat(all_dataframes, ignore_index=True)
        logger.info(f"Combined all chunks into DataFrame with shape: {df.shape}")
        
        # Save as parquet locally
        local_file = f"{table}.parquet"
        df.to_parquet(local_file, index=False, compression='snappy')
        file_size = os.path.getsize(local_file)
        logger.info(f"Saved as parquet file: {local_file} ({file_size} bytes)")
        
        # Upload to S3
        s3_key = f"{AWS_S3_PREFIX}{table}.parquet"
        s3_client.upload_file(local_file, AWS_BUCKET_NAME, s3_key)
        logger.info(f"Successfully uploaded {local_file} to s3://{AWS_BUCKET_NAME}/{s3_key}")
        
        # Clean up local file
        os.remove(local_file)
        logger.info("Cleaned up local file")
        
        return True
        
    except Exception as e:
        logger.error(f"Error exporting large table {dataset}.{table}: {e}")
        return False

def export_with_retry(bq_client, s3_client, dataset, table, max_retries=MAX_RETRIES):
    """
    Export table with exponential backoff retry
    """
    for attempt in range(max_retries):
        if attempt > 0:
            logger.info(f"Retry attempt {attempt} for {dataset}.{table}")
            # Exponential backoff with jitter
            delay = (2 ** attempt) + (attempt * 0.1)
            time.sleep(delay)
        
        if export_table_to_s3(bq_client, s3_client, dataset, table):
            return True
    
    logger.error(f"Failed to export {dataset}.{table} after {max_retries} attempts")
    return False

def process_batch(bq_client, s3_client, tables_batch, batch_num, total_batches):
    """
    Process a batch of tables
    """
    logger.info(f"Processing batch {batch_num}/{total_batches} with {len(tables_batch)} tables")
    
    success_count = 0
    failed_tables = []
    
    for i, table_full_name in enumerate(tables_batch):
        dataset, table = table_full_name.split('.')
        
        if export_with_retry(bq_client, s3_client, dataset, table):
            success_count += 1
            logger.info(f"Successfully exported {table_full_name} ({i+1}/{len(tables_batch)})")
        else:
            failed_tables.append(table_full_name)
            logger.error(f"Failed to export {table_full_name} after retries")
        
        # Add a small delay between tables to avoid rate limiting
        if i < len(tables_batch) - 1:  # Don't sleep after the last table
            time.sleep(DELAY_BETWEEN_TABLES)
    
    logger.info(f"Batch {batch_num} completed: {success_count}/{len(tables_batch)} successful")
    return failed_tables

def prioritize_tables(all_tables: List[str]) -> Tuple[List[str], List[str]]:
    """
    Prioritize tables by moving critical tables to the front
    
    Returns:
        Tuple of (critical_tables, remaining_tables)
    """
    # Separate critical tables from others
    critical_set = set(CRITICAL_TABLES)
    critical = [t for t in all_tables if t in critical_set]
    remaining = [t for t in all_tables if t not in critical_set]
    
    logger.info(f"Prioritized {len(critical)} critical tables for early processing")
    return critical, remaining

def main():
    """
    Main function to export tables
    """
    logger.info("Starting World Cup Analytics Dashboard BigQuery to S3 export process")
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Export World Cup data from BigQuery to S3')
    parser.add_argument('--dry-run', action='store_true', help='List tables without exporting')
    parser.add_argument('--pilot-mode', action='store_true', help='Export only critical tables')
    args = parser.parse_args()
    
    # Set up authentication
    setup_authentication()
    
    # Initialize clients
    try:
        bq_client, s3_client = initialize_clients()
    except Exception as e:
        logger.error(f"Failed to initialize clients: {e}")
        return 1
    
    # Validate prerequisites
    try:
        validate_prerequisites(s3_client)
    except Exception as e:
        logger.error(f"Prerequisite validation failed: {e}")
        return 1
    
    # List BigQuery tables
    logger.info("Discovering BigQuery tables...")
    all_tables = list_bigquery_tables(bq_client)
    logger.info(f"Found {len(all_tables)} total tables")
    
    if args.dry_run:
        logger.info("DRY RUN MODE - Listing tables without exporting:")
        for table in all_tables:
            print(table)
        return 0
    
    # Prioritize tables if not in pilot mode
    if args.pilot_mode:
        tables_to_export = CRITICAL_TABLES
        logger.info(f"PILOT MODE - Exporting only {len(tables_to_export)} critical tables")
    else:
        critical_tables, remaining_tables = prioritize_tables(all_tables)
        tables_to_export = critical_tables + remaining_tables
        logger.info(f"Preparing to export {len(tables_to_export)} tables ({len(critical_tables)} critical)")
    
    # Process tables in batches
    failed_tables = []
    total_batches = (len(tables_to_export) + BATCH_SIZE - 1) // BATCH_SIZE
    
    start_time = time.time()
    logger.info(f"Starting export of {len(tables_to_export)} tables in {total_batches} batches")
    
    for i in range(0, len(tables_to_export), BATCH_SIZE):
        batch_num = i // BATCH_SIZE + 1
        batch = tables_to_export[i:i+BATCH_SIZE]
        
        batch_failed = process_batch(bq_client, s3_client, batch, batch_num, total_batches)
        failed_tables.extend(batch_failed)
        
        progress = min(i+BATCH_SIZE, len(tables_to_export))
        logger.info(f"Overall progress: {progress}/{len(tables_to_export)} tables")
        
        # Add a delay between batches
        if i + BATCH_SIZE < len(tables_to_export):
            logger.info(f"Waiting {DELAY_BETWEEN_BATCHES}s before next batch...")
            time.sleep(DELAY_BETWEEN_BATCHES)
    
    # Calculate duration
    end_time = time.time()
    duration_minutes = (end_time - start_time) / 60
    
    # Report final results
    logger.info("=" * 70)
    logger.info("EXPORT PROCESS COMPLETED")
    logger.info(f"Total tables attempted: {len(tables_to_export)}")
    logger.info(f"Successful exports: {len(tables_to_export) - len(failed_tables)}")
    logger.info(f"Failed exports: {len(failed_tables)}")
    logger.info(f"Total duration: {duration_minutes:.1f} minutes")
    
    if failed_tables:
        logger.error("Failed tables:")
        for table in failed_tables:
            logger.error(f"  - {table}")
        
        # Save failed tables to a file
        with open('failed_tables.txt', 'w') as f:
            for table in failed_tables:
                f.write(f"{table}\n")
        logger.info("Failed tables saved to failed_tables.txt")
    else:
        logger.info("All tables exported successfully!")
    
    return 0 if len(failed_tables) == 0 else 1

if __name__ == "__main__":
    exit(main())