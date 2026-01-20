"""
Smart Motion Detector v2 - Main Entry Point
"""
import logging
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from app.services.settings import get_settings_service


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Smart Motion Detector API",
    version="2.0.0",
    description="Person detection with thermal/color camera support"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production'da değiştir
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize settings service
settings_service = get_settings_service()


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Smart Motion Detector v2", "status": "ok"}


@app.get("/ready")
async def ready():
    """Readiness probe endpoint."""
    return {"ready": True, "status": "ok"}


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "version": "2.0.0",
        "uptime_s": 0,
        "ai": {"enabled": False, "reason": "not_configured"},
        "cameras": {"online": 0, "retrying": 0, "down": 0},
        "components": {"pipeline": "ok", "telegram": "disabled", "mqtt": "disabled"}
    }


@app.get("/api/settings")
async def get_settings() -> Dict[str, Any]:
    """
    Get current application settings.
    
    Returns settings with masked secrets (api_key, bot_token).
    
    Returns:
        Dict containing current settings
        
    Raises:
        HTTPException: 500 if settings cannot be loaded
    """
    try:
        settings = settings_service.get_settings()
        logger.info("Settings retrieved successfully")
        return settings
    except Exception as e:
        logger.error(f"Failed to get settings: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": True,
                "code": "INTERNAL_ERROR",
                "message": f"Failed to load settings: {str(e)}"
            }
        )


@app.put("/api/settings")
async def update_settings(partial_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update application settings.
    
    Supports partial updates - only provided fields are updated.
    Nested updates are supported (e.g., {"detection": {"model": "yolov8s-person"}}).
    
    Args:
        partial_data: Partial configuration data
        
    Returns:
        Dict containing updated settings with masked secrets
        
    Raises:
        HTTPException: 400 if validation fails, 500 if save fails
    """
    try:
        updated_settings = settings_service.update_settings(partial_data)
        logger.info("Settings updated successfully")
        return updated_settings
    except ValidationError as e:
        logger.error(f"Settings validation failed: {e}")
        # Extract validation errors
        errors = []
        for error in e.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            errors.append(f"{field}: {error['msg']}")
        
        raise HTTPException(
            status_code=400,
            detail={
                "error": True,
                "code": "VALIDATION_ERROR",
                "message": "Settings validation failed",
                "errors": errors
            }
        )
    except Exception as e:
        logger.error(f"Failed to update settings: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": True,
                "code": "INTERNAL_ERROR",
                "message": f"Failed to update settings: {str(e)}"
            }
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
