# Vercel Deployment Guide

This guide covers deploying AutifyME to Vercel for serverless deployment.

## 📋 Prerequisites

- Vercel account (free)
- GitHub repository
- Environment variables configured

## 🚀 Quick Setup

### 1. Install Vercel CLI

```bash
npm install -g vercel
```

### 2. Login to Vercel

```bash
vercel login
```

### 3. Link Your Project

```bash
cd your-project-directory
vercel link
```

Follow the prompts to:
- Create a new project or link existing
- Select your GitHub repository
- Configure project settings

### 4. Configure Environment Variables

```bash
# Required environment variables
vercel env add SUPABASE_URL
vercel env add SUPABASE_ANON_KEY
vercel env add WHATSAPP_PHONE_NUMBER_ID
vercel env add WHATSAPP_ACCESS_TOKEN
vercel env add WHATSAPP_WEBHOOK_VERIFY_TOKEN
vercel env add LANGCHAIN_API_KEY
vercel env add OPENAI_API_KEY
vercel env add DATABASE_URL
```

### 5. Deploy

```bash
vercel --prod
```

## ⚙️ Configuration Details

### vercel.json

The `vercel.json` file is configured for Python deployment:

```json
{
  "version": 2,
  "builds": [
    {
      "src": "agents/src/autifyme_agents/entrypoints/whatsapp_webhook.py",
      "use": "@vercel/python",
      "config": {
        "maxLambdaSize": "50mb"
      }
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "agents/src/autifyme_agents/entrypoints/whatsapp_webhook.py"
    }
  ],
  "functions": {
    "agents/src/autifyme_agents/entrypoints/whatsapp_webhook.py": {
      "maxDuration": 30
    }
  },
  "env": {
    "PYTHONPATH": "agents/src"
  }
}
```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SUPABASE_URL` | Supabase project URL | Yes |
| `SUPABASE_ANON_KEY` | Supabase anonymous key | Yes |
| `WHATSAPP_PHONE_NUMBER_ID` | WhatsApp Business API phone number ID | Yes |
| `WHATSAPP_ACCESS_TOKEN` | WhatsApp Business API access token | Yes |
| `WHATSAPP_WEBHOOK_VERIFY_TOKEN` | Webhook verification token | Yes |
| `LANGCHAIN_API_KEY` | LangSmith API key | Yes |
| `OPENAI_API_KEY` | OpenAI API key | Yes |
| `DATABASE_URL` | PostgreSQL connection string | Yes |

## 🔄 CI/CD Integration

The GitHub Actions workflow includes automatic Vercel deployment:

```yaml
deploy-to-vercel:
  needs: [test, lint]
  runs-on: ubuntu-latest
  if: github.ref == 'refs/heads/main' || github.ref == 'refs/heads/InitialDesign'

  steps:
    - uses: actions/checkout@v4
    - name: Setup Node.js
      uses: actions/setup-node@v4
      with:
        node-version: '18'
    - name: Install Vercel CLI
      run: npm install -g vercel
    - name: Pull Vercel Environment Information
      run: vercel pull --yes --environment=production --token=${{ secrets.VERCEL_TOKEN }}
    - name: Build Project Artifacts
      run: vercel build --prod --token=${{ secrets.VERCEL_TOKEN }}
    - name: Deploy Project Artifacts to Vercel
      run: vercel deploy --prebuilt --prod --token=${{ secrets.VERCEL_TOKEN }}
```

### Required GitHub Secret

Add `VERCEL_TOKEN` to your GitHub repository secrets:
- Get token from: https://vercel.com/account/tokens
- Add as: `VERCEL_TOKEN`

## ⚠️ Vercel Limitations

### Function Timeouts
- Serverless functions timeout after 30 seconds
- Long-running AI operations may fail
- Consider Railway for production workloads

### File Uploads
- Limited to 5MB per request
- No persistent file storage
- Use Supabase Storage for files

### Cold Starts
- First request after inactivity may be slow
- Subsequent requests are fast
- Not ideal for time-sensitive operations

## 🧪 Testing Vercel Deployment

### Health Check
```bash
curl https://your-app.vercel.app/health
```

### WhatsApp Webhook Test
```bash
curl -X GET "https://your-app.vercel-app/webhook?hub.verify_token=YOUR_VERIFY_TOKEN&hub.challenge=test&hub.mode=subscribe"
```

## 🔧 Troubleshooting

### Build Failures
- Check `PYTHONPATH` environment variable
- Ensure all dependencies are in `requirements.txt`
- Verify Python version compatibility

### Runtime Errors
- Check function logs in Vercel dashboard
- Verify environment variables are set
- Test locally with `vercel dev`

### Webhook Issues
- Verify webhook URL in WhatsApp Business API
- Check function timeout settings
- Ensure proper error handling

## 📊 Monitoring

- **Logs**: Available in Vercel dashboard
- **Metrics**: Function duration, cold starts, errors
- **Alerts**: Configure in Vercel dashboard

## 💡 Best Practices

1. **Use Railway for production** - better for long-running tasks
2. **Vercel for demos/testing** - quick deployment, generous free tier
3. **Monitor cold starts** - optimize for performance
4. **Keep functions lightweight** - split complex logic
5. **Use proper error handling** - timeouts are common
