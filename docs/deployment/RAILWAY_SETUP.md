# 🚂 Railway Deployment Guide

## Step-by-Step Railway Setup

### 1. Create Railway Account
1. Go to [Railway.app](https://railway.app)
2. Sign up with GitHub (recommended) or email
3. Verify your email

### 2. Create New Project
1. Click **"New Project"**
2. Select **"Deploy from GitHub repo"**
3. Connect your GitHub account
4. Select the **AutifyME** repository
5. Click **"Deploy"**

Railway will automatically detect the `railway.toml` and `Dockerfile` in your repo.

### 3. Configure Environment Variables

In Railway Dashboard → Your Project → Variables:

#### Required Environment Variables:
```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_supabase_anon_key
DATABASE_URL=postgresql://postgres:password@containers-us-west-1.railway.app:xxxx/railway
WHATSAPP_PHONE_NUMBER_ID=your_whatsapp_phone_number_id
WHATSAPP_ACCESS_TOKEN=your_whatsapp_access_token
WHATSAPP_WEBHOOK_VERIFY_TOKEN=your_webhook_verify_token
WHATSAPP_API_VERSION=v20.0
LANGCHAIN_API_KEY=your_langsmith_api_key
OPENAI_API_KEY=your_openai_api_key
AGENT_RECURSION_LIMIT=15
```

#### How to Get These Values:

**Supabase:**
1. Go to [Supabase Dashboard](https://supabase.com/dashboard)
2. Select your project → Settings → API
3. Copy `Project URL` → `SUPABASE_URL`
4. Copy `anon public` key → `SUPABASE_ANON_KEY`
5. Copy `Database password` for connection string

**WhatsApp Business API:**
1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Your App → WhatsApp → API Setup
3. Copy Phone Number ID, Access Token, Verify Token

**LangSmith & OpenAI:**
- Copy from your existing `.env` file

### 4. Set Up Custom Domain (Highly Recommended)

1. Go to Railway Dashboard → Your Project → Settings → Domains
2. Click "Add Domain"
3. Enter your domain (e.g., `api.autifyme.com` or `autifyme.com`)
4. Railway provides automatic HTTPS certificates
5. Update DNS records as instructed:

**For apex domain (autifyme.com):**
```
Type: CNAME
Name: @
Value: your-app-name.up.railway.app
```

**For subdomain (api.autifyme.com):**
```
Type: CNAME
Name: api
Value: your-app-name.up.railway.app
```

**Important:** Railway domains are **completely free** and include automatic HTTPS certificates. This is much better than using the default Railway subdomain for production.

### 5. Verify Deployment

1. **Check Health Endpoint:**
   ```
   GET https://your-app.railway.app/health
   ```
   Should return: `{"status": "healthy", "service": "autifyme-webhook"}`

2. **Check Logs:**
   - Railway Dashboard → Deployments → View Logs
   - Look for successful startup messages

3. **Test WhatsApp Webhook:**
   - Update WhatsApp Business API webhook URL to: `https://your-app.railway.app/webhook`
   - Send a test message to verify

## 🔧 Troubleshooting

### Common Issues:

**1. Build Fails:**
- Check Railway logs for specific errors
- Verify `Dockerfile` is in root directory
- Ensure `railway.toml` is correctly formatted

**2. Environment Variables Missing:**
- Railway Dashboard → Variables → Check all required vars are set
- Restart deployment after adding variables

**3. Health Check Fails:**
```bash
# Test locally first
curl https://your-app.railway.app/health
```

**4. Database Connection Issues:**
- Verify `DATABASE_URL` format
- Check Supabase project is active
- Ensure database allows connections from Railway IPs

**5. WhatsApp Webhook Not Working:**
- Verify HTTPS URL in WhatsApp Business API dashboard
- Check webhook verification token matches
- Test webhook verification: `GET /webhook?hub.verify_token=YOUR_TOKEN`

### Railway-Specific Tips:

- **Automatic Scaling:** Railway auto-scales based on traffic
- **Logs:** Real-time logs in dashboard
- **Metrics:** CPU, Memory, Network usage
- **Rollback:** Easy deployment rollback in dashboard
- **Environment Isolation:** Separate staging/production environments

## 🚀 Post-Deployment Steps

### 1. Set Up Monitoring
- Railway provides basic metrics
- LangSmith for agent performance monitoring
- Set up alerts for failures

### 2. Configure Backups
- Railway handles infrastructure backups
- Configure Supabase database backups
- Export important data regularly

### 3. Update CI/CD (Optional)
If you want GitHub Actions to trigger Railway deploys:

1. Get Railway Token:
   - Railway Dashboard → Account Settings → Tokens
   - Generate new token

2. Add to GitHub Secrets:
   - Repository → Settings → Secrets and variables → Actions
   - Add `RAILWAY_TOKEN`

3. The CI/CD pipeline will then trigger Railway deploys

### 4. Production Checklist
- [ ] HTTPS working
- [ ] Health checks passing
- [ ] WhatsApp webhook verified
- [ ] Database connected
- [ ] All environment variables set
- [ ] Logs showing successful startup
- [ ] Test message sent successfully

## 💰 Cost Optimization

**Railway Free Tier:**
- 512MB RAM
- 1GB storage
- 1GB outbound bandwidth
- Custom domains included

**When to Upgrade:**
- Consistent memory usage > 400MB
- High traffic periods
- Need for horizontal scaling

**Upgrade Path:** $5/month Hobby plan (8GB RAM, more resources)

## 🔗 Useful Links

- [Railway Documentation](https://docs.railway.app/)
- [Railway Discord](https://discord.gg/railway)
- [AutifyME Deployment Docs](../README.md)
