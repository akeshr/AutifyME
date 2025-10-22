# Tool Design Standards for 2-Level Architecture

**Status:** Production Standard  
**Purpose:** Comprehensive guidelines for tool creation, ensuring consistency and reliability  
**Version:** 2.0 (2-Level Architecture)

---

## I. CORE DESIGN PHILOSOPHY

### Tool vs Agent Decision Matrix

```
Use TOOL when:
✅ Operation is deterministic (same input → same output)
✅ External API call (Vision, Database, Search, etc.)
✅ File I/O operation
✅ Data transformation without reasoning
✅ Validation/checking logic
✅ Integration with third-party services

Use AGENT when:
✅ Synthesis across multiple inputs required
✅ Reasoning with uncertainty
✅ Planning multi-step processes
✅ Natural language interpretation needed
✅ Context-dependent decision making
```

**Critical Rule:** If you're debating tool vs agent, default to tool. Agents should be rare (synthesis/reasoning only).

---

## II. TOOL ARCHITECTURE PATTERN

### Complete Tool Template

```python
"""
Tool Description: One-line summary of what this tool does

Category: [API_CALL | DATABASE | FILE_IO | INTEGRATION | VALIDATION | HITL]
Domain: [cataloging | marketing | seo | operations | etc.]
HITL Required: [Yes | No]

Usage Context:
- When specialist needs to [specific operation]
- Prerequisites: [what must be true before calling]
- Post-conditions: [what's guaranteed after successful call]
"""

from typing import Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, validator
from decimal import Decimal

# Input Model (Strict Typing)
class ToolNameInput(BaseModel):
    """Input schema for tool_name_tool with validation."""
    
    param1: str = Field(..., description="What param1 represents, constraints")
    param2: int = Field(ge=1, le=100, description="Range-validated integer")
    param3: Optional[str] = Field(None, description="Optional parameter")
    
    @validator('param1')
    def validate_param1(cls, v):
        """Custom validation logic."""
        if not v.strip():
            raise ValueError("param1 cannot be empty")
        return v.strip()

# Output Model (Structured Response)
class ToolNameOutput(BaseModel):
    """Output schema for tool_name_tool."""
    
    field1: str = Field(..., description="What field1 contains")
    field2: float = Field(..., ge=0, description="Non-negative result")
    warnings: List[str] = Field(default_factory=list, description="Non-critical issues")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context")

# Error Types (Domain-Specific)
class ToolNameError(Exception):
    """Base exception for tool_name_tool errors."""
    pass

class ToolNameValidationError(ToolNameError):
    """Raised when input validation fails."""
    pass

class ToolNameAPIError(ToolNameError):
    """Raised when external API fails."""
    pass

# Tool Implementation
@tool
def tool_name_tool(input_data: ToolNameInput) -> ToolNameOutput:
    """
    [One-line description]
    
    Detailed explanation of what this tool does, including:
    - Core functionality
    - Expected behavior
    - Side effects (if any)
    - Performance characteristics
    
    Args:
        input_data: ToolNameInput with validated parameters
        
    Returns:
        ToolNameOutput with structured results
        
    Raises:
        ToolNameValidationError: When input validation fails
        ToolNameAPIError: When external service is unavailable
        ToolNameError: For other tool-specific errors
        
    Example:
        >>> input_data = ToolNameInput(param1="value", param2=10)
        >>> result = tool_name_tool(input_data)
        >>> print(result.field1)
        'expected_output'
    """
    
    # 1. VALIDATION (Early Exit)
    try:
        validate_preconditions(input_data)
    except Exception as e:
        raise ToolNameValidationError(f"Validation failed: {str(e)}")
    
    # 2. MAIN LOGIC (Error Handling)
    try:
        result = perform_operation(input_data)
    except ExternalAPIException as e:
        raise ToolNameAPIError(f"API call failed: {str(e)}")
    except Exception as e:
        raise ToolNameError(f"Unexpected error: {str(e)}")
    
    # 3. POST-PROCESSING (Warnings, Metadata)
    warnings = []
    if result.has_issue():
        warnings.append("Non-critical issue detected")
    
    # 4. STRUCTURED RETURN
    return ToolNameOutput(
        field1=result.value,
        field2=result.score,
        warnings=warnings,
        metadata={"source": "tool_name_tool", "timestamp": datetime.now()}
    )
```

