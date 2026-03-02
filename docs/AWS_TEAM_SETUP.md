# AWS Team Access Setup Guide

## Quick Setup (5 minutes per person)

### Option 1: IAM Users (Recommended for 2-day sprint)

**Step 1: Create IAM Users**

1. Go to AWS Console → IAM → Users
2. Click "Add users"
3. Create 3 users:
   - `rivaai-person2` (Knowledge Base)
   - `rivaai-person3` (LLM)
   - `rivaai-person4` (Speech)

4. Access type: Select both
   - ✅ Programmatic access (for CLI/SDK)
   - ✅ AWS Management Console access

5. Set console password:
   - Choose "Custom password"
   - ✅ Require password reset (they'll change it on first login)

**Step 2: Attach Permissions**

For the 2-day sprint, use these pre-built policies:

**Person 2 (Knowledge Base):**
- `AmazonRDSFullAccess` - For PostgreSQL
- `AmazonElastiCacheFullAccess` - For Redis
- `AmazonVPCFullAccess` - For networking

**Person 3 (LLM):**
- `AmazonBedrockFullAccess` - For Claude/Titan
- `AmazonS3ReadOnlyAccess` - For reading data

**Person 4 (Speech & Telephony):**
- `AmazonTranscribeFullAccess` - For STT
- `AmazonPollyFullAccess` - For TTS
- `AmazonConnectFullAccess` - For telephony

**All Team Members:**
- `IAMReadOnlyAccess` - To see IAM resources
- `CloudWatchLogsReadOnlyAccess` - To view logs

**Step 3: Download Credentials**

After creating each user:
1. Download the CSV with:
   - Access Key ID
   - Secret Access Key
   - Console login URL
2. Send securely to each team member (Slack DM, encrypted email)

**Step 4: Team Members Configure AWS CLI**

Each person runs:
```bash
aws configure

# Enter when prompted:
AWS Access Key ID: [from CSV]
AWS Secret Access Key: [from CSV]
Default region: us-east-1
Default output format: json
```

---

### Option 2: IAM Identity Center (Better for long-term, but slower setup)

**Only use this if you have time (30+ minutes setup)**

1. Go to IAM Identity Center
2. Enable IAM Identity Center
3. Add users with email addresses
4. Create permission sets
5. Assign users to permission sets

**Skip this for 2-day sprint - use Option 1**

---

## Quick Permission Policy (Copy-Paste)

If you want custom policies instead of AWS managed ones:

### Create Custom Policy for RivaAI Team

1. Go to IAM → Policies → Create Policy
2. Use JSON editor:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:*",
        "rds:*",
        "elasticache:*",
        "transcribe:*",
        "polly:*",
        "connect:*",
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket",
        "logs:*",
        "cloudwatch:*",
        "ec2:Describe*",
        "vpc:Describe*"
      ],
      "Resource": "*"
    }
  ]
}
```

3. Name it: `RivaAI-Developer-Access`
4. Attach to all 3 users

---

## Security Best Practices (For 2-day sprint)

### ✅ DO:
- Use separate IAM users (not root account)
- Enable MFA on your root account
- Set password policy (min 8 chars)
- Use specific policies per person
- Rotate credentials after sprint

### ❌ DON'T:
- Share your root account credentials
- Use same credentials for all team members
- Commit credentials to Git
- Share credentials in plain text

---

## Quick Access URLs

After setup, share these with your team:

**Console Login:**
```
https://[YOUR-ACCOUNT-ID].signin.aws.amazon.com/console
```

**Services They'll Use:**

**Person 2:**
- RDS: https://console.aws.amazon.com/rds
- ElastiCache: https://console.aws.amazon.com/elasticache

**Person 3:**
- Bedrock: https://console.aws.amazon.com/bedrock
- S3: https://console.aws.amazon.com/s3

**Person 4:**
- Transcribe: https://console.aws.amazon.com/transcribe
- Polly: https://console.aws.amazon.com/polly
- Connect: https://console.aws.amazon.com/connect

**Everyone:**
- CloudWatch Logs: https://console.aws.amazon.com/cloudwatch

---

## Credentials Management

### For Local Development

Each person creates `.env` file:

```bash
# AWS Credentials
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1

# Service-specific (you'll share these)
EXOTEL_API_KEY=...
EXOTEL_API_TOKEN=...
```

### For Shared Resources

Create a shared `.env.shared` file (don't commit to Git):

```bash
# Shared Resources
DATABASE_URL=postgresql://user:pass@rivaai-dev.xxx.rds.amazonaws.com:5432/rivaai
REDIS_URL=redis://rivaai-dev.xxx.cache.amazonaws.com:6379/0

# Telephony (Person 4 manages)
EXOTEL_SID=...
EXOTEL_PHONE_NUMBER=+91...
```

---

## Cost Control (Important!)

### Set Billing Alerts

1. Go to Billing → Budgets
2. Create budget:
   - Name: "RivaAI-2Day-Sprint"
   - Amount: $100 (or your limit)
   - Alert at: 80% ($80)

3. Add email alerts for all team members

### Monitor Costs

Check daily:
```bash
aws ce get-cost-and-usage \
  --time-period Start=2026-03-03,End=2026-03-05 \
  --granularity DAILY \
  --metrics BlendedCost
```

---

## Troubleshooting

### "Access Denied" Errors

**Person 2 can't create RDS:**
- Add `AmazonRDSFullAccess` policy

**Person 3 can't use Bedrock:**
- Check Bedrock is enabled in your region
- Add `AmazonBedrockFullAccess` policy

**Person 4 can't use Transcribe:**
- Add `AmazonTranscribeFullAccess` policy

### "Invalid Credentials"

```bash
# Test credentials
aws sts get-caller-identity

# Should return:
{
  "UserId": "AIDAI...",
  "Account": "123456789012",
  "Arn": "arn:aws:iam::123456789012:user/rivaai-person2"
}
```

---

## After 2-Day Sprint

### Cleanup (Important!)

1. **Rotate credentials:**
   ```bash
   aws iam create-access-key --user-name rivaai-person2
   aws iam delete-access-key --user-name rivaai-person2 --access-key-id OLD_KEY
   ```

2. **Review permissions:**
   - Remove unnecessary policies
   - Add more restrictive policies

3. **Delete unused resources:**
   - Stop RDS instances
   - Delete ElastiCache clusters
   - Remove test data

---

## Quick Reference Card (Print & Share)

```
┌─────────────────────────────────────────┐
│ RivaAI AWS Access                       │
├─────────────────────────────────────────┤
│ Console: https://[ACCOUNT].signin...    │
│ Region: us-east-1                       │
│                                         │
│ Your Username: rivaai-person[2/3/4]    │
│ Password: [provided separately]         │
│                                         │
│ AWS CLI Setup:                          │
│   aws configure                         │
│   [enter your access key]               │
│                                         │
│ Help: #war-room Slack channel           │
└─────────────────────────────────────────┘
```

---

## Estimated Setup Time

- Create 3 IAM users: 5 minutes
- Attach policies: 3 minutes
- Download & share credentials: 2 minutes
- Team members configure CLI: 5 minutes each

**Total: ~25 minutes to get everyone working**

Start with this immediately so your team can begin Day 1 tasks!
