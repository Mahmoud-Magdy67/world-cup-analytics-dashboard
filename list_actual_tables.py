import os
import boto3

def list_actual_tables():
    """List actual tables in the Athena database"""
    print("Listing actual tables in Athena database...")
    
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    
    if not aws_access_key_id or not aws_secret_access_key:
        print("❌ AWS credentials not found")
        return
    
    try:
        client = boto3.client(
            'athena',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        )
        
        database_name = os.getenv("ATHENA_DATABASE", "worldcup_2026")
        
        # Use SHOW TABLES query
        query = "SHOW TABLES"
        
        response = client.start_query_execution(
            QueryString=query,
            QueryExecutionContext={
                'Database': database_name
            },
            ResultConfiguration={
                'OutputLocation': f"s3://{os.getenv('ATHENA_OUTPUT_BUCKET', 'aws-athena-query-results-worldcup')}/"
            }
        )
        
        query_execution_id = response['QueryExecutionId']
        print(f"Query Execution ID: {query_execution_id}")
        
        # Wait for query to complete
        import time
        max_wait = 30
        waited = 0
        while waited < max_wait:
            response = client.get_query_execution(QueryExecutionId=query_execution_id)
            status = response['QueryExecution']['Status']['State']
            
            if status in ['SUCCEEDED']:
                print("✅ Query succeeded")
                break
            elif status in ['FAILED', 'CANCELLED']:
                reason = response['QueryExecution']['Status'].get('StateChangeReason', 'Unknown error')
                print(f"❌ Query failed: {reason}")
                return
            time.sleep(2)
            waited += 2
        else:
            print("❌ Query timed out")
            return
        
        # Get results
        print("Getting query results...")
        results = client.get_query_results(QueryExecutionId=query_execution_id)
        
        # Parse and display table names
        print("Actual tables in database:")
        if 'ResultSet' in results and 'Rows' in results['ResultSet']:
            rows = results['ResultSet']['Rows']
            print(f"Found {len(rows)} rows in result set")
            
            for i, row in enumerate(rows):
                if 'Data' in row and len(row['Data']) > 0:
                    # First row is typically the header
                    table_name = row['Data'][0].get('VarCharValue', '')
                    if i == 0:
                        print(f"Header: {table_name}")
                    else:
                        print(f"Table {i}: {table_name}")
                        
                        # Get row count for this table
                        if table_name:  # Make sure we have a table name
                            count_query = f"SELECT COUNT(*) as cnt FROM \"{database_name}\".\"{table_name}\""
                            try:
                                count_response = client.start_query_execution(
                                    QueryString=count_query,
                                    QueryExecutionContext={
                                        'Database': database_name
                                    },
                                    ResultConfiguration={
                                        'OutputLocation': f"s3://{os.getenv('ATHENA_OUTPUT_BUCKET', 'aws-athena-query-results-worldcup')}/"
                                    }
                                )
                                
                                count_execution_id = count_response['QueryExecutionId']
                                
                                # Wait for count query to complete
                                count_waited = 0
                                while count_waited < 30:
                                    count_resp = client.get_query_execution(QueryExecutionId=count_execution_id)
                                    count_status = count_resp['QueryExecution']['Status']['State']
                                    
                                    if count_status in ['SUCCEEDED']:
                                        count_results = client.get_query_results(QueryExecutionId=count_execution_id)
                                        if 'ResultSet' in count_results and 'Rows' in count_results['ResultSet']:
                                            if len(count_results['ResultSet']['Rows']) > 1:
                                                count_value = count_results['ResultSet']['Rows'][1]['Data'][0].get('VarCharValue', '0')
                                                print(f"  Rows: {count_value}")
                                        break
                                    elif count_status in ['FAILED', 'CANCELLED']:
                                        print(f"  Count query failed")
                                        break
                                    time.sleep(1)
                                    count_waited += 1
                            except Exception as e:
                                print(f"  Error getting count: {e}")
        
    except Exception as e:
        print(f"❌ Error listing tables: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    list_actual_tables()