---

## III. TOOL CATEGORIES & PATTERNS

### Category 1: API Call Tools

**Characteristics:**
- Wraps external service (Vision, Classification, Search, etc.)
- Handles authentication/credentials
- Implements retry logic with exponential backoff
- Manages rate limiting
- Transforms external response to internal model

**Example: Image Analysis Tool**

```python
"""
Extract product attributes from images using Vision API.

Category: API_CALL
Domain: cataloging
HITL Required: No
"""

class ImageAnalysisInput(BaseModel):
    image_url: str = Field(..., description="Public HTTPS URL or base64 data URI")
    analysis_type: Literal["product_attributes", "quality_check", "category_hint"]
    confidence_threshold: float = Field(0.7, ge=0, le=1)

class ImageAnalysisOutput(BaseModel):
    attributes: Dict[str, str]  # {color: "blue", material: "plastic", ...}
    confidence: float
    category_suggestions: List[str]
    quality_score: int = Field(..., ge=1, le=10)

@tool
def image_analysis_tool(input_data: ImageAnalysisInput) -> ImageAnalysisOutput:
    """
    Analyze product image to extract attributes using Vision API.
    
    Retry Logic: 3 attempts with exponential backoff (1s, 2s, 4s)
    Timeout: 30 seconds per request
    Rate Limit: 100 requests/minute (handled by client)
    """
    
    # Retry wrapper
    for attempt in range(3):
        try:
            response = vision_api_client.analyze(
                url=input_data.image_url,
                features=["OBJECT_DETECTION", "LABEL_DETECTION"]
            )
            break
        except RateLimitError:
            if attempt < 2:
                time.sleep(2 ** attempt)
                continue
            raise ImageAnalysisAPIError("Rate limit exceeded after retries")
        except Timeout:
            if attempt < 2:
                continue
            raise ImageAnalysisAPIError("Timeout after 3 attempts")
    
    # Transform response
    attributes = extract_attributes(response)
    confidence = calculate_confidence(response)
    
    if confidence < input_data.confidence_threshold:
        raise LowConfidenceError(f"Confidence {confidence} below threshold")
    
    return ImageAnalysisOutput(
        attributes=attributes,
        confidence=confidence,
        category_suggestions=response.labels[:3],
        quality_score=assess_quality(response)
    )
```

### Category 2: Database Tools

**Characteristics:**
- Single database operation per tool
- Transaction management (commit/rollback)
- Connection pooling handled
- Input sanitization (SQL injection prevention)
- Returns structured data (not raw DB records)

**Example: Save Product Tool (with HITL)**

