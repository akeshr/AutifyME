# AutifyME Setup Checklist

Complete these steps to set up your development environment.

---

## ✅ Prerequisites (Already Done)

- [x] Python 3.11+ installed
- [x] `uv` package manager installed
- [x] Virtual environment created (`.venv`)
- [x] All packages installed
- [x] Project structure in place

---

## 🔧 Next: Environment Configuration

### Step 1: Create .env File

Create a `.env` file in the project root (`C:\Abhi\personal\AutifyME\.env`) with the following content:

```bash
# ============================================
# LangSmith Configuration (Observability)
# ============================================
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY=your_langsmith_api_key_here
LANGCHAIN_PROJECT=autifyme-dev

# ============================================
# Supabase Configuration (Database & Auth)
# ============================================
SUPABASE_URL=your_supabase_project_url_here
SUPABASE_ANON_KEY=your_supabase_anon_key_here

# ============================================
# OpenAI Configuration (Primary LLM)
# ============================================
OPENAI_API_KEY=your_openai_api_key_here

# ============================================
# Google Gemini Configuration (Optional)
# ============================================
GOOGLE_API_KEY=your_google_api_key_here
```

### Step 2: Get API Keys

#### LangSmith (Required - for observability)
1. Go to https://smith.langchain.com
2. Sign up for free account
3. Go to Settings → API Keys
4. Create new key
5. Copy and paste into `.env` file

#### OpenAI (Required - for LLM)
1. Go to https://platform.openai.com/api-keys
2. Create new API key
3. Copy and paste into `.env` file

#### Supabase (Required - for database)
1. Go to https://supabase.com
2. Create new project (or use existing)
3. Go to Project Settings → API
4. Copy `URL` and `anon/public` key
5. Paste into `.env` file

#### Google Gemini (Optional)
1. Go to https://aistudio.google.com/app/apikey
2. Create API key
3. Paste into `.env` file

### Step 3: Verify Setup

Run the verification script:

```powershell
.venv\Scripts\python.exe test_langsmith_setup.py
```

If successful, you should see:
- ✅ All environment variables loaded
- ✅ LangChain imports working
- ✅ LLM call successful
- ✅ Trace appears in LangSmith dashboard

---

## 📚 Detailed Guides

- **LangSmith Setup:** See `docs/setup/LANGSMITH_SETUP.md`
- **Architecture Overview:** See `docs/whitepaper.md`
- **Tech Stack Details:** See `docs/architecture/TECH_STACK.md`

---

## 🚀 After Setup Complete

Once environment is configured, we'll proceed with:

1. **Week 1:** Build Project Manager Agent infrastructure
2. **Week 2:** Build Cataloging Department & WhatsApp integration
3. **Week 3:** Deploy to first customer

---

## ⚠️ Important Notes

- **Never commit .env file to git** (already in .gitignore)
- **Keep API keys secret** - they grant full access to your services
- **LangSmith free tier** is sufficient for development
- **OpenAI costs** - gpt-4o-mini is very cheap, gpt-4o is more expensive

---

## 🆘 Need Help?

If you encounter issues:

1. Check `.env` file exists and has correct format
2. Verify API keys are valid (no extra spaces/quotes)
3. Ensure `.venv` is activated when running scripts
4. Check `docs/setup/LANGSMITH_SETUP.md` for troubleshooting

---

**Next Command:** Once you've created the `.env` file with your API keys, run:

```powershell
.venv\Scripts\python.exe test_langsmith_setup.py
```

