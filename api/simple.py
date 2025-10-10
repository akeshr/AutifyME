"""Simple FastAPI app for Vercel testing."""

# Try importing FastAPI, but fallback if not available
try:
    from fastapi import FastAPI
    app = FastAPI()

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "message": "Simple FastAPI app working!"}

    @app.get("/")
    async def root():
        return {"message": "Hello from simple FastAPI app"}

except ImportError:
    # Fallback to basic response if FastAPI not available
    def handler(request):
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": '{"status": "fallback", "message": "FastAPI not available, using basic handler"}'
        }

    app = handler
