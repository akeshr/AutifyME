# Explain Workflow

Trace and explain a workflow from code.

## Usage

```
/explain-workflow <workflow-name>
```

**Workflows**: `cataloging`, `pm-delegation`, `hitl`, `image-analysis`

## Task

Trace through code to explain how a workflow executes.

### 1. Cataloging Workflow

**Trace the flow**:
```bash
cd agents

echo "=== Cataloging Workflow Trace ==="
echo ""
echo "1. WhatsApp Webhook receives message"
echo "   File: src/autifyme_agents/entrypoints/whatsapp_webhook.py"
echo "   - Extracts text + caption"
echo "   - Gets media_id"
echo "   - Calls runner.handle_message(sender, text, media_id)"
echo ""
echo "2. WorkflowRunner processes message"
echo "   File: src/autifyme_agents/workflows/orchestration/runner.py"
echo "   - Downloads media to /tmp/media_downloads/"
echo "   - Builds semantic payload"
echo "   - Invokes PM"
echo ""
echo "3. Project Manager classifies and delegates"
echo "   File: src/autifyme_agents/workflows/project_manager.py"
echo "   - Classifies intent: cataloging"
echo "   - Optional: Uses write_todos to plan"
echo "   - Delegates to cataloging_department via task tool"
echo ""
echo "4. Cataloging Department executes"
echo "   File: src/autifyme_agents/departments/cataloging_department.py"
echo "   - Calls write_todos to plan workflow"
echo "   - Step 1: image_analysis_specialist(image_path)"
echo "   - Step 2: cataloging_specialist(text, image_analysis)"
echo "   - Step 3: save_product(fields...)"
echo ""
echo "5. Image Analysis Specialist"
echo "   File: src/autifyme_agents/specialists/image_analysis_specialist.py"
echo "   - Converts local path to base64 data URI"
echo "   - Calls OpenAI Vision API"
echo "   - Returns ImageAnalysisResult"
echo ""
echo "6. Cataloging Specialist"
echo "   File: src/autifyme_agents/specialists/cataloging_specialist.py"
echo "   - Takes user text + image analysis"
echo "   - Uses company context (via middleware)"
echo "   - Returns Product model"
echo ""
echo "7. HITL Interrupt (save_product)"
echo "   File: interrupt_coordinator.py"
echo "   - HumanInTheLoopMiddleware intercepts save_product"
echo "   - Creates interrupt at PM level (task tool)"
echo "   - Persists to pending_approvals table"
echo "   - Runner sends approval request to user"
echo ""
echo "8. User Approves"
echo "   File: runner.py"
echo "   - Runner.handle_approval(sender, 'approve')"
echo "   - InterruptCoordinator.resume_workflow()"
echo "   - Resumes at PM level using pm_factory"
echo "   - PM continues, executes save_product"
echo ""
echo "9. Product Saved"
echo "   File: src/autifyme_agents/tools/save_product_tool.py"
echo "   - Saves to Supabase products table"
echo "   - Returns CatalogingResult"
echo ""
echo "10. Success Message"
echo "   File: runner.py + WhatsAppChannel"
echo "   - Extracts CatalogingResult"
echo "   - Sends success message via WhatsApp"
```

### 2. Generate Flow Diagram

```bash
echo "=== Cataloging Workflow Diagram ==="
cat << 'EOF'

┌─────────────────────────────────────────────────┐
│           WhatsApp Message Received             │
│  (text: "Catalog sneakers $80" + image)        │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│          WorkflowRunner.handle_message          │
│  - Download media                               │
│  - Build semantic payload                       │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│           Project Manager (DeepAgent)           │
│  - Classify intent: cataloging                  │
│  - Optional: write_todos (plan)                 │
│  - Delegate via task tool                       │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│      Cataloging Department (DeepAgent)          │
│  Tools: write_todos, image_analysis,            │
│         cataloging_specialist, save_product     │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│         write_todos (Planning Phase)            │
│  Plan:                                          │
│    1. Analyze image                             │
│    2. Structure product data                    │
│    3. Save product                              │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│    image_analysis_specialist (Step 1)           │
│  - Convert local path to base64                 │
│  - Call OpenAI Vision API                       │
│  - Return: ImageAnalysisResult                  │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│    cataloging_specialist (Step 2)               │
│  Input: user_text + image_analysis              │
│  - Use company context                          │
│  - Return: Product model                        │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│           HITL Interrupt Triggered              │
│  Before: save_product tool execution            │
│  - Interrupt at PM level (task tool)            │
│  - Persist approval state                       │
│  - Send approval request to user                │
└────────────────┬────────────────────────────────┘
                 │
                 │ (User: "approve")
                 ▼
┌─────────────────────────────────────────────────┐
│        Resume at PM Level (pm_factory)          │
│  - PM continues from checkpoint                 │
│  - Executes save_product with approval          │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│          save_product (Step 3)                  │
│  - Save to Supabase products table              │
│  - Return: CatalogingResult                     │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│            Success Message Sent                 │
│  "Product saved! Name: X, Price: Y"             │
└─────────────────────────────────────────────────┘

EOF
```

### 3. Show Middleware Stack

```bash
echo "=== Middleware Stack ==="
echo ""
echo "Department Middleware (cataloging_department.py):"
echo "  1. SummarizationMiddleware (auto-added by DeepAgents)"
echo "  2. CompanyContextMiddleware (custom)"
echo "  3. HumanInTheLoopMiddleware (auto-added via tool_configs)"
echo ""
echo "Middleware execution order:"
echo "  before_model:"
echo "    - SummarizationMiddleware.before_model"
echo "    - CompanyContextMiddleware.before_model (injects context)"
echo "  after_model:"
echo "    - HumanInTheLoopMiddleware.after_model (checks tool_configs)"
```

