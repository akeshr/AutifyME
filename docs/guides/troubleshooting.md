# Troubleshooting Guide

Common issues and solutions for AutifyME setup and usage.

## 🚨 Installation Issues

### "uv not found" or "uv is not recognized"

**Problem**: `uv` command not available after installation.

**Solutions**:
1. **Use Python module**: `python -m uv` instead of `uv`
2. **Install officially**: 
   ```bash
   # Uninstall pip version
   pip uninstall uv
   
   # Install official version
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```
3. **Add to PATH**: Add `~/.local/bin` to your PATH environment variable

### "No module named 'src'"

**Problem**: Python can't find the src module.

**Solutions**:
1. **Run from project root**: Ensure you're in the AutifyME directory
2. **Use uv run**: Always use `uv run python` instead of `python`
3. **Check virtual environment**: Ensure `.venv` directory exists

### Dependencies installation fails

**Problem**: Package installation errors during setup.

**Solutions**:
1. **Update uv**: `uv self update`
2. **Clear cache**: `uv cache clean`
3. **Manual install**: `uv sync --reinstall`
4. **Check Python version**: Ensure Python 3.11+ is installed

## 🔑 Credential Issues

### "API key not found" errors

**Problem**: Credential manager can't find API keys.

**Solutions**:
1. **Check .env file exists**: `ls -la .env`
2. **Validate format**: No spaces around `=` in `.env`
3. **Check variable names**: Must match exactly (case-sensitive)
4. **Restart terminal**: Reload environment variables
5. **Validate credentials**:
   ```bash
   uv run python scripts/validate_credentials.py
   ```

### "Invalid API key" errors

**Problem**: API key is found but rejected by provider.

**Solutions**:
1. **Check key format**: Ensure complete key is copied
2. **Verify permissions**: Check API key has required permissions
3. **Check quotas**: Ensure you haven't exceeded usage limits
4. **Test manually**: Try key in provider's playground/console

### Supabase connection fails

**Problem**: Can't connect to Supabase database.

**Solutions**:
1. **Check URL format**: Should be `https://your-project.supabase.co`
2. **Verify project status**: Ensure Supabase project is active
3. **Check key type**: Use anon key, not service role key (unless needed)
4. **Network issues**: Try from different network/VPN
5. **Test connection**:
   ```bash
   uv run python -c "
   from supabase import create_client
   import os
   client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
   print('Connected successfully')
   "
   ```

## 🤖 AI Provider Issues

### OpenAI errors

**Common Issues**:
- `RateLimitError`: You've exceeded rate limits
- `InvalidRequestError`: Check model name and parameters
- `AuthenticationError`: Invalid API key

**Solutions**:
1. **Check billing**: Ensure you have credits/billing set up
2. **Verify model access**: Some models require special access
3. **Reduce request rate**: Lower `MAX_CONCURRENT_WORKFLOWS`
4. **Use different model**: Try `gpt-4o-mini` instead of `gpt-4`

### Anthropic errors

**Common Issues**:
- `PermissionError`: API key doesn't have required permissions
- `OverloadedError`: Service temporarily unavailable

**Solutions**:
1. **Check API access**: Ensure you have Claude API access
2. **Retry with backoff**: Anthropic has automatic retries
3. **Use fallback**: Configure OpenAI as fallback provider

### Google AI errors

**Common Issues**:
- `PermissionDenied`: API key invalid or restricted
- `ResourceExhausted`: Quota exceeded

**Solutions**:
1. **Enable API**: Ensure Generative AI API is enabled in Google Cloud
2. **Check quotas**: Review usage in Google Cloud Console
3. **Verify key**: Test in Google AI Studio first

## 🔄 Workflow Issues

### Workflow hangs or times out

**Problem**: Workflow starts but never completes.

**Solutions**:
1. **Check logs**: Enable debug mode with `DEBUG=true`
2. **Reduce complexity**: Try with simpler inputs first
3. **Check network**: Ensure stable internet connection
4. **Increase timeout**: Set higher `WORKFLOW_TIMEOUT_MINUTES`
5. **Monitor resources**: Check CPU/memory usage

