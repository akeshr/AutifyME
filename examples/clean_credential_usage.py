"""
Clean Credential Usage Examples

Demonstrates the CORRECT way to use the credential system following
the mandatory patterns defined in the steering document.
"""

import asyncio
from src.core.credentials import (
    # Service classes (for manual creation if needed)
    Supabase, OpenAI, Anthropic,
    
    # Service getters (primary usage pattern)
    supabase, openai, anthropic,
    
    # Type aliases for tools
    DatabaseService, AIService
)
from src.tools.database.crud_tools import create_record, list_records


async def demonstrate_clean_patterns():
    """Show the clean credential patterns in action"""
    
    print("🎯 Clean Credential Usage Examples")
    print("=" * 50)
    
    # ✅ CORRECT: Simple service access
    print("\n1. ✅ Simple Service Access")
    try:
        db = supabase()
        ai = openai()
        
        print(f"   Database: {db.url[:30]}...")
        print(f"   AI Service: {ai.api_key[:10]}...")
        print("   ✅ Services loaded successfully")
    except Exception as e:
        print(f"   ❌ Service loading failed: {e}")
    
    # ✅ CORRECT: Clean tool usage
    print("\n2. ✅ Clean Tool Usage")
    try:
        db = supabase()
        
        # Tools take service objects, not provider names
        result = await create_record(
            database=db,  # Service object
            table="test_table",
            data={"name": "test", "value": 123}
        )
        
        if result["success"]:
            print("   ✅ Record created successfully")
        else:
            print(f"   ℹ️ Create result: {result['message']}")
            
    except Exception as e:
        print(f"   ❌ Tool usage failed: {e}")
    
    # ✅ CORRECT: Multiple services
    print("\n3. ✅ Multiple Services")
    try:
        db = supabase()
        ai_openai = openai()
        ai_anthropic = anthropic()
        
        print("   Available services:")
        print(f"   - Database: Supabase")
        print(f"   - AI: OpenAI, Anthropic")
        print("   ✅ Multiple services ready")
        
    except Exception as e:
        print(f"   ❌ Multiple services failed: {e}")
    
    # ✅ CORRECT: Manual service creation (for testing)
    print("\n4. ✅ Manual Service Creation (Testing)")
    try:
        # Useful for unit tests or custom configurations
        test_db = Supabase(
            url="https://test.supabase.co",
            key="test_key_123"
        )
        
        test_ai = OpenAI(
            api_key="sk-test123",
            organization_id="org-test"
        )
        
        print("   ✅ Manual services created for testing")
        
    except Exception as e:
        print(f"   ❌ Manual creation failed: {e}")
    
    # ✅ CORRECT: Type-safe tool functions
    print("\n5. ✅ Type-Safe Tool Functions")
    
    def example_tool(database: DatabaseService, ai: AIService) -> dict:
        """Example tool that accepts any compatible service"""
        return {
            "database_type": type(database).__name__,
            "ai_type": type(ai).__name__,
            "message": "Tool works with any compatible service"
        }
    
    try:
        db = supabase()
        ai = openai()
        
        result = example_tool(database=db, ai=ai)
        print(f"   ✅ Tool result: {result['message']}")
        
    except Exception as e:
        print(f"   ❌ Type-safe tool failed: {e}")


def demonstrate_anti_patterns():
    """Show what NOT to do (for educational purposes)"""
    
    print("\n\n❌ Anti-Patterns (DO NOT USE)")
    print("=" * 50)
    
    print("\n❌ DON'T: Use provider names in function arguments")
    print("   def bad_tool(provider: str = 'openai'):")
    print("   # This violates the clean pattern!")
    
    print("\n❌ DON'T: Use generic credential getters")
    print("   get_database_credentials('supabase')")
    print("   get_ai_credentials('openai')")
    print("   # Use supabase() and openai() instead!")
    
    print("\n❌ DON'T: Import global config in services")
    print("   from src.core.config import get_config")
    print("   # Services should be self-contained!")
    
    print("\n❌ DON'T: Use 'Credentials' suffix in class names")
    print("   class SupabaseCredentials:")
    print("   # Use 'Supabase' instead!")


async def main():
    """Run all examples"""
    await demonstrate_clean_patterns()
    demonstrate_anti_patterns()
    
    print("\n\n🎉 Clean Credential Patterns Complete!")
    print("Use these patterns for all future development.")


if __name__ == "__main__":
    asyncio.run(main())