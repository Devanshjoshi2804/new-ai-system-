"""
Few-Shot Examples for API Testing (BUG #21 FIX)
Provides concrete examples to help AI generate better payloads
"""

FEW_SHOT_EXAMPLES = {
    "create_user": {
        "description": "Create a new user account",
        "good_examples": [
            {
                "name": "John Doe",
                "email": "john.doe@example.com",
                "password": "SecurePass123!",
                "age": 30,
                "isActive": True
            },
            {
                "name": "Jane Smith",
                "email": "jane.smith@company.io",
                "password": "MyP@ssw0rd",
                "age": 25,
                "isActive": True
            }
        ],
        "bad_examples": [
            {
                "name": "string",  # ❌ Placeholder instead of real value
                "email": "invalid-email",  # ❌ Invalid format
                "password": "123",  # ❌ Too short
                "age": "30",  # ❌ String instead of number
                "isActive": "true"  # ❌ String instead of boolean
            }
        ]
    },
    
    "create_order": {
        "description": "Create a new order",
        "good_examples": [
            {
                "productId": "prod_12345",
                "quantity": 2,
                "shippingAddress": {
                    "street": "123 Main St",
                    "city": "New York",
                    "zipCode": "10001",
                    "country": "USA"
                },
                "paymentMethod": "credit_card"
            }
        ],
        "bad_examples": [
            {
                "quantity": "2",  # ❌ String instead of number
                "shippingAddress": "123 Main St",  # ❌ String instead of object
                "paymentMethod": "card"  # ❌ Wrong enum value
            }
        ]
    },
    
    "update_status": {
        "description": "Update entity status",
        "good_examples": [
            {"status": "active"},
            {"status": "inactive"},
            {"status": "pending"}
        ],
        "bad_examples": [
            {"status": "true"},  # ❌ Boolean as string
            {"status": 1},  # ❌ Number instead of string
            {"status": "enabled"}  # ❌ Wrong enum value
        ]
    }
}


def get_few_shot_prompt(operation_type: str = None) -> str:
    """
    Get few-shot examples for AI prompt (BUG #21 FIX)
    
    Args:
        operation_type: Type of operation (create, update, etc.)
    
    Returns:
        Few-shot examples as formatted string
    """
    
    prompt = """
📚 FEW-SHOT LEARNING EXAMPLES:

Here are examples of CORRECT vs INCORRECT payloads:

✅ GOOD EXAMPLE - User Creation:
{
  "name": "John Doe",           ← Real name, not "string"
  "email": "john@example.com",  ← Valid email format
  "age": 30,                    ← Number, not "30" string
  "isActive": true              ← Boolean, not "true" string
}

❌ BAD EXAMPLE - Common Mistakes:
{
  "name": "string",             ← Don't use placeholders!
  "email": "invalid",           ← Invalid format
  "age": "30",                  ← Wrong type (string vs number)
  "isActive": "true"            ← Wrong type (string vs boolean)
}

✅ GOOD EXAMPLE - Order Creation:
{
  "productId": "prod_12345",    ← Use realistic IDs
  "quantity": 2,                ← Numeric value
  "shippingAddress": {          ← Nested object properly structured
    "street": "123 Main St",
    "city": "New York",
    "zipCode": "10001"
  },
  "paymentMethod": "credit_card" ← Valid enum value
}

❌ BAD EXAMPLE - Order Creation:
{
  "quantity": "2",              ← String instead of number
  "shippingAddress": "address", ← String instead of object
  "paymentMethod": "card"       ← Invalid enum (not in allowed values)
}

🎯 KEY LEARNINGS:
1. Use REAL values, not placeholders like "string" or "number"
2. Match EXACT data types: number (not "number"), boolean (not "boolean")
3. Use VALID formats: emails have @, dates are YYYY-MM-DD
4. Nested objects need full structure, not flat strings
5. Enum values must be EXACTLY from allowed list
6. Required fields MUST be present
7. Don't add fields not in documentation

Apply these patterns to generate your payload!
"""
    
    return prompt


def get_field_examples() -> str:
    """Get examples for common field patterns (BUG #21 FIX)"""
    
    return """
📋 COMMON FIELD PATTERNS:

Names:
✅ "John Doe", "Jane Smith", "Bob Johnson"
❌ "string", "name", "user"

Emails:
✅ "john.doe@example.com", "user@company.io"
❌ "email", "invalid-email", "test"

Dates:
✅ "2024-01-15", "2023-12-25"
❌ "2024/01/15", "01-15-2024", "date"

Booleans:
✅ true, false (no quotes!)
❌ "true", "false", "yes", "no"

Numbers:
✅ 123, 45.67, 0
❌ "123", "45.67", "number"

Status/Enum:
✅ Use EXACT value from docs: "active", "pending"
❌ Similar words: "enabled", "waiting"

IDs:
✅ "user_123", "ord_456", "prod_abc"
❌ "id", "123", "{id}"
"""
