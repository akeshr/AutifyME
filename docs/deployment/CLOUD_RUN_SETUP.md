# Google Cloud Run Deployment Guide

**Date:** 2025-11-26
**Status:** Production Ready

Google Cloud Run is the recommended deployment platform for AutifyME, offering serverless scaling, integrated secret management, and native GCP ecosystem integration.

---

## Why Cloud Run?

| Feature | Cloud Run | Vercel | Railway |
|---------|-----------|--------|---------|
| Execution timeout | 60 min | 30 sec (Pro) | 5 min |
| Memory | Up to 32GB | 3GB | 8GB |
| Secret Manager | Native | Env vars | Env vars |
| VPC connectivity | Yes | No | No |
| Pricing model | Per-request | Per-seat | Per-usage |
| Cold start | ~1-2s | ~500ms | Always warm |

**Best for:** Production workloads with long-running agent executions.

---

## Prerequisites

1. **GCP Account** with billing enabled
2. **gcloud CLI** installed and authenticated
3. **Docker** installed (for local testing)
4. **Secrets** ready (see [.env.example](../../.env.example))

```bash
# Install gcloud CLI
# https://cloud.google.com/sdk/docs/install

# Authenticate
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

---

## Quick Deploy (Manual)

### Step 1: Create Secrets in Secret Manager

```bash
# Required secrets
gcloud secrets create SUPABASE_URL --replication-policy="automatic"
echo -n "https://your-project.supabase.co" | gcloud secrets versions add SUPABASE_URL --data-file=-

gcloud secrets create SUPABASE_ANON_KEY --replication-policy="automatic"
echo -n "your_anon_key" | gcloud secrets versions add SUPABASE_ANON_KEY --data-file=-

gcloud secrets create DATABASE_URL --replication-policy="automatic"
echo -n "postgresql://..." | gcloud secrets versions add DATABASE_URL --data-file=-

gcloud secrets create OPENAI_API_KEY --replication-policy="automatic"
echo -n "sk-..." | gcloud secrets versions add OPENAI_API_KEY --data-file=-

gcloud secrets create GOOGLE_API_KEY --replication-policy="automatic"
echo -n "your_google_api_key" | gcloud secrets versions add GOOGLE_API_KEY --data-file=-

gcloud secrets create WHATSAPP_PHONE_NUMBER_ID --replication-policy="automatic"
echo -n "your_phone_id" | gcloud secrets versions add WHATSAPP_PHONE_NUMBER_ID --data-file=-

gcloud secrets create WHATSAPP_BUSINESS_ACCOUNT_ID --replication-policy="automatic"
echo -n "your_business_id" | gcloud secrets versions add WHATSAPP_BUSINESS_ACCOUNT_ID --data-file=-

gcloud secrets create WHATSAPP_ACCESS_TOKEN --replication-policy="automatic"
echo -n "your_access_token" | gcloud secrets versions add WHATSAPP_ACCESS_TOKEN --data-file=-

gcloud secrets create WHATSAPP_WEBHOOK_VERIFY_TOKEN --replication-policy="automatic"
echo -n "your_verify_token" | gcloud secrets versions add WHATSAPP_WEBHOOK_VERIFY_TOKEN --data-file=-

gcloud secrets create LANGCHAIN_API_KEY --replication-policy="automatic"
echo -n "lsv2_pt_..." | gcloud secrets versions add LANGCHAIN_API_KEY --data-file=-

gcloud secrets create TAVILY_API_KEY --replication-policy="automatic"
echo -n "tvly-..." | gcloud secrets versions add TAVILY_API_KEY --data-file=-
```

### Step 2: Build and Push Image

```bash
# Enable required APIs
gcloud services enable cloudbuild.googleapis.com run.googleapis.com secretmanager.googleapis.com

# Build and push (from project root)
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/autifyme-webhook

# Or use Docker locally
docker build -t gcr.io/YOUR_PROJECT_ID/autifyme-webhook .
docker push gcr.io/YOUR_PROJECT_ID/autifyme-webhook
```

### Step 3: Deploy to Cloud Run

```bash
gcloud run deploy autifyme-webhook \
  --image gcr.io/YOUR_PROJECT_ID/autifyme-webhook \
  --region asia-south1 \
  --platform managed \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 10 \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --concurrency 80 \
  --set-secrets "SUPABASE_URL=SUPABASE_URL:latest,SUPABASE_ANON_KEY=SUPABASE_ANON_KEY:latest,DATABASE_URL=DATABASE_URL:latest,WHATSAPP_PHONE_NUMBER_ID=WHATSAPP_PHONE_NUMBER_ID:latest,WHATSAPP_BUSINESS_ACCOUNT_ID=WHATSAPP_BUSINESS_ACCOUNT_ID:latest,WHATSAPP_ACCESS_TOKEN=WHATSAPP_ACCESS_TOKEN:latest,WHATSAPP_WEBHOOK_VERIFY_TOKEN=WHATSAPP_WEBHOOK_VERIFY_TOKEN:latest,OPENAI_API_KEY=OPENAI_API_KEY:latest,GOOGLE_API_KEY=GOOGLE_API_KEY:latest,LANGCHAIN_API_KEY=LANGCHAIN_API_KEY:latest,TAVILY_API_KEY=TAVILY_API_KEY:latest" \
  --set-env-vars "LANGCHAIN_TRACING_V2=true,LANGCHAIN_ENDPOINT=https://api.smith.langchain.com,LANGCHAIN_PROJECT=autifyme-prod,WHATSAPP_API_VERSION=v23.0,AGENT_RECURSION_LIMIT=50"
