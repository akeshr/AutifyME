"""Approval message formatting utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from autifyme_agents.schemas.models import Product


def format_batch_approval_message(products: list[Product]) -> str:
    """Format batch approval request message for multiple products.

    Args:
        products: List of Product objects to format for approval

    Returns:
        Formatted approval message string with product details and instructions

    Example:
        **Batch Approval Request** (3 products)

        Please review the following products:

        **Product 1:**
          - Name: Nike Shoes
          - Description: Running shoes
          - Price: Rs 1000
          - Sizes: S, M, L
          - Images: 2 attached

        ---

        **How to respond:**
        - To approve all: 'approve' or 'yes'
        - To approve some: 'approve 1 and 2'
        - To edit: 'edit product 2 price to 45'
        - To reject all: 'reject' or 'no'
    """
    message_parts = [
        f"**Batch Approval Request** ({len(products)} products)",
        "",
        "Please review the following products:",
        "",
    ]

    for idx, product in enumerate(products, 1):
        # Format each product
        product_lines = [
            f"**Product {idx}:**",
            f"  - Name: {product.name}",
            f"  - Description: {product.description}",
            f"  - Price: Rs {product.price}",
        ]

        if product.sizes:
            product_lines.append(f"  - Sizes: {', '.join(product.sizes)}")
        if product.colors:
            product_lines.append(f"  - Colors: {', '.join(product.colors)}")
        if product.image_urls:
            product_lines.append(f"  - Images: {len(product.image_urls)} attached")

        message_parts.extend(product_lines)
        message_parts.append("")  # Blank line between products

    message_parts.extend([
        "---",
        "",
        "**How to respond:**",
        "- To approve all: 'approve' or 'yes'",
        "- To approve some: 'approve 1 and 2' or 'approve product 1'",
        "- To edit: 'edit product 2 price to 45'",
        "- To reject all: 'reject' or 'no'",
    ])

    return "\n".join(message_parts)


def format_operation_intent_approval_message(operation_intent: dict[str, Any]) -> str:
    """Format OperationIntent approval request for database operations.

    Args:
        operation_intent: OperationIntent dict containing operation details

    Returns:
        Formatted approval message with operation summary and impact analysis

    Example:
        **Database Operation Approval**

        **Operation:** CREATE
        **Summary:** Create new PET Jars product family with 500ml capacity variant

        **What will be created:**
        - 1 product family
        - 2 variant axes
        - 2 variant values
        - 1 product SKU

        **Impact:** Will create 1 new product family with 1 initial SKU (500ml × 63mm)

        **Example SKUs:** PAV-JAR-PET-500ML-63MM

        Reply 'approve' or 'yes' to proceed, 'reject' or 'no' to cancel.
    """
    message_parts = [
        "**Database Operation Approval**",
        "",
        f"**Operation:** {operation_intent.get('intent_type', 'UNKNOWN').upper()}",
        f"**Summary:** {operation_intent.get('user_request_summary', 'No summary provided')}",
        "",
    ]

    # Add impact analysis
    impact_analysis = operation_intent.get('impact_analysis', {})
    new_entities_count = impact_analysis.get('new_entities_count', {})

    if new_entities_count:
        message_parts.append("**What will be created:**")
        for table, count in new_entities_count.items():
            # Format table name nicely (product_families -> product families)
            table_display = table.replace('_', ' ')
            message_parts.append(f"- {count} {table_display}")
        message_parts.append("")

    # Add business impact
    business_impact = impact_analysis.get('business_impact_summary')
    if business_impact:
        message_parts.append(f"**Impact:** {business_impact}")
        message_parts.append("")

    # Add example SKUs
    examples = impact_analysis.get('examples', [])
    if examples:
        examples_str = ', '.join(examples[:3])  # Show first 3 examples
        message_parts.append(f"**Example SKUs:** {examples_str}")
        message_parts.append("")

    # Add specialist reasoning
    reasoning = operation_intent.get('reasoning')
    if reasoning:
        message_parts.append(f"**Reasoning:** {reasoning}")
        message_parts.append("")

    message_parts.extend([
        "---",
        "",
        "Reply 'approve' or 'yes' to proceed, 'reject' or 'no' to cancel.",
    ])

    return "\n".join(message_parts)
