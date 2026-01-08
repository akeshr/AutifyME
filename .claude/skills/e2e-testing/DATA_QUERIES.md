# Supabase Data Queries

Query library for fetching real production data for testing.

**Usage:** Use `mcp__supabase__execute_sql` tool with these queries.

---

## Products

### Random Active Product

```sql
SELECT id, name, sku, price, description
FROM products
WHERE is_active = true AND status = 'ACTIVE'
ORDER BY RANDOM()
LIMIT 1;
```

### Product with Image

```sql
SELECT
    p.id,
    p.name,
    p.sku,
    p.price,
    pa.storage_path as image_path,
    pa.id as asset_id
FROM products p
JOIN product_assets pa ON pa.product_id = p.id
WHERE p.is_active = true
  AND pa.asset_type = 'image'
ORDER BY RANDOM()
LIMIT 1;
```

### Products by Category

```sql
SELECT id, name, sku, price, custom_attributes->>'category' as category
FROM products
WHERE custom_attributes->>'category' ILIKE '%[CATEGORY]%'
  AND is_active = true
ORDER BY RANDOM()
LIMIT 5;
```

### High-Value Products

```sql
SELECT id, name, sku, price
FROM products
WHERE price > 5000 AND is_active = true
ORDER BY price DESC
LIMIT 10;
```

### Products with Sale Pricing

```sql
SELECT id, name, sku, price, sale_price,
       sale_price_start, sale_price_end
FROM products
WHERE sale_price IS NOT NULL
  AND is_active = true
ORDER BY RANDOM()
LIMIT 5;
```

### Products by Type

```sql
SELECT id, name, sku, product_type
FROM products
WHERE product_type = '[TYPE]'  -- FINISHED_GOOD, RAW_MATERIAL, etc.
  AND is_active = true
ORDER BY RANDOM()
LIMIT 5;
```

### Products with Variants (Family Members)

```sql
SELECT
    pf.name as family_name,
    p.id,
    p.name,
    p.sku,
    p.is_primary_variant
FROM products p
JOIN product_families pf ON p.product_family_id = pf.id
WHERE p.is_active = true
ORDER BY pf.name, p.is_primary_variant DESC
LIMIT 10;
```

---

## Product Assets

### Random Image Asset

```sql
SELECT
    pa.id,
    pa.product_id,
    pa.storage_path,
    pa.asset_type,
    p.name as product_name
FROM product_assets pa
JOIN products p ON pa.product_id = p.id
WHERE pa.asset_type = 'image'
ORDER BY RANDOM()
LIMIT 1;
```

### Recent Image Uploads

```sql
SELECT
    pa.id,
    pa.storage_path,
    pa.created_at,
    p.name as product_name
FROM product_assets pa
JOIN products p ON pa.product_id = p.id
WHERE pa.asset_type = 'image'
ORDER BY pa.created_at DESC
LIMIT 10;
```

### Products Without Images

```sql
SELECT p.id, p.name, p.sku
FROM products p
LEFT JOIN product_assets pa ON pa.product_id = p.id AND pa.asset_type = 'image'
WHERE pa.id IS NULL AND p.is_active = true
LIMIT 10;
```

---

## Workflow Outcomes (Execution History)

### Recent Executions

```sql
SELECT
    id,
    trace_id,
    message_text,
    intent,
    department,
    success,
    duration_seconds,
    created_at
FROM workflow_outcomes
ORDER BY created_at DESC
LIMIT 20;
```

### Recent Failures

```sql
SELECT
    id,
    trace_id,
    message_text,
    intent,
    error_type,
    error_message,
    created_at
FROM workflow_outcomes
WHERE success = false
ORDER BY created_at DESC
LIMIT 10;
```

### Failures by Error Type

```sql
SELECT
    error_type,
    COUNT(*) as count,
    MAX(created_at) as last_occurrence
FROM workflow_outcomes
WHERE success = false
  AND created_at > NOW() - INTERVAL '7 days'
GROUP BY error_type
ORDER BY count DESC;
```

### High Latency Executions

