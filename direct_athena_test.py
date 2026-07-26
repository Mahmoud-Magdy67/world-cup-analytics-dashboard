#!/usr/bin/env python3
"""
Direct Athena query test to check if tables have data
"""

import os
import boto3
import time

def test_table_queries():
    """Test querying tables directly"""
    print("Testing direct table queries...")
    
    # Initialize Athena client
    aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    region_name = os.getenv('AWS_REGION', 'us-east-1')
    database_name = os.getenv('ATHENA_DATABASE', 'worldcup_2026')
    output_bucket = os.getenv('ATHENA_OUTPUT_BUCKET', 'aws-athena-query-results-worldcup')
    
    if not aws_access_key_id or not aws_secret_access_key:
        print("❌ AWS credentials not found")
        return
    
    try:
        client = boto3.client(
            'athena',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name
        )
    except Exception as e:
        print(f"❌ Failed to initialize Athena client: {e}")
        return
    
    # List of tables to test
    tables = [
        'wc26_dashboard_v16_live_july4',
        'v_winner_prediction_dashboard_v15_live_10m',
        'v_real_player_rows_enriched_v8',
        'v_team_schedule'
    ]
    
    # Test each table with a simple count query
    for table in tables:
        print(f"\nTesting table: {table}")
        try:
            query = f'SELECT COUNT(*) as row_count FROM "{database_name}"."{table}"'
            print(f"  Query: {query}")
            
            # Start query execution
            response = client.start_query_execution(
                QueryString=query,
                QueryExecutionContext={
                    'Database': database_name
                },
                ResultConfiguration={
                    'OutputLocation': f"s3://{output_bucket}/"
                }
            )
            
            query_execution_id = response['QueryExecutionId']
            print(f"  Query Execution ID: {query_execution_id}")
            
            # Wait for query to complete
            max_wait = 30
            waited = 0
            while waited < max_wait:
                response = client.get_query_execution(QueryExecutionId=query_execution_id)
                status = response['QueryExecution']['Status']['State']
                
                if status in ['SUCCEEDED']:
                    print(f"  Query status: {status}")
                    break
                elif status in ['FAILED', 'CANCELLED']:
                    reason = response['QueryExecution']['Status'].get('StateChangeReason', 'Unknown error')
                    print(f"  Query status: {status} - {reason}")
                    break
                
                print(f"  Waiting for query completion... ({waited}s)")
                time.sleep(2)
                waited += 2
            else:
                print("  Query timed out")
                continue
            
            # Get results if query succeeded
            if status == 'SUCCEEDED':
                results = client.get_query_results(QueryExecutionId=query_execution_id)
                if 'ResultSet' in results and 'Rows' in results['ResultSet']:
                    rows = results['ResultSet']['Rows']
                    if len(rows) >= 2:  # Header + data row
                        data_row = rows[1]  # First data row
                        if 'Data' in data_row and len(data_row['Data']) > 0:
                            count_value = data_row['Data'][0].get('VarCharValue', '0')
                            print(f"  Row count: {count_value}")
                        else:
                            print("  No data in result row")
                    else:
                        print("  No data rows in result")
                else:
                    print("  No ResultSet in response")
                    
        except Exception as e:
            print(f"  Error querying table {table}: {e}")

if __name__ == "__main__":
    test_table_queries()