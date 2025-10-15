# Analyze Costs

Analyze LangSmith token usage and costs.

## Usage

```
/analyze-costs [time-period]
```

**Periods**: `today`, `week`, `month`, `all`

## Task

Analyze LangSmith traces to understand token usage and API costs:

### 1. Fetch Runs
- Query LangSmith for runs in time period
- Filter by project if specified
- Sort by date descending

### 2. Aggregate Token Usage
- Extract token metadata from runs
- Sum total, prompt, and completion tokens
- Group by run type (PM, department, specialist, tool)
- Calculate averages per run

### 3. Estimate Costs
- Use current OpenAI pricing (verify latest rates):
  - Input: $2.50 / 1M tokens
  - Output: $10.00 / 1M tokens
- Calculate input cost, output cost, total cost
- Project monthly cost from period data

### 4. Analyze by Workflow
- Group runs by workflow type (cataloging, inquiry, conversational)
- Calculate cost per workflow
- Identify average tokens per workflow
- Find cost per successful completion

### 5. Identify Expensive Operations
- Find runs with >5k tokens
- List top 10 expensive operations
- Include run ID, name, tokens, timestamp
- Link to LangSmith trace URLs

### 6. Optimization Recommendations
Based on patterns, suggest:
- Prompt optimization (verbose prompts, redundant examples)
- Context management (summarization, history trimming)
- Model selection (GPT-4o vs GPT-4o-mini usage)
- Caching opportunities (image analysis, company context)

## Output

Generate cost report with:
- Total token usage (input/output/total)
- Cost breakdown (7 days, projected monthly, projected annual)
- Cost by workflow table
- Top expensive operations list
- Optimization recommendations with estimated savings

## Notes

- Costs are estimates based on OpenAI pricing
- Actual costs may vary with pricing changes
- Does not include LangSmith tracing costs
- Focus on high-token operations first
- Monitor after optimizations
