import logging
from pathlib import Path
from typing import Any, Dict, Optional

import psutil
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import Camera
from app.db.session import get_session
from app.dependencies import (
    ai_service,
    detector_worker,
    event_service,
    logs_service,
    media_service,
    settings_service,
    telegram_service,
)
from app.services.ai_probe import test_openai_connection
from app.services.time_utils import get_detection_source
from app.services.video_analyzer import analyze_video as run_video_analysis
from app.utils.paths import DATA_DIR
from app.version import __version__
from telegram import Bot

logger = logging.getLogger(__name__)
router = APIRouter()


def get_worker_info() -> Dict[str, Any]:
    """Current worker mode and (for multiprocessing) process count."""
    try:
        cfg = settings_service.load_config()
        mode = getattr(getattr(cfg, "performance", None), "worker_mode", "threading") or "threading"
    except Exception:
        mode = "threading"
    out: Dict[str, Any] = {"mode": mode}
    if mode == "multiprocessing" and hasattr(detector_worker, "processes"):
        out["process_count"] = len(detector_worker.processes)
        out["pids"] = [p.pid for p in detector_worker.processes.values() if p.pid is not None]
    return out


class VideoAnalyzeRequest(BaseModel):
    event_id: Optional[str] = None
    path: Optional[str] = None


class AiEventTestRequest(BaseModel):
    event_id: str


class TelegramTestRequest(BaseModel):
    bot_token: Optional[str] = None
    chat_ids: list
    event_id: Optional[str] = None


@router.get("/api/logs")
async def get_logs(lines: int = 200) -> Dict[str, Any]:
    try:
        log_lines = logs_service.get_logs(lines)
        return {"lines": log_lines, "count": len(log_lines)}
    except Exception as e:
        logger.error(f"Failed to get logs: {e}")
        raise HTTPException(status_code=500, detail={"error": True, "code": "INTERNAL_ERROR", "message": f"Failed to retrieve logs: {str(e)}"})


@router.post("/api/logs/clear")
async def clear_logs() -> Dict[str, Any]:
    try:
        cleared = logs_service.clear_logs()
        return {"success": True, "cleared": cleared}
    except Exception as e:
        logger.error("Failed to clear logs: %s", e)
        raise HTTPException(status_code=500, detail={"error": True, "code": "INTERNAL_ERROR", "message": f"Failed to clear logs: {str(e)}"})


@router.get("/api/system/info")
async def get_system_info() -> Dict[str, Any]:
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        addon_data_gb = 0.0
        try:
            total_bytes = sum(p.stat().st_size for p in DATA_DIR.rglob("*") if p.is_file())
            addon_data_gb = round(total_bytes / (1024 ** 3), 2)
        except Exception:
            pass
        return {
            "cpu": {"percent": round(cpu_percent, 1)},
            "memory": {
                "used_gb": round(memory.used / (1024 ** 3), 2),
                "total_gb": round(memory.total / (1024 ** 3), 2),
                "percent": round(memory.percent, 1),
            },
            "disk": {
                "used_gb": round(disk.used / (1024 ** 3), 2),
                "total_gb": round(disk.total / (1024 ** 3), 2),
                "percent": round(disk.percent, 1),
            },
            "addon_data_gb": addon_data_gb,
            "version": __version__,
            "worker": get_worker_info(),
        }
    except Exception as e:
        logger.error(f"Failed to get system info: {e}")
        raise HTTPException(status_code=500, detail={"error": True, "code": "INTERNAL_ERROR", "message": f"Failed to retrieve system info: {str(e)}"})


@router.post("/api/video/analyze")
async def analyze_video_endpoint(request: VideoAnalyzeRequest) -> Dict[str, Any]:
    video_path = None
    if request.event_id:
        media_path = media_service.get_media_path(request.event_id, "mp4")
        if not media_path or not media_path.exists():
            raise HTTPException(status_code=404, detail={"error": True, "code": "VIDEO_NOT_FOUND", "message": f"MP4 not found for event {request.event_id}"})
        video_path = str(media_path)
    elif request.path:
        p = Path(request.path)
        if not p.exists() or not p.is_file():
            raise HTTPException(status_code=400, detail={"error": True, "code": "INVALID_PATH", "message": f"File not found: {request.path}"})
        video_path = str(p)
    else:
        raise HTTPException(status_code=400, detail={"error": True, "code": "MISSING_PARAMS", "message": "Provide event_id or path"})
    result = run_video_analysis(video_path)
    if result is None:
        raise HTTPException(status_code=500, detail={"error": True, "code": "ANALYSIS_FAILED", "message": "Could not open or analyze video"})
    return result


@router.post("/api/ai/test")
async def test_ai(request: Dict[str, Any]) -> Dict[str, Any]:
    try:
        api_key = request.get("api_key")
        model = request.get("model", "gpt-4o")
        if not api_key:
            raise HTTPException(status_code=400, detail={"error": True, "code": "VALIDATION_ERROR", "message": "api_key is required"})
        result = await test_openai_connection(api_key, model)
        if not result["success"]:
            raise HTTPException(status_code=500, detail={"error": True, "code": "AI_TEST_FAILED", "message": result["message"]})
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI test failed: {e}")
        raise HTTPException(status_code=500, detail={"error": True, "code": "INTERNAL_ERROR", "message": f"AI test failed: {str(e)}"})


