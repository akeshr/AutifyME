# Analyze Costs

Analyze LangSmith token usage and API costs.

## Usage

```
/analyze-costs [time-period]
```

**Periods**: `today`, `week`, `month`, `all`

## Task

Query LangSmith for runs in time period, aggregate token usage (total, prompt, completion) by run type, estimate costs using current OpenAI pricing, analyze by workflow type, identify expensive operations (>5k tokens), and suggest optimizations (prompt reduction, context management, model selection, caching).

Generate cost report with total usage, cost breakdown (7-day, monthly, annual projections), cost-by-workflow table, top expensive operations with LangSmith URLs, and optimization recommendations with estimated savings.