```python
"""
Persist product catalog entry with human approval.

Category: DATABASE + HITL
Domain: cataloging
HITL Required: Yes
"""

class ProductData(BaseModel):
    name: str = Field(..., max_length=200)
    category: str
    subcategory: str
    price: Decimal = Field(..., ge=0)
    description: str = Field(..., max_length=1000)
    attributes: Dict[str, Any]
    image_url: str
    company_id: int

class SaveProductOutput(BaseModel):
    product_id: int
    status: Literal["approved", "rejected"]
    rejection_reason: Optional[str] = None

@tool
def save_product_tool(product_data: ProductData) -> SaveProductOutput:
    """
    Save product to database after human approval (HITL).
    
    HITL Flow:
    1. Generate preview of product entry
    2. Interrupt workflow with preview
    3. Await user approval/rejection/modification
    4. If approved: persist to database
    5. If rejected: return rejection status
    """
    
    # Generate preview for HITL
    preview = generate_product_preview(product_data)
    
    # Interrupt for human approval
    approval = interrupt_for_human_approval(
        display=preview,
        options=["approve", "reject", "modify"]
    )
    
    if approval.status == "reject":
        return SaveProductOutput(
            product_id=-1,
            status="rejected",
            rejection_reason=approval.reason
        )
    
    # Proceed with database write
    try:
        with db.transaction():
            product_id = db.products.insert(
                name=product_data.name,
                category_id=get_category_id(product_data.category),
                price=product_data.price,
                description=product_data.description,
                attributes=json.dumps(product_data.attributes),
                image_url=product_data.image_url,
                company_id=product_data.company_id,
                created_at=datetime.now()
            )
            
            # Audit trail
            db.audit_log.insert(
                action="product_created",
                entity_id=product_id,
                user_action="approved",
                timestamp=datetime.now()
            )
            
        return SaveProductOutput(product_id=product_id, status="approved")
        
    except IntegrityError as e:
        raise DatabaseError(f"Duplicate product or constraint violation: {str(e)}")
    except Exception as e:
        raise DatabaseError(f"Database operation failed: {str(e)}")
```

### Category 3: Validation Tools

**Characteristics:**
- No side effects (read-only)
- Fast execution (< 100ms)
- Clear pass/fail with detailed reasons
- Provides recommendations when validation fails

**Example: Price Validation Tool**

```python
"""
Validate if product price is reasonable for its category.

Category: VALIDATION
Domain: cataloging
HITL Required: No
"""

class PriceValidationInput(BaseModel):
    price: Decimal = Field(..., ge=0)
    category: str
    region: str = Field("IN", description="ISO country code")

class PriceValidationOutput(BaseModel):
    is_valid: bool
    suggested_range: Tuple[Decimal, Decimal]
    warnings: List[str]
    confidence: float

@tool
def validate_price_tool(input_data: PriceValidationInput) -> PriceValidationOutput:
    """
    Check if price is within reasonable range for category.
    
    Logic:
    - Fetch historical prices for category in region
    - Calculate percentile distribution (P10, P50, P90)
    - Flag if price outside P10-P90 range
    - Provide suggested range and warnings
    """
    
    # Fetch benchmark data
    benchmark = price_benchmark_service.get_category_stats(
        category=input_data.category,
        region=input_data.region
    )
    
    if not benchmark:
        return PriceValidationOutput(
            is_valid=True,  # Can't validate without data
            suggested_range=(Decimal("0"), Decimal("999999")),
            warnings=["No pricing data available for this category"],
            confidence=0.0
        )
    
    # Calculate position
    is_valid = benchmark.p10 <= input_data.price <= benchmark.p90
    warnings = []
    
    if input_data.price < benchmark.p10:
        warnings.append(f"Price below typical range (Rs {benchmark.p10}-{benchmark.p90})")
    elif input_data.price > benchmark.p90:
        warnings.append(f"Price above typical range (Rs {benchmark.p10}-{benchmark.p90})")
    
    return PriceValidationOutput(
        is_valid=is_valid,
        suggested_range=(benchmark.p10, benchmark.p90),
        warnings=warnings,
        confidence=benchmark.sample_size / 1000  # Confidence based on data volume
    )
```

### Category 4: Integration Tools

**Characteristics:**
- Connects AutifyME to external platforms
- Handles OAuth/API keys securely
- Maps external data models to internal models
- Implements webhook patterns where applicable

**Example: Shopify Product Sync Tool**

