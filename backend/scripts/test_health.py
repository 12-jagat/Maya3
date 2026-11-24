"""
Test script to verify GET /health through ASGI pipeline.
"""
import asyncio
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

import httpx
from app.main import app


async def main():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/health")
        print(f"Health Response Status Code: {response.status_code}")
        print(f"Health Response JSON: {response.json()}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        expected = {"status": "healthy", "application": "MAYA"}
        assert response.json() == expected, f"Expected {expected}, got {response.json()}"
        print(">>> GET /health VERIFIED SUCCESSFULLY! <<<")


if __name__ == "__main__":
    asyncio.run(main())