### 4. Show HITL Points

```bash
echo "=== HITL Configuration ==="
echo ""
echo "HITL-enabled tools:"
echo "  - save_product (cataloging_department)"
echo "    Config: allow_accept, allow_edit, allow_respond"
echo ""
echo "Interrupt location:"
echo "  - Triggers at PM level during task tool execution"
echo "  - Checkpoint namespace: 'task:cataloging_department'"
echo ""
echo "Resume location:"
echo "  - Resumes at PM level using pm_factory"
echo "  - PM continues from checkpoint"
echo "  - save_product executes after approval"
```

### 5. Show Data Flow

```bash
echo "=== Data Flow ==="
echo ""
echo "User Input:"
echo "  text: 'Catalog sneakers, $80, sizes 7-11'"
echo "  media: /tmp/media_downloads/img123.jpg"
echo ""
echo "PM Payload:"
echo "  messages: ["
echo "    HumanMessage("
echo "      'User message: Catalog sneakers, $80, sizes 7-11"
echo "       Media: 1 image(s)"
echo "         - Media 1: image (path: /tmp/media_downloads/img123.jpg)'"
echo "    )"
echo "  ]"
echo ""
echo "Department Receives:"
echo "  Same semantic description from PM"
echo ""
echo "image_analysis_specialist Returns:"
echo "  ImageAnalysisResult("
echo "    visual_description='White canvas sneakers...'"
echo "    identified_colors=['white', 'black']"
echo "    style_tags=['casual', 'sporty']"
echo "  )"
echo ""
echo "cataloging_specialist Returns:"
echo "  Product("
echo "    name='White Canvas Sneakers'"
echo "    price=80.0"
echo "    sizes=['7', '8', '9', '10', '11']"
echo "    colors=['white', 'black']"
echo "    description='Casual white canvas sneakers...'"
echo "  )"
echo ""
echo "save_product Saves:"
echo "  Database record with all Product fields"
echo ""
echo "Final Result:"
echo "  CatalogingResult("
echo "    success=True"
echo "    product_id='abc-123'"
echo "    message='Product saved successfully'"
echo "  )"
```

### 6. Show Context Flow

```bash
echo "=== Context Engineering ==="
echo ""
echo "Company Profile (loaded once at startup):"
echo "  name: 'StyleHub'"
echo "  brand_voice: 'Friendly and approachable...'"
echo "  target_audience: 'Young adults 18-35...'"
echo ""
echo "Injection Points:"
echo "  1. PM Prompt (template format)"
echo "     Brand Voice: {brand_voice}"
echo "     Target Audience: {target_audience}"
echo ""
echo "  2. Department Prompt (via CompanyContextMiddleware)"
echo "     Middleware injects context into state"
echo ""
echo "  3. Specialists (via middleware, not parameters)"
echo "     Context available in agent state"
echo "     Tools remain context-light"
```

### 7. Generate Complete Report

```markdown
## Workflow Explanation: Cataloging

### Overview
End-to-end product cataloging with image analysis and HITL approval.

### Entry Point
**File**: `entrypoints/whatsapp_webhook.py`
**Function**: `receive()` endpoint

### Flow Steps

1. **Message Reception** (webhook)
   - Extract text + caption from WhatsApp payload
   - Get media_id
   - Call `runner.handle_message()`

2. **Media Download** (runner)
   - Download media to temp directory
   - Returns local file path

3. **PM Invocation** (runner → PM)
   - Build semantic payload
   - Invoke PM with text + media path

4. **Intent Classification** (PM)
   - Classify: cataloging intent
   - Optional: Plan with write_todos
   - Delegate via task tool

5. **Department Execution** (cataloging_department)
   - Plan workflow with write_todos
   - Execute steps sequentially
   - Use middleware for context

6. **Image Analysis** (image_analysis_specialist)
   - Convert local path → base64
   - Call Vision API
   - Return structured result

7. **Product Structuring** (cataloging_specialist)
   - Combine text + image analysis
   - Use company context
   - Return Product model

8. **HITL Interrupt** (before save_product)
   - Middleware intercepts
   - Create interrupt at PM level
   - Persist state + media path
   - Send approval request

9. **User Approval** (webhook → runner)
   - User sends "approve"
   - Resume at PM level
   - PM continues execution

10. **Product Saving** (save_product)
    - Save to database
    - Return success result

11. **Success Message** (channel)
    - Format completion message
    - Send via WhatsApp

### Key Components

| Component | Type | Responsibility |
|-----------|------|----------------|
| PM | DeepAgent | Intent classification, delegation |
| Cataloging Dept | DeepAgent | Tool coordination, planning |
| Image Specialist | Agent | Vision analysis |
| Cataloging Specialist | Agent | Product structuring |
| save_product | Tool | Database persistence |

### Middleware Stack

1. SummarizationMiddleware (auto)
2. CompanyContextMiddleware (custom)
3. HumanInTheLoopMiddleware (auto)

### HITL Configuration

- **Tool**: save_product
- **Interrupt Level**: PM (task tool)
- **Resume Pattern**: PM level with pm_factory
- **State Storage**: pending_approvals table

### Data Transformations

```
WhatsApp Payload
  ↓
Semantic Description
  ↓
PM Messages
  ↓
Department Tasks
  ↓
Tool Calls
  ↓
Structured Outputs
  ↓
Database Records
```

### Critical Patterns

- **Sequential Execution**: Tools called in order via planning
- **Base64 Conversion**: Local files → data URIs
- **PM-Level Resume**: HITL resumes at PM, not department
- **Context Injection**: Via middleware, not parameters
```

## Notes

- Trace follows actual code execution
- Include file paths and line numbers
- Show data transformations
- Explain architectural decisions
- Link to relevant docs
