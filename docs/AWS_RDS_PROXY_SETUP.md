# AWS RDS Proxy Setup for RivaAI

This document provides guidance for setting up AWS RDS Proxy for connection pooling to handle 1000+ concurrent calls.

## Overview

AWS RDS Proxy is a fully managed database proxy that makes applications more scalable, resilient, and secure. For RivaAI, it provides:

- **Connection pooling**: Efficiently manages database connections for 1000+ concurrent calls
- **Automatic failover**: Reduces failover time by up to 66%
- **IAM authentication**: Enhanced security without managing database credentials
- **Connection multiplexing**: Reduces database memory and CPU overhead

## Prerequisites

- AWS account with appropriate permissions
- RDS PostgreSQL instance (version 11.9 or higher for pgvector support)
- VPC with private subnets
- Security groups configured

## Setup Steps

### 1. Create RDS PostgreSQL Instance

```bash
# Using AWS CLI
aws rds create-db-instance \
    --db-instance-identifier rivaai-postgres \
    --db-instance-class db.r6g.xlarge \
    --engine postgres \
    --engine-version 15.4 \
    --master-username postgres \
    --master-user-password <secure-password> \
    --allocated-storage 100 \
    --storage-type gp3 \
    --vpc-security-group-ids sg-xxxxx \
    --db-subnet-group-name rivaai-db-subnet \
    --backup-retention-period 7 \
    --preferred-backup-window "03:00-04:00" \
    --preferred-maintenance-window "mon:04:00-mon:05:00" \
    --enable-performance-insights \
    --performance-insights-retention-period 7
```

### 2. Install pgvector Extension

Connect to your RDS instance and run:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 3. Create IAM Role for RDS Proxy

```bash
# Create trust policy
cat > rds-proxy-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "rds.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create IAM role
aws iam create-role \
    --role-name RivaAI-RDS-Proxy-Role \
    --assume-role-policy-document file://rds-proxy-trust-policy.json

# Attach policy for Secrets Manager access
aws iam attach-role-policy \
    --role-name RivaAI-RDS-Proxy-Role \
    --policy-arn arn:aws:iam::aws:policy/SecretsManagerReadWrite
```

### 4. Store Database Credentials in Secrets Manager

```bash
aws secretsmanager create-secret \
    --name rivaai/db/credentials \
    --description "RivaAI PostgreSQL credentials" \
    --secret-string '{
        "username": "postgres",
        "password": "<secure-password>",
        "engine": "postgres",
        "host": "rivaai-postgres.xxxxx.region.rds.amazonaws.com",
        "port": 5432,
        "dbname": "rivaai"
    }'
```

### 5. Create RDS Proxy

```bash
aws rds create-db-proxy \
    --db-proxy-name rivaai-proxy \
    --engine-family POSTGRESQL \
    --auth '{
        "AuthScheme": "SECRETS",
        "SecretArn": "arn:aws:secretsmanager:region:account:secret:rivaai/db/credentials",
        "IAMAuth": "DISABLED"
    }' \
    --role-arn arn:aws:iam::account:role/RivaAI-RDS-Proxy-Role \
    --vpc-subnet-ids subnet-xxxxx subnet-yyyyy \
    --require-tls true \
    --idle-client-timeout 1800
```

### 6. Register RDS Instance with Proxy

```bash
aws rds register-db-proxy-targets \
    --db-proxy-name rivaai-proxy \
    --db-instance-identifiers rivaai-postgres
```

### 7. Configure Connection Pooling Settings

```bash
aws rds modify-db-proxy \
    --db-proxy-name rivaai-proxy \
    --connection-pool-config '{
        "MaxConnectionsPercent": 100,
        "MaxIdleConnectionsPercent": 50,
        "ConnectionBorrowTimeout": 120,
        "SessionPinningFilters": ["EXCLUDE_VARIABLE_SETS"]
    }'
```

## Connection Pool Configuration

For 1000+ concurrent calls, configure the following:

### RDS Instance Settings

```sql
-- Increase max connections (requires instance restart)
ALTER SYSTEM SET max_connections = 1000;

-- Optimize connection handling
ALTER SYSTEM SET shared_buffers = '4GB';
ALTER SYSTEM SET effective_cache_size = '12GB';
ALTER SYSTEM SET maintenance_work_mem = '1GB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;
ALTER SYSTEM SET work_mem = '4MB';
ALTER SYSTEM SET min_wal_size = '1GB';
ALTER SYSTEM SET max_wal_size = '4GB';
```