```sql
SELECT
    id,
    trace_id,
    message_text,
    intent,
    duration_seconds,
    created_at
FROM workflow_outcomes
WHERE duration_seconds > 60
ORDER BY duration_seconds DESC
LIMIT 10;
```

### Executions by Intent

```sql
SELECT
    intent,
    COUNT(*) as total,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful,
    AVG(duration_seconds) as avg_duration
FROM workflow_outcomes
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY intent
ORDER BY total DESC;
```

### Executions by Department

```sql
SELECT
    department,
    COUNT(*) as total,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful,
    ROUND(AVG(duration_seconds)::numeric, 2) as avg_duration
FROM workflow_outcomes
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY department
ORDER BY total DESC;
```

### Thread History

```sql
SELECT
    thread_id,
    message_text,
    intent,
    success,
    created_at
FROM workflow_outcomes
WHERE thread_id = '[THREAD_ID]'
ORDER BY created_at ASC;
```

### Executions with Media

```sql
SELECT
    id,
    trace_id,
    message_text,
    media_type,
    success,
    created_at
FROM workflow_outcomes
WHERE media_id IS NOT NULL
ORDER BY created_at DESC
LIMIT 20;
```

---

## Company Context

### Company Details

```sql
SELECT
    name,
    brand_voice,
    target_audience,
    industry,
    default_currency,
    currency_symbol
FROM companies
LIMIT 1;
```

---

## Categories & Taxonomy

### All Categories

```sql
SELECT DISTINCT
    custom_attributes->>'category' as category,
    COUNT(*) as product_count
FROM products
WHERE custom_attributes->>'category' IS NOT NULL
GROUP BY custom_attributes->>'category'
ORDER BY product_count DESC;
```

### Product Tags

```sql
SELECT DISTINCT
    unnest(tags) as tag,
    COUNT(*) as usage_count
FROM products
WHERE tags IS NOT NULL AND tags != '{}'
GROUP BY tag
ORDER BY usage_count DESC
LIMIT 20;
```

---

## Analytics Queries

### Daily Execution Volume

```sql
SELECT
    DATE(created_at) as date,
    COUNT(*) as executions,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful,
    ROUND(AVG(duration_seconds)::numeric, 2) as avg_duration
FROM workflow_outcomes
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

### Success Rate Trend

```sql
SELECT
    DATE(created_at) as date,
    COUNT(*) as total,
    ROUND(
        100.0 * SUM(CASE WHEN success THEN 1 ELSE 0 END) / COUNT(*),
        1
    ) as success_rate
FROM workflow_outcomes
WHERE created_at > NOW() - INTERVAL '14 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

### Intent Distribution

```sql
SELECT
    intent,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 1) as percentage
FROM workflow_outcomes
WHERE created_at > NOW() - INTERVAL '7 days'
  AND intent IS NOT NULL
GROUP BY intent
ORDER BY count DESC;
```

---

## Cleanup Queries

### Delete Test Products

```sql
-- Delete products with test SKU prefix
DELETE FROM products
WHERE sku LIKE 'TEST-%' OR sku LIKE 'INT-TEST-%';
```

---

## Usage Examples

### Fetching Data for Scenario

```python
# Using Supabase MCP
result = mcp__supabase__execute_sql(
    query="""
    SELECT p.name, p.sku, p.price, pa.storage_path
    FROM products p
    JOIN product_assets pa ON pa.product_id = p.id
    WHERE pa.asset_type = 'image'
    ORDER BY RANDOM()
    LIMIT 1
    """
)

# Use in scenario
product = result[0]
message = f"Update {product['name']} price to Rs {int(product['price'] * 1.1)}"
media_path = download_from_storage(product['storage_path'])
```

### Finding Similar Failures

```python
# Find failures with similar message pattern
result = mcp__supabase__execute_sql(
    query="""
    SELECT trace_id, message_text, error_type
    FROM workflow_outcomes
    WHERE success = false
      AND message_text ILIKE '%catalog%'
    ORDER BY created_at DESC
    LIMIT 5
    """
)
```
