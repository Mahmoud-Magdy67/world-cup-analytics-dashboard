import os
import boto3

def check_for_views():
    """Check if there are views instead of tables in the database"""
    print("Checking for views in Athena database...")
    
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
        
        # Try INFORMATION_SCHEMA to see all relations (tables and views)
        query = """
        SELECT table_name, table_type 
        FROM information_schema.tables 
        WHERE table_schema = %s
        """
        
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
                # Try alternate approach
                return check_with_show_views(client, database_name)
            time.sleep(2)
            waited += 2
        else:
            print("❌ Query timed out")
            return
        
        # Get results
        results = client.get_query_results(QueryExecutionId=query_execution_id)
        
        # Parse and display relations
        print("Relations in database:")
        if 'ResultSet' in results and 'Rows' in results['ResultSet']:
            rows = results['ResultSet']['Rows']
            print(f"Found {len(rows)} rows in result set")
            
            for i, row in enumerate(rows):
                if 'Data' in row and len(row['Data']) >= 2:
                    name = row['Data'][0].get('VarCharValue', '')
                    type_val = row['Data'][1].get('VarCharValue', '')
                    if i == 0:
                        print(f"Header: {name}, {type_val}")
                    else:
                        print(f"{type_val}: {name}")
        
    except Exception as e:
        print(f"❌ Error checking relations: {e}")

def check_with_show_views(client, database_name):
    """Alternate method to check for views"""
    print("Trying alternate approach with SHOW VIEWS...")
    
    try:
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
                return
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
            
            for i, row in enumerate(rows):
                if 'Data' in row and len(row['Data']) > 0:
                    view_name = row['Data'][0].get('VarCharValue', '')
                    if i == 0:
                        print(f"Header: {view_name}")
                    else:
                        print(f"View: {view_name}")
                        
    except Exception as e:
        print(f"❌ Error with alternate approach: {e}")

if __name__ == "__main__":
    check_for_views()