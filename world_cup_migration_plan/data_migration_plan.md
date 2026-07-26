# World Cup Analytics Dashboard: BigQuery to AWS Athena Migration Plan

## Executive Summary

This document outlines a comprehensive plan to migrate the World Cup Analytics Dashboard data infrastructure from Google BigQuery to AWS Athena. The migration will involve exporting data from BigQuery to Amazon S3 in Parquet format and setting up Athena tables for querying the data.

## Migration Objectives

1. Transfer all necessary World Cup analytics data from BigQuery to AWS S3
2. Set up AWS Athena for querying the migrated data
3. Maintain compatibility with existing application code
4. Ensure data integrity throughout the migration process
5. Minimize downtime during the transition
6. Optimize cost and performance in the new environment

## Prerequisites

### GCP Requirements
- GCP Service Account with BigQuery read permissions
- BigQuery datasets containing World Cup analytics data
- Access to export approximately 170-255 tables (based on reference implementation)

### AWS Requirements
- AWS account with S3 write permissions
- AWS account with Athena query permissions
- S3 bucket for storing Parquet files
- S3 bucket for Athena query results
- Appropriate IAM roles and policies

## Migration Phases

### Phase 1: Assessment and Planning

#### 1.1 Dataset Inventory
- Catalog all BigQuery datasets related to World Cup analytics
- Document table schemas, sizes, and dependencies
- Identify critical tables that need to be migrated first
- Determine which tables are actually used by the application (reference shows 170 of 255 tables were needed)

#### 1.2 Infrastructure Setup
- Create dedicated S3 bucket for World Cup data
- Create S3 bucket for Athena query results
- Set up IAM roles and policies for data access
- Configure AWS CLI with appropriate credentials

#### 1.3 Environment Preparation
- Set up development environment with required tools:
  - Python 3.7+
  - Google Cloud SDK
  - AWS CLI
  - Required Python packages: `google-cloud-bigquery`, `boto3`, `pandas`, `pyarrow`

### Phase 2: Data Migration

#### 2.1 Export Strategy
Based on lessons learned from the reference implementation:

##### Table Prioritization
- Identify critical tables (dashboards, key metrics)
- Group tables by dependency relationships
- Plan for batch processing to optimize throughput

##### Batch Processing Plan
- Small tables (<10MB): Initial testing group
- Medium tables (10MB-1GB): Primary migration batch
- Large tables (>1GB): Special handling with pagination

##### Best Practices Implementation
- Use batch sizes of 10-50 tables based on testing
- Implement exponential backoff for retries (3-5 retries)
- Add delays between batches (1-2 seconds) to avoid rate limiting
- Use Parquet format for efficient storage and querying
- Validate data integrity by comparing row counts

#### 2.2 Export Execution

##### Export Script Implementation
Using a modified version of the template script:

1. Set up authentication for both GCP and AWS
2. Initialize BigQuery and S3 clients
3. Process tables in batches with error handling
4. Implement retry mechanisms with exponential backoff
5. Monitor progress with detailed logging

##### Large Table Handling
For tables with >100K rows:
- Use pagination with OFFSET/LIMIT (page size 10K-50K rows)
- Monitor memory usage during export
- Implement garbage collection between chunks
- Process data in manageable chunks to prevent memory overflow

##### Progress Monitoring
- Log completed/remaining table counts
- Track average export time per table
- Monitor error rates and retry counts
- Generate progress reports during long-running operations

### Phase 3: Athena Configuration

#### 3.1 Database Creation
- Create Athena database for World Cup analytics
- Define appropriate location for data in S3

#### 3.2 Table Schema Mapping
- Map BigQuery data types to Athena-compatible types:
  - BigQuery TIMESTAMP → Athena TIMESTAMP
  - BigQuery STRING → Athena VARCHAR
  - BigQuery INTEGER → Athena INTEGER
  - BigQuery FLOAT → Athena DOUBLE
  - BigQuery BOOLEAN → Athena BOOLEAN

#### 3.3 External Table Creation
- Create external tables in Athena pointing to S3 Parquet files
- Define partitioning strategy if applicable
- Set appropriate table properties for performance

### Phase 4: Testing and Validation

#### 4.1 Data Integrity Validation
- Compare row counts between BigQuery source and Athena tables
- Sample data validation for critical tables
- Schema validation to ensure consistency
- Checksum verification for key tables

#### 4.2 Query Validation
- Execute sample queries from the application against Athena
- Verify query results match BigQuery outputs
- Performance benchmarking of equivalent queries
- Validate dashboard functionality with Athena backend

#### 4.3 Application Testing
- Update application configuration to use Athena
- Test all dashboard features with migrated data
- Performance testing under expected load conditions
- User acceptance testing of key dashboard features

### Phase 5: Cutover and Deployment

#### 5.1 Application Modifications
- Update environment variables:
  - Replace GCP-specific variables with AWS equivalents:
    - `GCP_SERVICE_ACCOUNT_KEY` → `AWS_ACCESS_KEY_ID`
    - `GCP_PROJECT_ID` → `AWS_SECRET_ACCESS_KEY`
    - Add new variables: `AWS_REGION`, `ATHENA_DATABASE`, `ATHENA_OUTPUT_BUCKET`