### "No suitable LLM provider available"

**Problem**: Can't create any LLM instance.

**Solutions**:
1. **Check credentials**: Ensure at least one provider is configured
2. **Verify model availability**: Some models may be deprecated
3. **Check fallbacks**: Configure multiple providers
4. **Test providers individually**:
   ```bash
   uv run python -c "
   from src.core.llm_factory import get_fast_llm
   llm = get_fast_llm()
   print('LLM created successfully')
   "
   ```

### Database operation failures

**Problem**: Database operations fail or return errors.

**Solutions**:
1. **Check connection**: Verify Supabase credentials
2. **Review permissions**: Ensure database user has required permissions
3. **Check schema**: Verify tables exist and have correct structure
4. **Monitor quotas**: Check Supabase usage limits
5. **Enable RLS**: Ensure Row Level Security is properly configured

## 🐳 Docker Issues

### Container won't start

**Problem**: Docker container fails to start.

**Solutions**:
1. **Check logs**: `docker logs <container_name>`
2. **Verify environment**: Ensure `.env.docker` has all required variables
3. **Check ports**: Ensure port 8000 is available
4. **Build fresh**: `docker-compose build --no-cache`

### Environment variables not loaded

**Problem**: Credentials not available in container.

**Solutions**:
1. **Use JSON format**: For credentials in containers
2. **Check env file**: Ensure `env_file` is specified in docker-compose.yml
3. **Verify paths**: Use absolute paths for mounted volumes

## 📊 Performance Issues

### Slow response times

**Problem**: Workflows take too long to complete.

**Solutions**:
1. **Use faster models**: Configure `FAST` tier models for simple tasks
2. **Enable caching**: Set `ENABLE_CACHING=true`
3. **Reduce batch size**: Lower concurrent operations
4. **Optimize prompts**: Shorter, more specific prompts
5. **Check network**: Ensure good internet connection

### High costs

**Problem**: AI API costs are higher than expected.

**Solutions**:
1. **Set budget limits**: Configure `DAILY_BUDGET_USD`
2. **Use cheaper models**: Prefer `gpt-4o-mini` over `gpt-4`
3. **Enable caching**: Reduce duplicate API calls
4. **Monitor usage**: Check provider dashboards regularly
5. **Optimize workflows**: Remove unnecessary AI calls

## 🔍 Debugging Tips

### Enable Debug Mode

```bash
# In .env file
DEBUG=true
LOG_LEVEL=DEBUG
LANGCHAIN_VERBOSE=true
LANGSMITH_TRACING=true
```

### Check System Status

```bash
# Validate entire system
uv run python scripts/validate_credentials.py

# Test specific components
uv run python -c "
from src.core.credentials import get_credential_manager
from src.specialists.database import DatabaseSpecialist
from src.core.llm_factory import get_fast_llm

print('Testing components...')
manager = get_credential_manager()
print(f'Credentials: {len(manager.get_available_providers())} providers')

db = DatabaseSpecialist()
print('Database: Connected')

llm = get_fast_llm()
print('LLM: Available')
print('All components working!')
"
```

### Monitor Resources

```bash
# Check disk space
df -h

# Check memory usage
free -h

# Check Python processes
ps aux | grep python
```

## 📞 Getting Help

If you're still having issues:

1. **Search existing issues**: [GitHub Issues](https://github.com/autifyme/autifyme/issues)
2. **Create new issue**: Include error messages, logs, and system info
3. **Join community**: [Discord Server](https://discord.gg/autifyme)
4. **Check documentation**: [Full Documentation](../README.md)

### When reporting issues, include:

- **Operating System**: Windows/macOS/Linux version
- **Python Version**: `python --version`
- **AutifyME Version**: Git commit hash
- **Error Messages**: Complete error output
- **Configuration**: Sanitized `.env` file (remove actual keys)
- **Steps to Reproduce**: Exact commands that cause the issue

---

**Still stuck?** Don't hesitate to ask for help in our [community Discord](https://discord.gg/autifyme)!