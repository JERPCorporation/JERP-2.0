"""
JERP 2.0 - API Router
Main router for all API endpoints
"""
from fastapi import APIRouter

api_router = APIRouter()

# Import and include endpoint routers here as they are created
# Example: from app.api.v1.endpoints import compliance
# api_router.include_router(compliance.router, prefix="/compliance", tags=["compliance"])
