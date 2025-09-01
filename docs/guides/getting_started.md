# Getting Started with AutifyME

Welcome to AutifyME! This guide will help you get up and running in just a few minutes.

## 🎯 What is AutifyME?

AutifyME is the world's first Agentic Business Operating System that automates end-to-end business functions using AI agents, domain specialists, and deterministic tools.

## ⚡ Quick Start (5 minutes)

### 1. Prerequisites

- **Python 3.11+** (we recommend 3.13+)
- **Git** for cloning the repository
- **API Keys** for at least one AI provider (OpenAI, Anthropic, or Google)
- **Supabase Account** for database (free tier available)

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/autifyme/autifyme.git
cd autifyme

# Run the setup script
python scripts/setup.py
```

The setup script will:
- Install `uv` package manager (if needed)
- Create virtual environment
- Install all dependencies
- Create `.env` file from template

### 3. Configuration

Edit the `.env` file with your credentials:

```bash
# Required: At least one AI provider
OPENAI_API_KEY=sk-your_openai_key_here
# OR
ANTHROPIC_API_KEY=your_anthropic_key_here
# OR  
GOOGLE_API_KEY=your_google_ai_key_here

# Required: Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key_here
```

### 4. Validate Setup

```bash
# Check if everything is configured correctly
uv run python scripts/validate_credentials.py
```

You should see ✅ for your configured providers.

### 5. Run Your First Workflow

```bash
# Start the cataloging workflow
uv run python -m src.workflows.cataloging
```

## 🏗️ Architecture Overview

AutifyME follows a three-layer architecture:

```
┌─────────────────┐
│     Agents      │  ← Orchestrate workflows with state management
├─────────────────┤
│   Specialists   │  ← Provide domain expertise (AI-powered)
├─────────────────┤
│     Tools       │  ← Execute deterministic operations
└─────────────────┘
```

## 🔄 Available Workflows

### 1. **Cataloging Workflow** (Ready)
Automatically processes product images and creates structured catalog entries.

**Use Case**: E-commerce businesses wanting to automate product cataloging.

```bash
uv run python -m src.workflows.cataloging
```

### 2. **Marketing Workflow** (Coming Soon)
Generates marketing content, social media posts, and campaigns.

### 3. **Website Workflow** (Coming Soon)  
Creates and manages business websites automatically.

## 🛠️ Core Components

### Agents
- **Cataloging Agent**: Orchestrates product processing workflows
- **Marketing Agent**: Manages marketing content generation
- **Website Agent**: Handles website creation and updates

### Specialists
- **Database Specialist**: Intelligent data operations with AI optimization
- **Content Specialist**: AI-powered content analysis and generation
- **Design Specialist**: Visual design and layout optimization
- **SEO Specialist**: Search engine optimization automation

### Tools
- **Image Analysis**: Computer vision for product recognition
- **Database Operations**: CRUD operations with caching
- **External APIs**: Integration with third-party services
- **Validation Tools**: Data quality and integrity checks

## 📊 Cost Management

AutifyME includes built-in cost optimization:

- **Model Routing**: Automatically uses cheaper models for simple tasks
- **Caching**: Reduces API calls by caching frequent requests
- **Budget Controls**: Set daily spending limits
- **Usage Tracking**: Monitor costs per workflow

Default budget: $50/day (configurable in `.env`)

## 🔐 Security Features

- **Centralized Credentials**: Secure credential management system
- **Multi-Tenancy**: Business data isolation
- **Audit Logging**: Complete audit trail for compliance
- **Row-Level Security**: Database-level access controls

## 📈 Monitoring & Analytics

- **LangSmith Integration**: Track AI model performance
- **Workflow Analytics**: Monitor success rates and bottlenecks
- **Cost Analytics**: Detailed cost breakdowns
- **Performance Metrics**: Response times and throughput

## 🆘 Need Help?

- **[Troubleshooting Guide](./troubleshooting.md)** - Common issues and solutions
- **[Configuration Guide](./configuration.md)** - Detailed setup instructions
- **[API Documentation](../api/rest_api.md)** - Integration reference
- **[GitHub Issues](https://github.com/autifyme/autifyme/issues)** - Report bugs or request features

## 🎉 What's Next?

1. **Explore Workflows**: Try different workflows to see AutifyME's capabilities
2. **Customize Configuration**: Adjust settings for your specific needs
3. **Integrate APIs**: Connect AutifyME to your existing systems
4. **Scale Up**: Deploy to production with Docker
5. **Contribute**: Help improve AutifyME by contributing code or documentation

---

**Ready to automate your business?** Start with the [Cataloging Workflow](../workflows/cataloging_workflow.md)!