```python
"""
Sync product to Shopify store.

Category: INTEGRATION
Domain: operations
HITL Required: No
"""

class ShopifySyncInput(BaseModel):
    product_id: int
    shopify_store_url: str
    sync_inventory: bool = True

class ShopifySyncOutput(BaseModel):
    shopify_product_id: str
    sync_status: Literal["success", "partial", "failed"]
    errors: List[str]

@tool
def shopify_sync_tool(input_data: ShopifySyncInput) -> ShopifySyncOutput:
    """
    Sync AutifyME product to Shopify store.
    
    Steps:
    1. Fetch product from AutifyME database
    2. Transform to Shopify product model
    3. Create/update product via Shopify API
    4. Optionally sync inventory levels
    """
    
    # Fetch internal product
    product = db.products.get(input_data.product_id)
    
    # Transform to Shopify format
    shopify_product = {
        "title": product.name,
        "body_html": product.description,
        "vendor": "AutifyME",
        "product_type": product.category,
        "variants": [{
            "price": str(product.price),
            "sku": f"AUTIFY-{product.id}",
            "inventory_quantity": product.stock if input_data.sync_inventory else 0
        }],
        "images": [{"src": product.image_url}]
    }
    
    # Sync to Shopify
    try:
        shopify_client = get_shopify_client(input_data.shopify_store_url)
        response = shopify_client.products.create(shopify_product)
        
        return ShopifySyncOutput(
            shopify_product_id=response.id,
            sync_status="success",
            errors=[]
        )
    except ShopifyAPIError as e:
        return ShopifySyncOutput(
            shopify_product_id="",
            sync_status="failed",
            errors=[str(e)]
        )
```

---

## IV. HITL (Human-in-the-Loop) PATTERN

### When to Use HITL

**Use HITL for:**
✅ Financial transactions (payments, refunds)
✅ Data modifications with business impact (catalog entries, pricing changes)
✅ External communications (emails, social posts, ads)
✅ Irreversible actions (deletions, publications)
✅ Compliance-sensitive operations (HR, legal)

**Don't Use HITL for:**
❌ Read-only operations (searches, analysis)
❌ Temporary/draft operations
❌ Internal system operations (logs, caching)
❌ Validation checks

### HITL Implementation Pattern

```python
@tool
def hitl_operation_tool(input_data: InputModel) -> OutputModel:
    """Tool requiring human approval before execution."""
    
    # 1. PREPARE PREVIEW
    # - Generate human-readable summary
    # - Include all relevant details
    # - Show potential impact
    preview = {
        "action": "Save Product",
        "summary": "Creating new catalog entry",
        "details": {
            "Product": input_data.name,
            "Category": input_data.category,
            "Price": f"Rs {input_data.price}",
            "Description": input_data.description[:100] + "..."
        },
        "impact": "This product will be visible in your catalog immediately",
        "visual": generate_product_card_html(input_data)  # Rich preview
    }
    
    # 2. INTERRUPT FOR APPROVAL
    # - Pause workflow
    # - Show preview to user
    # - Await response
    approval = interrupt_for_human_input(
        message="Please review this product before saving:",
        display=preview,
        options={
            "approve": "Save to catalog",
            "reject": "Don't save",
            "modify": "Edit details before saving"
        },
        timeout=3600  # 1 hour max wait
    )
    
    # 3. HANDLE RESPONSE
    if approval.choice == "reject":
        return OutputModel(
            status="rejected",
            rejection_reason=approval.reason or "User chose not to proceed"
        )
    
    if approval.choice == "modify":
        # User provided modifications
        input_data = apply_modifications(input_data, approval.modifications)
        # Re-show preview recursively
        return hitl_operation_tool(input_data)
    
    # 4. EXECUTE APPROVED ACTION
    try:
        result = execute_operation(input_data)
        return OutputModel(status="approved", result=result)
    except Exception as e:
        return OutputModel(status="error", error_message=str(e))
```

### HITL Preview Best Practices

**Effective Previews:**
✅ Show exactly what will happen in plain language
✅ Include visual representations (cards, tables, charts)
✅ Highlight risks or irreversible aspects
✅ Provide clear action buttons (approve/reject/modify)
✅ Show cost implications if applicable

