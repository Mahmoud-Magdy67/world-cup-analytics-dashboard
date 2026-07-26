#!/usr/bin/env python3
"""
World Cup Analytics Dashboard - Athena Table Setup

This script creates Athena tables for the World Cup Analytics Dashboard
after data has been exported from BigQuery to S3 in Parquet format.

The script:
1. Connects to AWS Athena
2. Creates database if it doesn't exist
3. Creates external tables pointing to S3 Parquet files
4. Validates table creation
"""

import boto3
import time
import argparse
from typing import List, Dict
import json

def initialize_athena_client(region_name: str, aws_profile: str = None):
    """
    Initialize Athena client
    
    Args:
        region_name: AWS region
        aws_profile: AWS profile name (optional)
        
    Returns:
        Athena client
    """
    if aws_profile:
        session = boto3.Session(profile_name=aws_profile)
        client = session.client('athena', region_name=region_name)
    else:
        client = boto3.client('athena', region_name=region_name)
    
    return client

def execute_athena_query(client, query: str, database: str, output_location: str) -> str:
    """
    Execute an Athena query and return the query execution ID
    
    Args:
        client: Athena client
        query: SQL query to execute
        database: Database name
        output_location: S3 location for query results
        
    Returns:
        Query execution ID
    """
    response = client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={'Database': database},
        ResultConfiguration={'OutputLocation': output_location}
    )
    return response['QueryExecutionId']

def wait_for_query_completion(client, query_execution_id: str, timeout: int = 300) -> Dict:
    """
    Wait for Athena query to complete
    
    Args:
        client: Athena client
        query_execution_id: Query execution ID
        timeout: Timeout in seconds
        
    Returns:
        Query execution details
    """
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        response = client.get_query_execution(QueryExecutionId=query_execution_id)
        status = response['QueryExecution']['Status']['State']
        
        if status in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
            return response['QueryExecution']
        
        time.sleep(2)
    
    raise TimeoutError(f"Query {query_execution_id} did not complete within {timeout} seconds")

def get_query_results(client, query_execution_id: str):
    """
    Get results of an Athena query
    
    Args:
        client: Athena client
        query_execution_id: Query execution ID
        
    Returns:
        Query results
    """
    results = []
    next_token = None
    
    while True:
        if next_token:
            response = client.get_query_results(QueryExecutionId=query_execution_id, NextToken=next_token)
        else:
            response = client.get_query_results(QueryExecutionId=query_execution_id)
        
        results.extend(response['ResultSet']['Rows'])
        
        next_token = response.get('NextToken')
        if not next_token:
            break
    
    return results

def create_database_if_not_exists(client, database_name: str, output_location: str) -> bool:
    """
    Create Athena database if it doesn't exist
    
    Args:
        client: Athena client
        database_name: Name of the database to create
        output_location: S3 location for query results
        
    Returns:
        True if database was created or already existed
    """
    try:
        query = f"CREATE DATABASE IF NOT EXISTS {database_name}"
        query_id = execute_athena_query(client, query, 'default', output_location)
        execution = wait_for_query_completion(client, query_id)
        
        if execution['Status']['State'] == 'SUCCEEDED':
            print(f"Database '{database_name}' is ready")
            return True
        else:
            print(f"Failed to create database: {execution['Status']['StateChangeReason']}")
            return False
    except Exception as e:
        print(f"Error creating database: {e}")
        return False

def get_table_schema_from_bigquery_sample(table_name: str) -> List[Dict]:
    """
    This is a simplified function. In a real implementation, you would:
    1. Either connect to BigQuery to get the actual schema
    2. Or read from a schema definition file
    
    For this example, we'll return a sample schema for common World Cup tables.
    """
    # Sample schemas for common World Cup tables
    sample_schemas = {
        "matches": [
            {"name": "match_id", "type": "STRING"},
            {"name": "date", "type": "DATE"},
            {"name": "time", "type": "STRING"},
            {"name": "stage", "type": "STRING"},
            {"name": "stadium", "type": "STRING"},
            {"name": "team_home", "type": "STRING"},
            {"name": "team_away", "type": "STRING"},
            {"name": "goals_home", "type": "INTEGER"},
            {"name": "goals_away", "type": "INTEGER"},
            {"name": "possession_home", "type": "DOUBLE"},
            {"name": "possession_away", "type": "DOUBLE"},
            {"name": "attendance", "type": "INTEGER"}
        ],
        "teams": [
            {"name": "team_id", "type": "STRING"},
            {"name": "country", "type": "STRING"},
            {"name": "group", "type": "STRING"},
            {"name": "fifa_ranking", "type": "INTEGER"},
            {"name": "coach", "type": "STRING"}
        ],
        "players": [
            {"name": "player_id", "type": "STRING"},
            {"name": "name", "type": "STRING"},
            {"name": "team_id", "type": "STRING"},
            {"name": "position", "type": "STRING"},
            {"name": "age", "type": "INTEGER"},
            {"name": "goals", "type": "INTEGER"},
            {"name": "assists", "type": "INTEGER"},
            {"name": "yellow_cards", "type": "INTEGER"},
            {"name": "red_cards", "type": "INTEGER"}
        ],
        "champions": [
            {"name": "year", "type": "INTEGER"},
            {"name": "country", "type": "STRING"},
            {"name": "wins", "type": "INTEGER"}
        ]
    }
    
    # Try to match table name to sample schemas
    for key in sample_schemas:
        if key in table_name.lower():
            return sample_schemas[key]
    
    # Default schema if no match found
    return [
        {"name": "id", "type": "STRING"},
        {"name": "name", "type": "STRING"},
        {"name": "value", "type": "DOUBLE"}
    ]

