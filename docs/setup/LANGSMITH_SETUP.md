# LangSmith Setup Guide

**Purpose:** Configure LangSmith for observability, debugging, and evaluation of our agentic system.

---

## Why LangSmith?

LangSmith is **essential** for our development workflow because:

1. **Debugging:** See every step of agent execution (LLM calls, tool invocations, state changes)
2. **Evaluation:** Test prompts and measure agent performance
3. **Monitoring:** Track production behavior and costs
4. **Collaboration:** Share traces with team members

**Without LangSmith, debugging multi-agent systems is nearly impossible.**

---

## Step 1: Create LangSmith Account

1. Go to https://smith.langchain.com
2. Sign up (free Developer tier is sufficient)
3. Verify your email

---

## Step 2: Get API Key

1. Once logged in, go to **Settings** (gear icon in top-right)
2. Click **API Keys** in the left sidebar
3. Click **Create API Key**
4. Give it a name (e.g., "AutifyME Development")
5. Copy the key (you won't see it again!)

---

## Step 3: Add to .env File

Open the `.env` file in the project root and fill in:

```bash
LANGCHAIN_API_KEY=lsv2_pt_your_api_key_here
```

**The other LangSmith variables are already configured:**
- `LANGCHAIN_TRACING_V2=true` - Enables automatic tracing
- `LANGCHAIN_ENDPOINT=https://api.smith.langchain.com` - Default endpoint
- `LANGCHAIN_PROJECT=autifyme-dev` - Your project name in LangSmith

---

## Step 4: Verify Setup

We'll create a simple test script to verify LangSmith is working:

```python
# test_langsmith.py
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# This simple call should automatically be traced in LangSmith
llm = ChatOpenAI(model="gpt-5-nano-2025-08-07")
response = llm.invoke([HumanMessage(content="Hello from AutifyME!")])

print("Response:", response.content)
print("\nCheck LangSmith dashboard: https://smith.langchain.com")
print("You should see a trace under the 'autifyme-dev' project")
```

Run it:
```bash
.venv\Scripts\python.exe test_langsmith.py
```

---

## Step 5: View Traces

1. Go to https://smith.langchain.com
2. Select the **autifyme-dev** project
3. You should see your test trace!
4. Click on it to see:
   - Input prompt
   - LLM response
   - Token usage
   - Latency
   - Cost

---

## Understanding Traces

Each trace shows:

### For Simple LLM Calls:
- **Input:** The prompt sent to the LLM
- **Output:** The response from the LLM
- **Metadata:** Model, temperature, tokens, cost, latency

### For Agent Workflows:
- **Full execution tree:** Every step the agent took
- **Tool calls:** Which tools were invoked and with what arguments
- **Sub-agents:** Nested agent executions
- **State changes:** How the state evolved through the workflow
- **Interrupts:** HITL approval points

---

## LangSmith Projects

We'll use different projects for different environments:

- **autifyme-dev** - Local development (default in .env)
- **autifyme-staging** - Staging environment
- **autifyme-prod** - Production

You can switch projects by changing `LANGCHAIN_PROJECT` in your environment.

---

## Advanced Features (For Later)

### 1. Datasets
Create test datasets to evaluate agent performance:
```python
from langsmith import Client

client = Client()
dataset = client.create_dataset("cataloging-test-cases")
client.create_example(
    dataset_id=dataset.id,
    inputs={"image_url": "...", "text": "..."},
    outputs={"expected_product": {...}}
)
```

### 2. Evaluators
Run automated evaluations on your agents:
```python
from langsmith.evaluation import evaluate

evaluate(
    lambda inputs: agent.invoke(inputs),
    data="cataloging-test-cases",
    evaluators=[correctness_evaluator, brand_voice_evaluator]
)
```

### 3. Prompt Playground
Test and compare different prompts directly in the UI without changing code.

---

## Troubleshooting

### "No traces appearing in LangSmith"

1. Check `.env` file has correct `LANGCHAIN_API_KEY`
2. Verify `LANGCHAIN_TRACING_V2=true`
3. Make sure `.env` is being loaded (check with `print(settings.LANGCHAIN_API_KEY)`)
4. Check you're looking at the correct project in LangSmith UI

### "API key invalid"

1. Regenerate key in LangSmith settings
2. Update `.env` file
3. Restart your application

### "Rate limit exceeded"

Free tier has limits. Upgrade to paid tier or wait for quota reset.

---

## Next Steps

Once LangSmith is configured:
1. ✅ All agent executions will be automatically traced
2. ✅ Debug issues by inspecting traces
3. ✅ Create datasets for evaluation
4. ✅ Monitor production performance

**LangSmith is now your best friend for building reliable agents!**

