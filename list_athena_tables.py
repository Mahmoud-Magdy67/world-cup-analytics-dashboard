import os
import boto3

def list_athena_tables():
    """List all tables in the Athena database"""
    print("Listing tables in Athena database...")
    
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
        
        # List all tables in the database
        query = f"SHOW TABLES IN `{os.getenv('ATHENA_DATABASE', 'worldcup_2026')}`"
        
        # Start query execution
        response = client.start_query_execution(
            QueryString=query,
            QueryExecutionContext={
                'Database': os.getenv("ATHENA_DATABASE", "worldcup_2026")
            },
            ResultConfiguration={
                'OutputLocation': f"s3://{os.getenv('ATHENA_OUTPUT_BUCKET', 'aws-athena-query-results-worldcup')}/"
            }
        )
        
        query_execution_id = response['QueryExecutionId']
        
        # Wait for query to complete
        import time
        while True:
            response = client.get_query_execution(QueryExecutionId=query_execution_id)
            status = response['QueryExecution']['Status']['State']
            
            if status in ['SUCCEEDED']:
                break
            elif status in ['FAILED', 'CANCELLED']:
                reason = response['QueryExecution']['Status'].get('StateChangeReason', 'Unknown error')
                print(f"❌ Query failed: {reason}")
                return
            time.sleep(1)
        
        # Get results
        results = client.get_query_results(QueryExecutionId=query_execution_id)
        
        # Print table names
        print("Tables in database:")
        if 'ResultSet' in results and 'Rows' in results['ResultSet']:
            for i, row in enumerate(results['ResultSet']['Rows']):
                if 'Data' in row and len(row['Data']) > 0:
                    table_name = row['Data'][0].get('VarCharValue', '')
                    if table_name and table_name != 'tab_name':  # Skip header
                        print(f"  - {table_name}")
                        
                        # Get row count for each table
                        count_query = f"SELECT COUNT(*) as cnt FROM `{os.getenv('ATHENA_DATABASE', 'worldcup_2026')}`.`{table_name}`"
                        try:
                            count_response = client.start_query_execution(
                                QueryString=count_query,
                                QueryExecutionContext={
                                    'Database': os.getenv("ATHENA_DATABASE", "worldcup_2026")
                                },
                                ResultConfiguration={
                                    'OutputLocation': f"s3://{os.getenv('ATHENA_OUTPUT_BUCKET', 'aws-athena-query-results-worldcup')}/"
                                }
                            )
                            
                            count_execution_id = count_response['QueryExecutionId']
                            
                            # Wait for count query to complete
                            while True:
                                count_resp = client.get_query_execution(QueryExecutionId=count_execution_id)
                                count_status = count_resp['QueryExecution']['Status']['State']
                                
                                if count_status in ['SUCCEEDED']:
                                    break
                                elif count_status in ['FAILED', 'CANCELLED']:
                                    break
                                time.sleep(1)
                            
                            if count_status == 'SUCCEEDED':
                                count_results = client.get_query_results(QueryExecutionId=count_execution_id)
                                if 'ResultSet' in count_results and 'Rows' in count_results['ResultSet']:
                                    if len(count_results['ResultSet']['Rows']) > 1:  # Skip header
                                        count_value = count_results['ResultSet']['Rows'][1]['Data'][0].get('VarCharValue', '0')
                                        print(f"    Rows: {count_value}")
                        except Exception as e:
                            print(f"    Error getting count: {e}")
        
    except Exception as e:
        print(f"❌ Error listing tables: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    list_athena_tables()