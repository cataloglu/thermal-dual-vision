import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from app.dependencies import settings_service, mqtt_service
from app.models.config import AppConfig

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/settings")
async def get_settings() -> Dict[str, Any]:
    try:
        return settings_service.get_settings()
    except Exception as e:
        logger.error(f"Failed to get settings: {e}")
        raise HTTPException(status_code=500, detail={"error": True, "code": "INTERNAL_ERROR", "message": f"Failed to load settings: {str(e)}"})


@router.get("/api/settings/defaults")
async def get_default_settings() -> Dict[str, Any]:
    try:
        defaults = settings_service.get_default_config()
        return settings_service._mask_secrets(defaults)
    except Exception as e:
        logger.error(f"Failed to load default settings: {e}")
        raise HTTPException(status_code=500, detail={"error": True, "code": "INTERNAL_ERROR", "message": f"Failed to load defaults: {str(e)}"})


@router.post("/api/settings/reset")
async def reset_settings() -> Dict[str, Any]:
    try:
        defaults = settings_service.get_default_config()
        settings_service.save_config(AppConfig(**defaults))
        logger.info("Settings reset to defaults")
        return settings_service.get_settings()
    except Exception as e:
        logger.error(f"Failed to reset settings: {e}")
        raise HTTPException(status_code=500, detail={"error": True, "code": "INTERNAL_ERROR", "message": f"Failed to reset settings: {str(e)}"})


@router.put("/api/settings")
async def update_settings(partial_data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        updated_settings = settings_service.update_settings(partial_data)
        if "mqtt" in partial_data:
            logger.info("MQTT settings changed, restarting service...")
            mqtt_service.restart()
        logger.info("Settings updated successfully")
        return updated_settings
    except ValidationError as e:
        errors = [f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}" for err in e.errors()]
        raise HTTPException(status_code=400, detail={"error": True, "code": "VALIDATION_ERROR", "message": "Settings validation failed", "errors": errors})
    except Exception as e:
        logger.error(f"Failed to update settings: {e}")
        raise HTTPException(status_code=500, detail={"error": True, "code": "INTERNAL_ERROR", "message": f"Failed to update settings: {str(e)}"})


@router.get("/api/mqtt/status")
async def get_mqtt_status() -> Dict[str, Any]:
    try:
        return mqtt_service.get_monitoring_status()
    except Exception as e:
        logger.error(f"Failed to get MQTT status: {e}")
        raise HTTPException(status_code=500, detail={"error": True, "code": "INTERNAL_ERROR", "message": f"Failed to get MQTT status: {str(e)}"})