def map_bigquery_type_to_athena(bigquery_type: str) -> str:
    """
    Map BigQuery data types to Athena-compatible types
    
    Args:
        bigquery_type: BigQuery data type
        
    Returns:
        Athena-compatible data type
    """
    type_mapping = {
        'STRING': 'STRING',
        'INTEGER': 'INTEGER',
        'INT64': 'BIGINT',
        'FLOAT': 'DOUBLE',
        'FLOAT64': 'DOUBLE',
        'BOOLEAN': 'BOOLEAN',
        'BOOL': 'BOOLEAN',
        'TIMESTAMP': 'TIMESTAMP',
        'DATE': 'DATE',
        'TIME': 'STRING',  # Athena doesn't have TIME type
        'DATETIME': 'TIMESTAMP',
        'BYTES': 'BINARY',
        'NUMERIC': 'DECIMAL(38,9)',
        'BIGNUMERIC': 'DECIMAL(38,9)'
    }
    
    return type_mapping.get(bigquery_type.upper(), 'STRING')

def create_external_table(client, database: str, table_name: str, s3_location: str, 
                         output_location: str, schema: List[Dict] = None) -> bool:
    """
    Create an external table in Athena for a Parquet file in S3
    
    Args:
        client: Athena client
        database: Database name
        table_name: Table name
        s3_location: S3 location of the Parquet file
        output_location: S3 location for query results
        schema: Table schema (if None, will try to infer)
        
    Returns:
        True if table was created successfully
    """
    try:
        # If no schema provided, try to get from sample
        if schema is None:
            schema = get_table_schema_from_bigquery_sample(table_name)
            print(f"Using sample schema for table '{table_name}'")
        
        # Build column definitions
        columns = []
        for col in schema:
            athena_type = map_bigquery_type_to_athena(col['type'])
            columns.append(f"`{col['name']}` {athena_type}")
        
        columns_def = ",\n  ".join(columns)
        
        # Create the CREATE TABLE statement
        query = f"""
        CREATE EXTERNAL TABLE IF NOT EXISTS `{database}`.`{table_name}` (
          {columns_def}
        )
        STORED AS PARQUET
        LOCATION '{s3_location}'
        tblproperties ("parquet.compression"="SNAPPY")
        """
        
        print(f"Creating table '{table_name}'...")
        print(f"Query: {query}")
        
        query_id = execute_athena_query(client, query, database, output_location)
        execution = wait_for_query_completion(client, query_id)
        
        if execution['Status']['State'] == 'SUCCEEDED':
            print(f"Table '{table_name}' created successfully")
            return True
        else:
            error_msg = execution['Status']['StateChangeReason']
            print(f"Failed to create table '{table_name}': {error_msg}")
            return False
            
    except Exception as e:
        print(f"Error creating table '{table_name}': {e}")
        return False

def list_s3_parquet_files(s3_client, bucket_name: str, prefix: str = "") -> List[str]:
    """
    List all Parquet files in an S3 bucket
    
    Args:
        s3_client: S3 client
        bucket_name: S3 bucket name
        prefix: Optional prefix
        
    Returns:
        List of table names (file names without extension)
    """
    parquet_files = []
    
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)
        
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    if obj['Key'].endswith('.parquet'):
                        # Extract table name from file path
                        table_name = obj['Key'].replace(prefix, '').replace('.parquet', '')
                        parquet_files.append(table_name)
                        
    except Exception as e:
        print(f"Error listing S3 files: {e}")
    
    return parquet_files

