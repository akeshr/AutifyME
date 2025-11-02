"""Test to reproduce sort_order int→float conversion issue."""

import json
from pydantic import BaseModel, Field
from typing import Any

# Simulate what happens in the pipeline
class OperationIntent(BaseModel):
    """Simplified OperationIntent for testing."""
    entities: list[dict[str, Any]] = Field(...)


def test_int_to_float_conversion():
    """Test various scenarios where int might convert to float."""

    print("=" * 80)
    print("Testing Integer to Float Conversion in Pipeline")
    print("=" * 80)

    # Test 1: Direct dict creation
    print("\n1. Direct dict creation:")
    direct_dict = {"sort_order": 1, "name": "test"}
    print(f"   Original: {direct_dict}")
    print(f"   sort_order type: {type(direct_dict['sort_order'])}")

    # Test 2: JSON round-trip (common in LangChain structured output)
    print("\n2. JSON round-trip (LLM → JSON → Python):")
    json_str = '{"sort_order": 1, "name": "test"}'
    from_json = json.loads(json_str)
    print(f"   JSON string: {json_str}")
    print(f"   Parsed: {from_json}")
    print(f"   sort_order type: {type(from_json['sort_order'])}")

    # Test 3: JSON with float notation
    print("\n3. JSON with float notation (1.0 vs 1):")
    json_float_str = '{"sort_order": 1.0, "name": "test"}'
    from_json_float = json.loads(json_float_str)
    print(f"   JSON string: {json_float_str}")
    print(f"   Parsed: {from_json_float}")
    print(f"   sort_order type: {type(from_json_float['sort_order'])}")

    # Test 4: Pydantic dict[str, Any] doesn't coerce types
    print("\n4. Pydantic model with dict[str, Any]:")
    intent = OperationIntent(entities=[{"sort_order": 1}, {"sort_order": 1.0}])
    print(f"   Entity 1 sort_order type: {type(intent.entities[0]['sort_order'])}")
    print(f"   Entity 2 sort_order type: {type(intent.entities[1]['sort_order'])}")

    # Test 5: Pydantic model_dump (JSON mode)
    print("\n5. Pydantic model_dump(mode='json'):")
    dumped = intent.model_dump(mode='json')
    print(f"   Dumped: {dumped}")
    print(f"   Entity 1 sort_order type: {type(dumped['entities'][0]['sort_order'])}")
    print(f"   Entity 2 sort_order type: {type(dumped['entities'][1]['sort_order'])}")

    # Test 6: JSON dumps → loads round-trip
    print("\n6. JSON dumps → loads round-trip:")
    json_dumped = json.dumps(intent.model_dump())
    json_loaded = json.loads(json_dumped)
    print(f"   After round-trip entity 1 sort_order type: {type(json_loaded['entities'][0]['sort_order'])}")
    print(f"   After round-trip entity 2 sort_order type: {type(json_loaded['entities'][1]['sort_order'])}")

    # Test 7: Check what LLMs typically generate
    print("\n7. Typical LLM JSON response:")
    llm_json = '''
    {
        "entities": [
            {"sort_order": 1, "name": "first"},
            {"sort_order": 2, "name": "second"}
        ]
    }
    '''
    from_llm = json.loads(llm_json)
    print(f"   Parsed LLM JSON:")
    for idx, entity in enumerate(from_llm['entities']):
        print(f"   Entity {idx} sort_order: {entity['sort_order']} (type: {type(entity['sort_order'])})")

    print("\n" + "=" * 80)
    print("FINDINGS")
    print("=" * 80)
    print("✓ JSON.loads preserves int type if JSON has integer notation (1, 2, 3)")
    print("✗ JSON.loads converts to float if JSON has float notation (1.0, 2.0)")
    print("✓ Pydantic dict[str, Any] preserves whatever type is passed in")
    print("✓ model_dump() preserves original types in dict values")
    print("\nPOTENTIAL ISSUE:")
    print("If LLM generates JSON with float notation (1.0 instead of 1), or if")
    print("any intermediate processing converts integers to floats, the database")
    print("will reject the float values for integer columns.")
    print("=" * 80)


if __name__ == "__main__":
    test_int_to_float_conversion()