**Poor Previews:**
❌ Technical jargon or code
❌ Incomplete information
❌ Ambiguous action buttons
❌ No visual context
❌ Hidden side effects

---

## V. ERROR HANDLING STANDARDS

### Error Hierarchy

```
ToolError (Base)
  ├─ ValidationError (Input problems)
  │   ├─ MissingParameterError
  │   ├─ InvalidFormatError
  │   └─ ConstraintViolationError
  │
  ├─ ExecutionError (Runtime problems)
  │   ├─ APIError
  │   ├─ DatabaseError
  │   ├─ NetworkError
  │   └─ TimeoutError
  │
  ├─ BusinessRuleError (Domain logic)
  │   ├─ InsufficientPermissionsError
  │   ├─ DuplicateEntityError
  │   └─ ConflictError
  │
  └─ ExternalServiceError (Third-party failures)
      ├─ RateLimitError
      ├─ AuthenticationError
      └─ ServiceUnavailableError
```

### Error Response Pattern

```python
class ToolErrorResponse(BaseModel):
    """Standardized error response for all tools."""
    
    success: bool = False
    error_type: str  # ValidationError, APIError, etc.
    error_message: str  # Human-readable description
    error_code: str  # Machine-readable code (e.g., "VISION_API_TIMEOUT")
    retry_able: bool  # Can this operation be retried?
    retry_after: Optional[int] = None  # Seconds to wait before retry
    details: Dict[str, Any] = {}  # Additional context
```

### Retry Logic Pattern

```python
def execute_with_retry(
    operation: Callable,
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    retryable_exceptions: Tuple = (APIError, NetworkError, TimeoutError)
):
    """
    Execute operation with exponential backoff retry.
    
    Args:
        operation: Function to execute
        max_attempts: Maximum retry attempts
        backoff_factor: Exponential backoff multiplier
        retryable_exceptions: Exception types that trigger retry
    """
    
    for attempt in range(max_attempts):
        try:
            return operation()
        except retryable_exceptions as e:
            if attempt == max_attempts - 1:
                # Final attempt failed
                raise ToolError(f"Operation failed after {max_attempts} attempts: {str(e)}")
            
            # Calculate backoff
            wait_time = backoff_factor ** attempt
            logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s...")
            time.sleep(wait_time)
        except Exception as e:
            # Non-retryable error
            raise ToolError(f"Non-retryable error: {str(e)}")
```

---

## VI. TESTING STANDARDS

### Unit Testing Pattern

```python
def test_tool_name_tool_success():
    """Test successful tool execution."""
    
    # Arrange
    input_data = ToolNameInput(
        param1="valid_value",
        param2=50
    )
    
    # Act
    result = tool_name_tool(input_data)
    
    # Assert
    assert result.field1 == "expected_value"
    assert result.field2 > 0
    assert len(result.warnings) == 0

def test_tool_name_tool_validation_error():
    """Test tool handles invalid input."""
    
    # Arrange
    invalid_input = ToolNameInput(
        param1="",  # Empty string should fail
        param2=50
    )
    
    # Act & Assert
    with pytest.raises(ToolNameValidationError) as exc_info:
        tool_name_tool(invalid_input)
    
    assert "param1 cannot be empty" in str(exc_info.value)

def test_tool_name_tool_api_failure():
    """Test tool handles external API failure gracefully."""
    
    # Arrange
    input_data = ToolNameInput(param1="value", param2=50)
    
    # Mock external API to fail
    with mock.patch('external_api.call') as mock_api:
        mock_api.side_effect = ExternalAPIException("Service unavailable")
        
        # Act & Assert
        with pytest.raises(ToolNameAPIError):
            tool_name_tool(input_data)
```

### Integration Testing Pattern

```python
def test_tool_end_to_end_flow():
    """Test tool in realistic scenario with real dependencies."""
    
    # Arrange: Set up test database/API credentials
    setup_test_environment()
    
    input_data = ToolNameInput(
        param1="real_value",
        param2=75
    )
    
    # Act: Execute with real services
    result = tool_name_tool(input_data)
    
    # Assert: Verify actual side effects
    assert result.status == "success"
    assert database_contains_entity(result.entity_id)
    
    # Cleanup
    teardown_test_environment()
```