@router.post("/api/ai/test-event")
async def test_ai_event(request: AiEventTestRequest, db=Depends(get_session)) -> Dict[str, Any]:
    try:
        config = settings_service.load_config()
        if not config.ai.enabled:
            raise HTTPException(status_code=400, detail={"error": True, "code": "AI_DISABLED", "message": "AI is disabled"})
        if not config.ai.api_key or config.ai.api_key == "***REDACTED***":
            raise HTTPException(status_code=400, detail={"error": True, "code": "NO_API_KEY", "message": "API key is required"})

        event = event_service.get_event_by_id(db=db, event_id=request.event_id)
        if not event:
            raise HTTPException(status_code=404, detail={"error": True, "code": "EVENT_NOT_FOUND", "message": f"Event with id {request.event_id} not found"})

        camera = db.query(Camera).filter(Camera.id == event.camera_id).first()
        if not camera:
            raise HTTPException(status_code=404, detail={"error": True, "code": "CAMERA_NOT_FOUND", "message": f"Camera with id {event.camera_id} not found"})

        collage_path = media_service.get_media_path(event.id, "collage")
        if not collage_path or not collage_path.exists():
            raise HTTPException(status_code=400, detail={"error": True, "code": "COLLAGE_NOT_FOUND", "message": "Event collage not found"})

        detection_source = get_detection_source(camera.detection_source.value)
        camera_payload = {
            "id": camera.id, "name": camera.name,
            "type": camera.type.value if camera.type else None,
            "detection_source": detection_source,
            "use_custom_prompt": False, "ai_prompt_override": None,
        }
        event_payload = {
            "id": event.id, "camera_id": event.camera_id,
            "timestamp": event.timestamp.isoformat() + "Z",
            "confidence": event.confidence,
        }
        prompt = ai_service._get_prompt_for_event(event_payload, camera_payload)
        summary = await ai_service.analyze_event(event_payload, collage_path, camera_payload)
        return {
            "success": bool(summary), "event_id": event.id, "camera_id": event.camera_id,
            "camera_type": camera_payload["type"], "detection_source": detection_source,
            "prompt": prompt, "summary": summary, "model": config.ai.model,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI event test failed: {e}")
        raise HTTPException(status_code=500, detail={"error": True, "code": "INTERNAL_ERROR", "message": f"AI event test failed: {str(e)}"})


@router.post("/api/telegram/test")
async def test_telegram(request: TelegramTestRequest, db=Depends(get_session)) -> Dict[str, Any]:
    try:
        bot_token = request.bot_token
        chat_ids = request.chat_ids
        if not bot_token or bot_token == "***REDACTED***":
            config = settings_service.load_config()
            bot_token = config.telegram.bot_token
        if not bot_token or bot_token == "***REDACTED***":
            raise HTTPException(status_code=400, detail={"error": True, "code": "VALIDATION_ERROR", "message": "bot_token is required"})
        if not chat_ids:
            raise HTTPException(status_code=400, detail={"error": True, "code": "VALIDATION_ERROR", "message": "chat_ids is required"})

        from app.db.models import Event
        event = None
        if request.event_id:
            event = event_service.get_event_by_id(db=db, event_id=request.event_id)
        if not event:
            event = db.query(Event).order_by(Event.timestamp.desc()).first()

        if event:
            camera_name = "Test Camera"
            camera = db.query(Camera).filter(Camera.id == event.camera_id).first()
            if camera and camera.name:
                camera_name = camera.name
            message = f"🧪 Telegram test\n📹 {camera_name}"
            collage_path = media_service.get_media_path(event.id, "collage")
            mp4_path = media_service.get_media_path(event.id, "mp4")
            bot = Bot(token=bot_token)
            for chat_id in chat_ids:
                if collage_path and collage_path.exists():
                    with open(collage_path, "rb") as photo:
                        await bot.send_photo(chat_id=chat_id, photo=photo, caption=message)
                else:
                    await bot.send_message(chat_id=chat_id, text=message)
                if mp4_path and mp4_path.exists():
                    with open(mp4_path, "rb") as video:
                        await bot.send_video(chat_id=chat_id, video=video, caption="🎥 Event Video", supports_streaming=True)
            return {"success": True, "message": "Telegram test message sent"}

        result = await telegram_service.test_connection(bot_token, chat_ids)
        if not result["success"]:
            raise HTTPException(status_code=500, detail={"error": True, "code": "TELEGRAM_TEST_FAILED", "message": result["error_reason"]})
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Telegram test failed: {e}")
        raise HTTPException(status_code=500, detail={"error": True, "code": "INTERNAL_ERROR", "message": f"Telegram test failed: {str(e)}"})
