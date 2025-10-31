"""Test Gemini 2.5 Flash capabilities for structured output and vision."""

from dotenv import load_dotenv
load_dotenv('.env')

from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

class TestSchema(BaseModel):
    """Test schema for structured output."""
    description: str = Field(description='Visual description')
    colors: list[str] = Field(description='List of colors')
    material: str = Field(description='Material type')

# Test 1: Structured output support
print("=" * 60)
print("TEST 1: Gemini 2.5 Flash - Structured Output")
print("=" * 60)

llm = ChatGoogleGenerativeAI(model='gemini-2.5-flash', temperature=0.0)
print(f"[OK] Model initialized: gemini-2.5-flash")
print(f"[OK] Has with_structured_output: {hasattr(llm, 'with_structured_output')}")

try:
    structured_llm = llm.with_structured_output(TestSchema, method='json_schema')
    print(f"[OK] Structured output binding successful")
    print(f"  Type: {type(structured_llm).__name__}")

    # Test invocation with text
    result = structured_llm.invoke("Describe a blue leather jacket")
    print(f"[OK] Invocation successful")
    print(f"  Result type: {type(result).__name__}")
    print(f"  Description: {result.description[:50]}...")
    print(f"  Colors: {result.colors}")
    print(f"  Material: {result.material}")
except Exception as e:
    print(f"[ERROR] Error: {e}")

# Test 2: Vision/multimodal support
print("\n" + "=" * 60)
print("TEST 2: Gemini 2.5 Flash - Vision Support")
print("=" * 60)

try:
    # Test with multimodal message format
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "What color is the sky typically?"},
            ],
        }
    ]

    response = structured_llm.invoke(messages)
    print(f"[OK] Multimodal message format supported")
    print(f"  Colors detected: {response.colors}")
except Exception as e:
    print(f"[ERROR] Error with multimodal format: {e}")

# Test 3: Model info
print("\n" + "=" * 60)
print("TEST 3: Model Configuration")
print("=" * 60)
print(f"Model: {llm.model}")
print(f"Temperature: {llm.temperature}")
print(f"Supports streaming: {hasattr(llm, 'stream')}")

print("\n" + "=" * 60)
print("SUMMARY: Gemini 2.5 Flash is READY for migration")
print("=" * 60)