---

## VII. DOCUMENTATION STANDARDS

### Required Documentation

**Every Tool Must Have:**

1. **Module Docstring:**
   - One-line summary
   - Category (API_CALL, DATABASE, etc.)
   - Domain (cataloging, marketing, etc.)
   - HITL requirement (Yes/No)

2. **Function Docstring:**
   - Detailed description
   - Args section with types
   - Returns section with structure
   - Raises section with all exceptions
   - Example usage

3. **Input/Output Models:**
   - Field descriptions
   - Validation constraints
   - Default values with rationale

4. **Error Documentation:**
   - When each error occurs
   - How to recover
   - Whether retryable

### Example: Complete Tool Documentation

```python
"""
Image Analysis Tool - Extract product attributes from images.

Category: API_CALL
Domain: cataloging
HITL Required: No

Purpose:
Analyzes product images using Vision API to extract structured attributes
like color, material, style, and condition. Provides confidence scores and
category suggestions to assist with product classification.

Dependencies:
- Google Cloud Vision API (authentication via service account)
- Image storage (images must be publicly accessible via HTTPS)

Performance:
- Typical latency: 1-3 seconds
- Rate limit: 100 requests/minute
- Retry policy: 3 attempts with exponential backoff

Usage Context:
- First step in cataloging workflow
- Called by cataloging_specialist
- Requires user to upload image before invocation
"""

@tool
def image_analysis_tool(input_data: ImageAnalysisInput) -> ImageAnalysisOutput:
    """
    Analyze product image to extract attributes and suggest categories.
    
    This tool wraps the Google Cloud Vision API to perform object detection
    and label classification. It transforms raw Vision API responses into
    structured product attributes suitable for catalog entries.
    
    Process:
    1. Validate image URL accessibility
    2. Call Vision API with OBJECT_DETECTION and LABEL_DETECTION features
    3. Extract attributes from detection results
    4. Calculate confidence scores
    5. Generate category suggestions from labels
    6. Assess image quality for catalog suitability
    
    Args:
        input_data: ImageAnalysisInput containing:
            - image_url: Public HTTPS URL or base64 data URI
            - analysis_type: Type of analysis to perform
            - confidence_threshold: Minimum acceptable confidence (0.0-1.0)
            
    Returns:
        ImageAnalysisOutput containing:
            - attributes: Dict of detected attributes (color, material, etc.)
            - confidence: Overall confidence score (0.0-1.0)
            - category_suggestions: List of suggested categories
            - quality_score: Image quality rating (1-10)
            
    Raises:
        InvalidImageError: Image URL inaccessible or image corrupted
        VisionAPIError: Vision API service unavailable or rate limited
        LowConfidenceError: Analysis confidence below threshold
        
    Example:
        >>> input_data = ImageAnalysisInput(
        ...     image_url="https://cdn.example.com/product.jpg",
        ...     analysis_type="product_attributes"
        ... )
        >>> result = image_analysis_tool(input_data)
        >>> print(result.attributes)
        {'color': 'blue', 'material': 'plastic', 'style': 'modern'}
        >>> print(result.confidence)
        0.89
    """
    # Implementation...
```

---

## VIII. PERFORMANCE GUIDELINES

### Optimization Principles

**Fast Tools (< 100ms):**
- Validation tools
- Local calculations
- Memory-only operations
- Cache hits

**Medium Tools (< 1s):**
- Database queries (simple)
- File I/O (small files)
- API calls (fast services)

**Slow Tools (< 5s):**
- External API calls (Vision, ML models)
- Database queries (complex)
- File processing (large files)

**Very Slow Tools (> 5s):**
- Batch operations
- Report generation
- Complex ML inference
- Should be async/background jobs

