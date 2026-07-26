import os
import boto3

def check_database_contents():
    """Check what's in the Athena database"""
    print("Checking contents of Athena database...")
    
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
        
        # Try simple SHOW VIEWS query
        query = "SHOW VIEWS"
        
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
        print(f"SHOW VIEWS Query Execution ID: {query_execution_id}")
        
        # Wait for query to complete
        import time
        max_wait = 30
        waited = 0
        while waited < max_wait:
            response = client.get_query_execution(QueryExecutionId=query_execution_id)
            status = response['QueryExecution']['Status']['State']
            
            if status in ['SUCCEEDED']:
                print("✅ SHOW VIEWS query succeeded")
                break
            elif status in ['FAILED', 'CANCELLED']:
                reason = response['QueryExecution']['Status'].get('StateChangeReason', 'Unknown error')
                print(f"❌ SHOW VIEWS query failed: {reason}")
                
                # Try DESCRIBE DATABASE as an alternate approach
                return check_describe_database(client, database_name)
            time.sleep(2)
            waited += 2
        else:
            print("❌ SHOW VIEWS query timed out")
            return
        
        # Get results
        results = client.get_query_results(QueryExecutionId=query_execution_id)
        
        # Parse and display views
        print("Views in database:")
        if 'ResultSet' in results and 'Rows' in results['ResultSet']:
            rows = results['ResultSet']['Rows']
            print(f"Found {len(rows)} rows in result set")
            
            view_names = []
            for i, row in enumerate(rows):
                if 'Data' in row and len(row['Data']) > 0:
                    view_name = row['Data'][0].get('VarCharValue', '')
                    if i == 0:
                        print(f"Header: {view_name}")
                    else:
                        print(f"View: {view_name}")
                        view_names.append(view_name)
            
            # Check row counts for each view
            print("\nRow counts for views:")
            for view_name in view_names:
                try:
                    count_query = f"SELECT COUNT(*) as cnt FROM \"{database_name}\".\"{view_name}\""
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
                                    print(f"  {view_name}: {count_value} rows")
                            break
                        elif count_status in ['FAILED', 'CANCELLED']:
                            print(f"  {view_name}: Count query failed")
                            break
                        time.sleep(1)
                        count_waited += 1
                except Exception as e:
                    print(f"  {view_name}: Error getting count - {e}")
        
    except Exception as e:
        print(f"❌ Error checking database contents: {e}")
        import traceback
        traceback.print_exc()

def check_describe_database(client, database_name):
    """Alternate method to check database"""
    print("Trying DESCRIBE DATABASE approach...")
    
    try:
        query = f"DESCRIBE DATABASE {database_name}"
        
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
        print(f"DESCRIBE DATABASE Query Execution ID: {query_execution_id}")
        
        # Wait for query to complete
        import time
        max_wait = 30
        waited = 0
        while waited < max_wait:
            response = client.get_query_execution(QueryExecutionId=query_execution_id)
            status = response['QueryExecution']['Status']['State']
            
            if status in ['SUCCEEDED']:
                print("✅ DESCRIBE DATABASE query succeeded")
                break
            elif status in ['FAILED', 'CANCELLED']:
                reason = response['QueryExecution']['Status'].get('StateChangeReason', 'Unknown error')
                print(f"❌ DESCRIBE DATABASE query failed: {reason}")
                return
            time.sleep(2)
            waited += 2
        else:
            print("❌ DESCRIBE DATABASE query timed out")
            return
        
        # Get results
        results = client.get_query_results(QueryExecutionId=query_execution_id)
        
        # Display results
        print("Database description:")
        if 'ResultSet' in results and 'Rows' in results['ResultSet']:
            for row in results['ResultSet']['Rows']:
                if 'Data' in row:
                    print(f"  {row['Data']}")
        
    except Exception as e:
        print(f"❌ Error with alternate approach: {e}")

if __name__ == "__main__":
    check_database_contents()