"""Simple debug endpoint for Vercel."""

def handler(request):
    """Simple Vercel function handler."""
    return {
        "statusCode": 200,
        "body": "Hello from Vercel Python function!"
    }
