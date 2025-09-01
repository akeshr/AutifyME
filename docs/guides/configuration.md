# Configuration Guide

This guide covers all configuration options for AutifyME, from basic setup to advanced customization.

## 🔧 Environment Configuration

### Required Environment Variables

```bash
# AI Providers (at least one required)
OPENAI_API_KEY=sk-your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here  
GOOGLE_API_KEY=your_google_ai_key_here

# Database (required)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key_here
```

### Optional Environment Variables

```bash
# Storage
GOOGLE_DRIVE_CREDENTIALS_PATH=path/to/service-account.json
GOOGLE_DRIVE_CREDENTIALS_JSON={"type":"service_account",...}

# Monitoring
LANGSMITH_API_KEY=your_langsmith_key_here

# Security
APP_SECRET_KEY=your_app_secret_key_here

# Application Settings
DEBUG=true
LOG_LEVEL=INFO
MAX_CONCURRENT_WORKFLOWS=5

# Cost Controls
DAILY_BUDGET_USD=50.0
MAX_TOKENS_PER_REQUEST=4000
```

## 🤖 AI Provider Setup

### OpenAI Configuration

1. **Get API Key**: Visit [OpenAI API Keys](https://platform.openai.com/api-keys)
2. **Set Environment Variable**:
   ```bash
   OPENAI_API_KEY=sk-your_key_here
   ```
3. **Supported Models**:
   - `gpt-4o-mini` (Fast tier)
   - `gpt-4o` (Balanced tier)
   - `gpt-4-turbo` (Premium tier)

### Anthropic Configuration

1. **Get API Key**: Visit [Anthropic Console](https://console.anthropic.com/)
2. **Set Environment Variable**:
   ```bash
   ANTHROPIC_API_KEY=your_key_here
   ```
3. **Supported Models**:
   - `claude-3-haiku-20240307` (Fast tier)
   - `claude-3-sonnet-20240229` (Balanced tier)
   - `claude-3-opus-20240229` (Premium tier)

### Google AI Configuration

1. **Get API Key**: Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. **Set Environment Variable**:
   ```bash
   GOOGLE_API_KEY=your_key_here
   ```
3. **Supported Models**:
   - `gemini-pro` (Balanced tier)
   - `gemini-pro-vision` (Premium tier with vision)

## 🗄️ Database Setup

### Supabase Configuration

1. **Create Project**: Visit [Supabase Dashboard](https://supabase.com/dashboard)
2. **Get Credentials**:
   - Project URL: `https://your-project.supabase.co`
   - Anon Key: Found in Project Settings → API
3. **Set Environment Variables**:
   ```bash
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your_anon_key_here
   ```

### Database Schema

Run the schema setup:
```bash
# Apply database schema
uv run python -c "
from src.specialists.database import DatabaseSpecialist
db = DatabaseSpecialist()
# Schema will be auto-created on first use
"
```

## 📁 Storage Configuration

### Google Drive Setup (Optional)

For storing product images and documents:

1. **Create Service Account**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create new project or select existing
   - Enable Google Drive API
   - Create Service Account
   - Download JSON credentials

2. **Configure Credentials**:
   ```bash
   # Option 1: File path
   GOOGLE_DRIVE_CREDENTIALS_PATH=/path/to/service-account.json
   
   # Option 2: JSON content (for containers)
   GOOGLE_DRIVE_CREDENTIALS_JSON='{"type":"service_account",...}'
   ```

## ⚙️ Advanced Configuration

### LLM Configuration

Create `config/llm_config.json` for advanced LLM settings:

```json
{
  "preferred_provider": "openai",
  "fallback_providers": ["anthropic", "google"],
  "daily_budget_usd": 50.0,
  "max_tokens_per_request": 4000,
  "enable_caching": true,
  "cache_ttl_hours": 24,
  
  "task_routing": {
    "simple_classification": "fast",
    "product_enrichment": "balanced", 
    "complex_analysis": "premium",
    "image_analysis": "premium"
  }
}
```

### Custom Credentials

Add custom providers in `config/credentials.json`:

```json
{
  "stripe": {
    "provider": "stripe",
    "credential_type": "api_key",
    "env_var_name": "STRIPE_SECRET_KEY",
    "required": false,
    "description": "Stripe secret key for payments"
  },
  
  "sendgrid": {
    "provider": "sendgrid", 
    "credential_type": "api_key",
    "env_var_name": "SENDGRID_API_KEY",
    "required": false,
    "description": "SendGrid API key for email notifications"
  }
}
```

## 🔍 Validation & Testing

### Validate Configuration

```bash
# Check all credentials
uv run python scripts/validate_credentials.py

# Test specific provider
uv run python -c "
from src.core.credentials import get_credential_manager
manager = get_credential_manager()
print('OpenAI available:', manager.has_provider_credentials('openai'))
"
```

### Test Database Connection

```bash
# Test database connectivity
uv run python -c "
from src.specialists.database import DatabaseSpecialist
db = DatabaseSpecialist()
print('Database connected successfully')
"
```

## 🐳 Docker Configuration

### Environment File for Docker

Create `.env.docker`:
```bash
# Use JSON format for credentials in containers
GOOGLE_DRIVE_CREDENTIALS_JSON={"type":"service_account",...}

# Other settings remain the same
OPENAI_API_KEY=sk-your_key_here
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_key_here
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'
services:
  autifyme:
    build: .
    env_file: .env.docker
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
```

## 🔐 Security Best Practices

### Credential Security

1. **Never commit credentials** to version control
2. **Use environment variables** for all secrets
3. **Rotate credentials regularly**
4. **Use least-privilege access** for service accounts
5. **Monitor credential usage** in provider dashboards

### Network Security

```bash
# Restrict API access by IP (if supported)
# Configure in provider dashboards

# Use HTTPS only
FORCE_HTTPS=true

# Set secure session settings
SESSION_SECURE=true
SESSION_HTTPONLY=true
```

## 📊 Monitoring Configuration

### LangSmith Setup

1. **Create Account**: Visit [LangSmith](https://smith.langchain.com/)
2. **Get API Key**: From project settings
3. **Configure**:
   ```bash
   LANGSMITH_API_KEY=your_key_here
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_PROJECT=autifyme-production
   ```

### Cost Monitoring

```bash
# Set budget alerts
DAILY_BUDGET_USD=50.0
BUDGET_ALERT_THRESHOLD=0.8  # Alert at 80% of budget

# Enable cost tracking
ENABLE_COST_TRACKING=true
COST_TRACKING_INTERVAL=hourly
```

## 🚨 Troubleshooting

### Common Issues

1. **"No module named 'src'"**
   - Ensure you're running from project root
   - Use `uv run python` instead of `python`

2. **"API key not found"**
   - Check `.env` file exists and has correct keys
   - Validate with `scripts/validate_credentials.py`

3. **"Database connection failed"**
   - Verify Supabase URL and key
   - Check network connectivity
   - Ensure Supabase project is active

4. **"Model not available"**
   - Check API key permissions
   - Verify model name in configuration
   - Try fallback provider

### Debug Mode

Enable detailed logging:
```bash
DEBUG=true
LOG_LEVEL=DEBUG
LANGCHAIN_VERBOSE=true
```

## 📞 Support

Need help with configuration?

- **[Troubleshooting Guide](./troubleshooting.md)** - Common solutions
- **[GitHub Issues](https://github.com/autifyme/autifyme/issues)** - Report problems
- **[Documentation](../README.md)** - Full documentation
- **[Community Discord](https://discord.gg/autifyme)** - Get help from community

---

**Next Steps**: Once configured, try the [Getting Started Guide](./getting_started.md) to run your first workflow!