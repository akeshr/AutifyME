"""Approval message formatting utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

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
