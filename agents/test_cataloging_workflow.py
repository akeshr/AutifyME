import asyncio
from pprint import pprint

from autifyme_agents.specialists.cataloging_specialist import create_cataloging_specialist
from autifyme_agents.tools.storage_tools import save_product
from autifyme_agents.schemas.models import Product

async def main():
    """
    An end-to-end test script for the initial cataloging workflow.

    This script performs two key architectural tests:
    1.  **Specialist Agent Test:** Invokes the CatalogingSpecialist to test its
        ability to extract unstructured text into a structured Pydantic model
        using LangChain v1's `.with_structured_output()`.
    2.  **Storage Tool Test:** Takes the structured output from the agent and
        passes it to the `save_product` tool, testing the full integration
        from tool definition down to the Supabase client and database.
    """
    print("--- Starting Cataloging Workflow Test ---")

    # 1. Define a sample user message from WhatsApp
    user_message = """
    Hi, I want to add a new t-shirt to our catalog.
    It's called the 'Sunset Tee'.
    Description: A comfortable cotton t-shirt with a vibrant sunset graphic. Perfect for summer evenings.
    Price is 29.99.
    We have it in sizes S, M, and L.
    Available colors are Coral, Navy, and White.
    """

    # 2. Create and invoke the Cataloging Specialist
    print("\n[Step 1/2] Invoking Cataloging Specialist to extract product data...")
    cataloging_specialist = create_cataloging_specialist()
    structured_product: Product = await cataloging_specialist.ainvoke({
        "user_message": user_message
    })

    print("\n✅ Specialist returned structured Pydantic object:")
    pprint(structured_product.model_dump())

    # 3. Pass the structured product to the storage tool
    print("\n[Step 2/2] Invoking 'save_product' tool to save to Supabase...")
    try:
        saved_product = save_product.func(product=structured_product)
        print("\n✅ Product successfully saved to Supabase:")
        pprint(saved_product.model_dump())
        print(f"\n--- Test Complete: Product saved with ID: {saved_product.id} ---")

    except Exception as e:
        print(f"\n❌ Error saving product to Supabase: {e}")
        print("--- Test Failed ---")


if __name__ == "__main__":
    # Ensure the event loop is managed correctly for async execution
    asyncio.run(main())