```

### Step 4: Get Service URL

```bash
gcloud run services describe autifyme-webhook --region asia-south1 --format="value(status.url)"
```

---

## CI/CD with Cloud Build (Recommended)

The repository includes [cloudbuild.yaml](../../cloudbuild.yaml) for automated deployments.

### Setup Cloud Build Trigger

1. **Connect Repository:**
   ```bash
   # Go to Cloud Console > Cloud Build > Triggers
   # Or use:
   gcloud source repos create autifyme
   git remote add google https://source.developers.google.com/p/YOUR_PROJECT_ID/r/autifyme
   git push google main
   ```

2. **Create Trigger:**
   ```bash
   gcloud builds triggers create github \
     --repo-name=AutifyME \
     --repo-owner=YOUR_GITHUB_USERNAME \
     --branch-pattern="^main$" \
     --build-config=cloudbuild.yaml \
     --substitutions=_SERVICE_NAME=autifyme-webhook,_REGION=asia-south1
   ```

3. **Grant Permissions:**
   ```bash
   PROJECT_NUMBER=$(gcloud projects describe YOUR_PROJECT_ID --format="value(projectNumber)")

   # Cloud Build service account needs Secret Manager access
   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
     --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
     --role="roles/secretmanager.secretAccessor"

   # Cloud Build needs Cloud Run deploy permissions
   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
     --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
     --role="roles/run.admin"

   # Cloud Build needs to act as Cloud Run service account
   gcloud iam service-accounts add-iam-policy-binding \
     ${PROJECT_NUMBER}-compute@developer.gserviceaccount.com \
     --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
     --role="roles/iam.serviceAccountUser"
   ```

---

## Local Development with Docker

```bash
# Build locally
docker build -t autifyme-webhook .

# Run with local .env file
docker run -p 8080:8080 --env-file .env autifyme-webhook

# Test health endpoint
curl http://localhost:8080/health
```

---

## WhatsApp Webhook Configuration

After deployment, configure the webhook URL in Meta Business Suite:

1. Go to [Meta for Developers](https://developers.facebook.com)
2. Select your app > WhatsApp > Configuration
3. Set **Callback URL:** `https://YOUR_SERVICE_URL/webhook`
4. Set **Verify token:** Same as `WHATSAPP_WEBHOOK_VERIFY_TOKEN`
5. Subscribe to: `messages`, `message_deliveries`, `message_reads`

---

## Monitoring

### Cloud Run Console
- **Logs:** Cloud Console > Cloud Run > autifyme-webhook > Logs
- **Metrics:** CPU, Memory, Request count, Latency

### LangSmith
- All agent executions traced automatically
- Set `LANGCHAIN_PROJECT=autifyme-prod` for production traces

### Cloud Logging Queries

```sql
-- Recent errors
resource.type="cloud_run_revision"
resource.labels.service_name="autifyme-webhook"
severity>=ERROR

-- Webhook requests
resource.type="cloud_run_revision"
jsonPayload.message="Processing WhatsApp message"

-- Workflow completions
resource.type="cloud_run_revision"
jsonPayload.message="Background workflow processing completed"
```

---

## Cost Optimization

### Recommended Settings

| Setting | Development | Production |
|---------|-------------|------------|
| Min instances | 0 | 1 |
| Max instances | 2 | 10 |
| Memory | 512Mi | 1Gi |
| CPU | 1 | 1 |
| Concurrency | 80 | 80 |
| Timeout | 300s | 300s |

### Cost Estimate (asia-south1)

- **Always Free:** 2M requests/month, 360K GB-seconds, 180K vCPU-seconds
- **Beyond free tier:** ~$0.00002400 per request + compute

For typical usage (1000 messages/day):
- **Estimated cost:** $5-15/month

---

## Troubleshooting

### Container fails to start

```bash
# Check logs
gcloud run services logs read autifyme-webhook --region asia-south1 --limit 50

# Common issues:
# - Missing secrets: Verify all secrets exist in Secret Manager
# - Import errors: Check PYTHONPATH includes source directory
```

### Webhook verification fails

```bash
# Test verification locally
curl "https://YOUR_URL/webhook?hub.mode=subscribe&hub.challenge=test&hub.verify_token=YOUR_TOKEN"

# Should return: test
```

### Database connection timeout

- Ensure `DATABASE_URL` uses connection pooler (port 6543 for Supabase)
- Cloud Run default timeout is 300s; increase if needed
- Check VPC connector if using private networking

### Cold start latency

- Set `min-instances=1` for always-warm production
- Use Cloud Run CPU boost: `--cpu-boost`
- Pre-warm with scheduled Cloud Scheduler pings

---

## Security Best Practices

1. **Use Secret Manager** - Never store secrets as env vars in code
2. **Limit IAM** - Use least-privilege service account
3. **Enable Cloud Armor** - DDoS protection for production
4. **VPC Service Controls** - For enterprise security requirements
5. **Binary Authorization** - Enforce signed images only

---

## Related Documentation

- [Custom Domain Setup](./CUSTOM_DOMAIN_GUIDE.md)
- [Database Maintenance](./DATABASE_MAINTENANCE.md)
- [LangSmith Setup](./LANGSMITH_SETUP.md)