### Application Configuration

Update `.env` file:

```bash
# Use RDS Proxy endpoint instead of direct RDS endpoint
DATABASE_URL=postgresql://postgres:<password>@rivaai-proxy.proxy-xxxxx.region.rds.amazonaws.com:5432/rivaai

# Connection pool settings
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
DATABASE_POOL_TIMEOUT=30
DATABASE_POOL_RECYCLE=3600
```

## Security Configuration

### Security Group Rules

**RDS Proxy Security Group (Inbound)**:
- Port 5432 from application security group
- Port 5432 from VPC CIDR (for internal access)

**RDS Instance Security Group (Inbound)**:
- Port 5432 from RDS Proxy security group only

### IAM Authentication (Optional)

For enhanced security, enable IAM authentication:

```bash
# Modify proxy to enable IAM auth
aws rds modify-db-proxy \
    --db-proxy-name rivaai-proxy \
    --auth '{
        "AuthScheme": "SECRETS",
        "SecretArn": "arn:aws:secretsmanager:region:account:secret:rivaai/db/credentials",
        "IAMAuth": "REQUIRED"
    }'

# Grant IAM user/role permission to connect
aws iam attach-user-policy \
    --user-name rivaai-app \
    --policy-arn arn:aws:iam::aws:policy/AmazonRDSDataFullAccess
```

## Monitoring and Optimization

### CloudWatch Metrics

Monitor these key metrics:

- `DatabaseConnections`: Current connections
- `ClientConnections`: Application connections to proxy
- `QueryDatabaseResponseLatency`: Query latency
- `MaxDatabaseConnectionsAllowed`: Connection limit

### Set Up Alarms

```bash
# High connection usage alarm
aws cloudwatch put-metric-alarm \
    --alarm-name rivaai-high-db-connections \
    --alarm-description "Alert when DB connections exceed 80%" \
    --metric-name DatabaseConnections \
    --namespace AWS/RDS \
    --statistic Average \
    --period 300 \
    --threshold 800 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 2

# High query latency alarm
aws cloudwatch put-metric-alarm \
    --alarm-name rivaai-high-query-latency \
    --alarm-description "Alert when query latency exceeds 100ms" \
    --metric-name QueryDatabaseResponseLatency \
    --namespace AWS/RDS \
    --statistic Average \
    --period 60 \
    --threshold 100 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 3
```

## Load Testing

Before production deployment, perform load testing:

```bash
# Install pgbench
sudo apt-get install postgresql-contrib

# Initialize test database
pgbench -i -s 50 rivaai

# Run load test with 1000 concurrent connections
pgbench -c 1000 -j 100 -T 300 -h rivaai-proxy.proxy-xxxxx.region.rds.amazonaws.com -U postgres rivaai
```

## Troubleshooting

### Connection Timeout Issues

If experiencing timeouts:

1. Increase `ConnectionBorrowTimeout` in proxy config
2. Increase `DATABASE_POOL_TIMEOUT` in application
3. Check security group rules
4. Verify RDS instance has sufficient capacity

### High Connection Count

If connections are exhausted:

1. Increase RDS instance `max_connections`
2. Optimize application connection pooling
3. Implement connection retry logic
4. Consider scaling RDS instance

### Slow Query Performance

If queries are slow:

1. Check pgvector index creation: `\d+ crops`
2. Analyze query plans: `EXPLAIN ANALYZE SELECT ...`
3. Update table statistics: `ANALYZE crops, chemicals, schemes;`
4. Consider increasing RDS instance size

## Cost Optimization

- Use Reserved Instances for RDS (up to 60% savings)
- Enable RDS Proxy only in production (not dev/staging)
- Use appropriate instance types (r6g for memory-intensive workloads)
- Set up automated backups with appropriate retention

## References

- [AWS RDS Proxy Documentation](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-proxy.html)
- [pgvector Extension](https://github.com/pgvector/pgvector)
- [PostgreSQL Connection Pooling Best Practices](https://www.postgresql.org/docs/current/runtime-config-connection.html)
