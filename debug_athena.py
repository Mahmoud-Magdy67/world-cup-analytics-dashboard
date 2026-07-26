import os
import boto3

def debug_athena_tables():
    """Debug Athena table listing issue"""
    print("Debugging Athena table listing...")
    
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
        
        # Simple test - list databases first
        print("1. Listing databases:")
        response = client.list_databases(CatalogName='AwsDataCatalog')
        for db in response.get('DatabaseList', []):
            print(f"   - {db['Name']}")
        
        # Check the specific database exists
        database_name = os.getenv("ATHENA_DATABASE", "worldcup_2026")
        print(f"\n2. Checking if database '{database_name}' exists...")
        
        db_exists = any(db['Name'] == database_name for db in response.get('DatabaseList', []))
        if db_exists:
            print(f"   ✅ Database '{database_name}' exists")
        else:
            print(f"   ❌ Database '{database_name}' not found")
            return
        
        # Try a simple query to see if we can get any results
        print(f"\n3. Running simple query test...")
        query = "SELECT 1 as test_column"
        
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
        print(f"   Query Execution ID: {query_execution_id}")
        
        # Wait for query to complete
        import time
        max_wait = 30
        waited = 0
        while waited < max_wait:
            response = client.get_query_execution(QueryExecutionId=query_execution_id)
            status = response['QueryExecution']['Status']['State']
            print(f"   Query status: {status}")
            
            if status in ['SUCCEEDED']:
                print("   ✅ Query succeeded")
                break
            elif status in ['FAILED', 'CANCELLED']:
                reason = response['QueryExecution']['Status'].get('StateChangeReason', 'Unknown error')
                print(f"   ❌ Query failed: {reason}")
                return
            time.sleep(2)
            waited += 2
        else:
            print("   ❌ Query timed out")
            return
        
        # Get results
        print("4. Getting query results...")
        results = client.get_query_results(QueryExecutionId=query_execution_id)
        print(f"   Results structure: {list(results.keys())}")
        
        if 'ResultSet' in results:
            print(f"   ResultSet keys: {list(results['ResultSet'].keys())}")
            if 'Rows' in results['ResultSet']:
                print(f"   Number of rows: {len(results['ResultSet']['Rows'])}")
                for i, row in enumerate(results['ResultSet']['Rows'][:3]):  # Show first 3 rows
                    print(f"   Row {i}: {row}")
                    if 'Data' in row:
                        print(f"     Data: {row['Data']}")
        
    except Exception as e:
        print(f"❌ Error in debug: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_athena_tables()