def validate_table(client, database: str, table_name: str, output_location: str) -> bool:
    """
    Validate that a table exists and can be queried
    
    Args:
        client: Athena client
        database: Database name
        table_name: Table name
        output_location: S3 location for query results
        
    Returns:
        True if table is valid
    """
    try:
        # Simple COUNT(*) query to validate table
        query = f"SELECT COUNT(*) as row_count FROM `{database}`.`{table_name}`"
        query_id = execute_athena_query(client, query, database, output_location)
        execution = wait_for_query_completion(client, query_id)
        
        if execution['Status']['State'] == 'SUCCEEDED':
            results = get_query_results(client, query_id)
            if len(results) > 1:  # Header + data row
                row_count = results[1]['Data'][0]['VarCharValue']
                print(f"Table '{table_name}' validated with {row_count} rows")
                return True
            else:
                print(f"Table '{table_name}' exists but no data returned")
                return True
        else:
            print(f"Failed to validate table '{table_name}': {execution['Status']['StateChangeReason']}")
            return False
    except Exception as e:
        print(f"Error validating table '{table_name}': {e}")
        return False

def main(aws_region: str, database_name: str, s3_bucket: str, s3_prefix: str,
         query_results_bucket: str, aws_profile: str = None, 
         tables: List[str] = None):
    """
    Main function to set up Athena tables
    
    Args:
        aws_region: AWS region
        database_name: Athena database name
        s3_bucket: S3 bucket containing Parquet files
        s3_prefix: S3 prefix for Parquet files
        query_results_bucket: S3 bucket for Athena query results
        aws_profile: AWS profile name (optional)
        tables: Specific tables to create (if None, will discover from S3)
    """
    print("Setting up Athena tables for World Cup Analytics Dashboard...")
    
    # Initialize clients
    athena_client = initialize_athena_client(aws_region, aws_profile)
    s3_client = boto3.client('s3', region_name=aws_region)
    
    # Output location for Athena query results
    output_location = f"s3://{query_results_bucket}/athena-results/"
    
    # Create database if it doesn't exist
    if not create_database_if_not_exists(athena_client, database_name, output_location):
        print("Failed to create database. Exiting.")
        return False
    
    # Determine which tables to create
    if tables is None:
        # Discover tables from S3
        print("Discovering tables from S3...")
        tables = list_s3_parquet_files(s3_client, s3_bucket, s3_prefix)
        print(f"Found {len(tables)} tables in S3")
    
    # Create tables
    successful_tables = []
    failed_tables = []
    
    for table_name in tables:
        s3_location = f"s3://{s3_bucket}/{s3_prefix}{table_name}.parquet"
        
        if create_external_table(athena_client, database_name, table_name, 
                               s3_location, output_location):
            successful_tables.append(table_name)
            
            # Validate the table
            if validate_table(athena_client, database_name, table_name, output_location):
                print(f"✓ Table '{table_name}' is ready for querying")
            else:
                print(f"⚠ Table '{table_name}' was created but validation failed")
        else:
            failed_tables.append(table_name)
    
    # Summary
    print("\n" + "="*60)
    print("ATHENA TABLE SETUP SUMMARY")
    print("="*60)
    print(f"Database: {database_name}")
    print(f"Total tables processed: {len(tables)}")
    print(f"Successful: {len(successful_tables)}")
    print(f"Failed: {len(failed_tables)}")
    
    if failed_tables:
        print("\nFailed tables:")
        for table in failed_tables:
            print(f"  - {table}")
        return False
    else:
        print(f"\n✓ All {len(successful_tables)} tables created successfully!")
        print(f"Database '{database_name}' is ready for querying.")
        return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Set up Athena tables for World Cup Analytics Dashboard')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--database', default='world_cup_analytics', help='Athena database name')
    parser.add_argument('--s3-bucket', required=True, help='S3 bucket containing Parquet files')
    parser.add_argument('--s3-prefix', default='input/', help='S3 prefix for Parquet files')
    parser.add_argument('--query-results-bucket', required=True, help='S3 bucket for Athena query results')
    parser.add_argument('--profile', help='AWS profile name')
    parser.add_argument('--tables', nargs='+', help='Specific tables to create (default: discover from S3)')
    
    args = parser.parse_args()
    
    success = main(
        aws_region=args.region,
        database_name=args.database,
        s3_bucket=args.s3_bucket,
        s3_prefix=args.s3_prefix,
        query_results_bucket=args.query_results_bucket,
        aws_profile=args.profile,
        tables=args.tables
    )
    
    exit(0 if success else 1)