### Performance Monitoring

```python
import time
from functools import wraps

def monitor_performance(tool_name: str):
    """Decorator to track tool execution time."""
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start
                
                # Log performance metrics
                logger.info(f"{tool_name} completed in {duration:.2f}s")
                metrics.record(tool_name, "success", duration)
                
                return result
            except Exception as e:
                duration = time.time() - start
                logger.error(f"{tool_name} failed after {duration:.2f}s: {str(e)}")
                metrics.record(tool_name, "error", duration)
                raise
        
        return wrapper
    return decorator

@tool
@monitor_performance("image_analysis_tool")
def image_analysis_tool(input_data: ImageAnalysisInput) -> ImageAnalysisOutput:
    # Implementation...
```

---

## IX. SECURITY STANDARDS

### Input Sanitization

```python
def sanitize_input(input_data: BaseModel) -> BaseModel:
    """Sanitize all string inputs to prevent injection attacks."""
    
    for field_name, field_value in input_data.__dict__.items():
        if isinstance(field_value, str):
            # Remove dangerous characters
            sanitized = re.sub(r'[<>"\';(){}]', '', field_value)
            setattr(input_data, field_name, sanitized)
    
    return input_data
```

### Credential Management

```python
# ❌ BAD: Hardcoded credentials
API_KEY = "sk_live_abc123..."

# ✅ GOOD: Environment variables
API_KEY = os.getenv("VISION_API_KEY")

# ✅ BETTER: Secrets manager
API_KEY = secrets_manager.get_secret("vision_api_key")
```

### Access Control

```python
def check_permissions(user_id: int, operation: str) -> bool:
    """Verify user has permission for operation."""
    
    user = db.users.get(user_id)
    required_permission = OPERATION_PERMISSIONS.get(operation)
    
    if required_permission not in user.permissions:
        raise InsufficientPermissionsError(
            f"User {user_id} lacks permission: {required_permission}"
        )
    
    return True

@tool
def privileged_operation_tool(input_data: InputModel) -> OutputModel:
    """Tool requiring specific permissions."""
    
    # Check permissions before execution
    check_permissions(input_data.user_id, "privileged_operation")
    
    # Proceed with operation...
```

---

## X. MAINTENANCE & EVOLUTION

### When to Refactor Tools

**Refactor when:**
- Tool doing multiple unrelated things → Split into separate tools
- Tool frequently modified → Abstract common patterns
- Tool has complex branching logic → Simplify or extract sub-tools
- Tool performance degrades → Optimize or cache
- Tool error rate increases → Improve error handling

### Versioning Strategy

```python
"""
Tool versioning for backward compatibility.

Version 1: Original implementation
Version 2: Added optional parameters
"""

@tool
def image_analysis_tool_v2(input_data: ImageAnalysisInputV2) -> ImageAnalysisOutput:
    """
    Version 2: Added support for multiple analysis types.
    
    Changes from v1:
    - Added analysis_type parameter (default: "product_attributes")
    - Added confidence_threshold parameter (default: 0.7)
    - Improved error handling for low confidence scenarios
    """
    # Implementation...

# Keep v1 for backward compatibility
@tool
def image_analysis_tool(image_url: str) -> ImageAnalysisOutput:
    """Version 1: Deprecated, use image_analysis_tool_v2."""
    return image_analysis_tool_v2(
        ImageAnalysisInputV2(
            image_url=image_url,
            analysis_type="product_attributes"
        )
    )
```

### Deprecation Process

1. **Announce:** Document deprecation in tool docstring
2. **Warning:** Log warnings when deprecated tool called
3. **Grace Period:** 2-4 weeks before removal
4. **Remove:** Delete deprecated tool, update all callers

---

**END OF TOOL DESIGN STANDARDS**

These standards ensure every tool in AutifyME is reliable, maintainable, secure,
and performs optimally. Follow these patterns religiously for production quality.
