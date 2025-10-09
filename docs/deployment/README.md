# Deployment Guide

## 🚀 Quick Deploy Options

### Option 1: Railway (Recommended - Most Beginner Friendly)

**Free Tier:** 512MB RAM, 1GB storage, custom domain with HTTPS
**Pros:** Automatic HTTPS, GitHub integration, **no Docker required**, PostgreSQL included
**Cons:** Limited free resources

#### Steps:

1. **Connect Repository:**
   - Go to [Railway.app](https://railway.app) and sign up
   - Click "New Project" → "Deploy from GitHub repo"
   - Connect your AutifyME repository

2. **Configure Environment Variables:**
   ```bash
   SUPABASE_URL=your_supabase_url
   SUPABASE_ANON_KEY=your_supabase_anon_key
   DATABASE_URL=your_supabase_postgres_url
   WHATSAPP_PHONE_NUMBER_ID=your_whatsapp_phone_id
   WHATSAPP_ACCESS_TOKEN=your_whatsapp_token
   WHATSAPP_WEBHOOK_VERIFY_TOKEN=your_webhook_token
   LANGCHAIN_API_KEY=your_langsmith_key
   OPENAI_API_KEY=your_openai_key
   ```

3. **Set Custom Domain (Optional):**
   - Go to Settings → Domains
   - Add your domain (free HTTPS included)

### Option 2: Render (Great Alternative)

**Free Tier:** 750 hours/month, custom domain with HTTPS
**Pros:** Generous free tier, PostgreSQL available
**Cons:** No built-in database

#### Steps:

1. **Deploy Web Service:**
   - Go to [Render.com](https://render.com) and sign up
   - Click "New +" → "Web Service"
   - Connect your GitHub repo

2. **Configure Build & Deploy:**
   - **Build Command:** `pip install uv && uv pip install -r pyproject.toml`
   - **Start Command:** `uvicorn autifyme_agents.entrypoints.whatsapp_webhook:app --host 0.0.0.0 --port $PORT`

3. **Add PostgreSQL Database:**
   - Create a new PostgreSQL instance on Render
   - Copy the connection string to `DATABASE_URL`

### Option 3: Fly.io (Most Flexible)

**Free Tier:** 3 shared CPU, 256MB RAM, 1GB storage
**Pros:** Global deployment, custom domains
**Cons:** More complex setup

#### Steps:

1. **Install Fly CLI:**
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. **Initialize App:**
   ```bash
   fly launch
   fly secrets set SUPABASE_URL=your_value
   fly secrets set SUPABASE_ANON_KEY=your_value
   # ... set all required secrets
   ```

3. **Deploy:**
   ```bash
   fly deploy
   ```

## 🔒 Security Considerations

### Environment Variables (Critical)
- **Never commit secrets** to Git - use platform secret management
- **Rotate tokens regularly** - especially WhatsApp tokens
- **Use different tokens** for staging/production

### WhatsApp Webhook Security
- **HTTPS Required:** All platforms provide automatic HTTPS
- **Webhook Verification:** Implemented in `/webhook` GET endpoint
- **Idempotency:** Built-in duplicate message prevention

### Database Security
- **Use connection pooling** (Supabase handles this)
- **Enable RLS policies** in Supabase for data isolation
- **Regular backups** (enable in Supabase dashboard)

## 📊 Cost Comparison

| Platform | Free Tier | Paid Tier | HTTPS | Custom Domain |
|----------|-----------|-----------|-------|---------------|
| Railway | 512MB RAM | $5/month | ✅ | ✅ |
| Render | 750 hrs/mo | $7/month | ✅ | ✅ |
| Fly.io | 256MB RAM | $5/month | ✅ | ✅ |
| Heroku | 550 hrs/mo | $7/month | ✅ | ❌ Free |

## 🔍 Monitoring & Debugging

### Health Checks
- **Endpoint:** `GET /health`
- **Returns:** `{"status": "healthy", "service": "autifyme-webhook"}`

### Logs
- **Railway:** Dashboard → Logs tab
- **Render:** Dashboard → Logs tab
- **Fly.io:** `fly logs`

### LangSmith Monitoring
- All agent executions automatically traced
- Cost tracking per request
- Performance metrics dashboard

## 🚨 Troubleshooting

### Common Issues:

1. **Webhook not receiving messages:**
   - Verify HTTPS URL in WhatsApp Business API dashboard
   - Check webhook verification token matches

2. **Database connection errors:**
   - Verify DATABASE_URL format
   - Check Supabase project is active

3. **Out of memory:**
   - Upgrade to paid tier (512MB free is tight)
   - Optimize agent context window

4. **Slow response times:**
   - Check LangSmith for bottleneck identification
   - Consider agent caching middleware

## 🔄 CI/CD with GitHub Actions

The included `.github/workflows/ci-cd.yml` provides:

- **Automated testing** on every push/PR
- **Code quality checks** (linting, type checking)
- **Automated deployment** to Railway (no Docker needed)

### Required Secrets:
```bash
RAILWAY_TOKEN=your_railway_token
RAILWAY_SERVICE_ID=your_railway_service_id
```

## 📈 Scaling Considerations

### Vertical Scaling (Bigger instances):
- Railway: Upgrade to $5/month Hobby plan
- Render: Upgrade to $7/month Starter plan

### Horizontal Scaling (Multiple instances):
- Railway: Pro plan ($10/month) supports horizontal scaling
- Use load balancer for multiple webhook endpoints

### Database Scaling:
- Supabase free tier: 500MB database, 50MB file storage
- Upgrade path: $25/month Pro plan (2GB database, 100GB files)

## 🎯 Production Checklist

- [ ] HTTPS enabled and working
- [ ] Webhook verification successful
- [ ] Database connection established
- [ ] LangSmith tracing active
- [ ] Health check endpoint responding
- [ ] CI/CD pipeline passing
- [ ] Environment secrets configured
- [ ] Monitoring alerts set up
- [ ] Backup strategy in place
