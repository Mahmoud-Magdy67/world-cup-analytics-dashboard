import os
import sys
import pandas as pd
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

# Test AWS credentials directly
def test_aws_credentials():
    """Test if AWS credentials are properly configured"""
    print("Testing AWS credentials...")
    
    try:
        # Test if credentials are available
        aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        
        if not aws_access_key_id or not aws_secret_access_key:
            print("❌ AWS credentials not found in environment variables")
            return False
            
        print(f"✅ AWS Access Key ID found: {aws_access_key_id[:5]}...{aws_access_key_id[-5:]}")
        
        # Test Athena client initialization
        client = boto3.client(
            'athena',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        )
        
        # Test basic connectivity
        response = client.list_work_groups()
        print("✅ AWS Athena client initialized successfully")
        print(f"Available workgroups: {[wg['Name'] for wg in response.get('WorkGroups', [])[:5]]}")
        
        return True
        
    except Exception as e:
        print(f"❌ AWS connection error: {e}")
        return False

def test_athena_query():
    """Test executing a simple Athena query"""
    print("\nTesting Athena query execution...")
    
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    
    if not aws_access_key_id or not aws_secret_access_key:
        print("❌ Cannot test query without AWS credentials")
        return False
    
    try:
        client = boto3.client(
            'athena',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        )
        
        # Simple test query - list databases
        response = client.list_databases(
            CatalogName='AwsDataCatalog'
        )
        
        databases = [db['Name'] for db in response.get('DatabaseList', [])]
        print(f"✅ Athena databases found: {databases}")
        
        # Check if our expected database is present
        expected_db = "worldcup_2026"
        if expected_db in databases:
            print(f"✅ Database '{expected_db}' found")
        else:
            print(f"⚠️ Database '{expected_db}' not found. Available databases: {databases}")
            
        return True
        
    except Exception as e:
        print(f"❌ Athena query test failed: {e}")
        return False

if __name__ == "__main__":
    print("=== AWS Athena Connection Test ===")
    
    credential_test = test_aws_credentials()
    query_test = test_athena_query()
    
    if credential_test and query_test:
        print("\n🎉 All tests passed! Athena connection is working correctly.")
    else:
        print("\n❌ Some tests failed. Please check your AWS configuration.")