- Update data layer imports from `data.bigquery*` to `data.athena*`
- Modify SQL queries to use Athena syntax (double quotes instead of backticks)
- Add AWS SDK dependencies and remove Google Cloud dependencies

#### 5.2 Gradual Rollout
- Implement feature flag for database backend
- Start with non-critical dashboards
- Monitor performance and error rates
- Gradually increase traffic to Athena backend

#### 5.3 Monitoring and Observability
- Set up CloudWatch metrics for Athena queries
- Monitor S3 access patterns
- Implement alerting for query performance degradation
- Track cost implications of the new architecture

## Technical Implementation Details

### Authentication Setup

#### GCP Authentication
```bash
# Set GCP credentials
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
```

#### AWS Authentication
```bash
# Configure AWS credentials in ~/.aws/credentials
[default]
aws_access_key_id = YOUR_ACCESS_KEY_ID
aws_secret_access_key = YOUR_SECRET_ACCESS_KEY
region = us-east-1
```

### Required Dependencies

```bash
pip install google-cloud-bigquery pandas pyarrow boto3
```

### S3 Path Structure
```
s3://world-cup-analytics-data/input/table_name.parquet     # Main data files
s3://world-cup-analytics-query-results/                   # Athena query results
```

### Batch Processing Approach
1. Start with small batches (10-20 tables) for testing
2. Increase to medium batches (50 tables) once stability is confirmed
3. Monitor resource utilization to prevent bottlenecks
4. Maintain consistent timing by adding delays between batches

### Error Handling and Recovery
Implement the retry mechanism pattern:
```python
def export_with_retry(table_name, max_retries=3):
    """Export table with exponential backoff retry"""
    for attempt in range(max_retries):
        try:
            export_table(table_name)
            return True
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            # Exponential backoff
            delay = (2 ** attempt) + random.uniform(0, 1)
            time.sleep(delay)
    return False
```

## Timeline and Milestones

### Week 1: Assessment and Setup
- Complete dataset inventory
- Set up AWS infrastructure
- Prepare development environment
- Create migration scripts

### Week 2: Pilot Migration
- Identify and migrate pilot dataset (10-15 tables)
- Validate data integrity and query compatibility
- Refine migration process based on findings

### Week 3: Full Data Migration
- Execute batch migration of remaining tables
- Monitor progress and address any issues
- Complete data integrity validation

### Week 4: Athena Configuration and Testing
- Create Athena database and tables
- Perform comprehensive query validation
- Conduct application integration testing

### Week 5: Deployment and Monitoring
- Implement gradual rollout plan
- Monitor performance and error rates
- Complete user acceptance testing

## Risk Mitigation

### Potential Risks and Mitigation Strategies

1. **Data Loss During Migration**
   - Mitigation: Maintain BigQuery data until full validation is complete
   - Backup strategy: Use BigQuery table snapshots

2. **Performance Degradation**
   - Mitigation: Performance testing in staging environment
   - Optimization: Review and tune Athena queries

3. **Authentication Issues**
   - Mitigation: Thorough credential testing
   - Fallback plan: Maintain ability to roll back to BigQuery

4. **Schema Compatibility Issues**
   - Mitigation: Comprehensive schema mapping and validation
   - Testing: Validate all query patterns used by the application

5. **Cost Overruns**
   - Mitigation: Monitor S3 storage and Athena query costs
   - Optimization: Review query patterns and data organization

## Cost Considerations

### AWS Services Costs
1. **Amazon S3 Storage**
   - Standard storage for Parquet files
   - Request charges for data access

2. **Amazon Athena**
   - Per-query pricing based on data scanned
   - Optimization through efficient data organization and partitioning

3. **AWS Data Transfer**
   - Consider costs for cross-region data transfer if needed

### Cost Optimization Strategies
1. Use appropriate S3 storage classes (Standard for frequently accessed data)
2. Implement data partitioning to reduce query costs
3. Compress data using Parquet format for reduced storage and query costs
4. Schedule exports during off-peak hours if possible

## Success Criteria

1. All required World Cup analytics data successfully migrated to S3
2. Athena tables created and validated with correct schemas
3. Application functionality fully operational with Athena backend
4. Data integrity verified (row counts and sample data validation)
5. Query performance comparable to or better than BigQuery
6. Deployment completed with minimal downtime
7. Cost savings achieved compared to BigQuery (if that was an objective)

## Rollback Plan

In case of critical issues post-migration:

1. Revert application configuration to use BigQuery backend
2. Monitor for any residual issues
3. Address root causes of failure
4. Plan for re-execution of migration with improvements

## Conclusion

This migration plan provides a structured approach to moving the World Cup Analytics Dashboard from BigQuery to AWS Athena. By following the phased approach with thorough testing and validation at each stage, we can minimize risks and ensure a successful migration with minimal impact to users.

The implementation leverages lessons learned from previous migrations, adopting best practices for batch processing, error handling, and performance optimization. Regular monitoring and validation throughout the process will help ensure data integrity and maintain application functionality.