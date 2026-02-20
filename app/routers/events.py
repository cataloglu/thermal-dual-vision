import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response, StreamingResponse
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.db.models import Camera, Event
from app.db.session import get_session
from app.dependencies import event_service, media_service, retention_worker

logger = logging.getLogger(__name__)
router = APIRouter()


def _resolve_media_urls(event, ingress_path: str = "") -> Dict[str, Optional[str]]:
    collage_path = media_service.get_media_path(event.id, "collage")
    gif_path = media_service.get_media_path(event.id, "gif")
    mp4_path = media_service.get_media_path(event.id, "mp4")
    prefix = ingress_path.rstrip("/") if ingress_path else ""
    base_collage = event.collage_url or f"/api/events/{event.id}/collage"
    base_gif = event.gif_url or f"/api/events/{event.id}/preview.gif"
    base_mp4 = event.mp4_url or f"/api/events/{event.id}/timelapse.mp4"
    collage_url = f"{prefix}{base_collage}" if prefix else base_collage
    gif_url = f"{prefix}{base_gif}" if prefix else base_gif
    mp4_url = f"{prefix}{base_mp4}" if prefix else base_mp4
    return {
        "collage_url": collage_url if collage_path and collage_path.exists() else None,
        "gif_url": gif_url if gif_path and gif_path.exists() else None,
        "mp4_url": mp4_url if mp4_path and mp4_path.exists() else None,
    }


@router.get("/api/events")
async def get_events(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    camera_id: Optional[str] = Query(None),
    date: Optional[datetime] = Query(None),
    confidence: Optional[float] = Query(None, ge=0.0, le=1.0),
    rejected: Optional[bool] = Query(None),
    db: Session = Depends(get_session),
) -> Dict[str, Any]:
    try:
        result = event_service.get_events(
            db=db,
            page=page,
            page_size=page_size,
            camera_id=camera_id,
            date_filter=date,
            min_confidence=confidence,
            rejected_only=rejected,
        )
        ingress_path = request.headers.get("X-Ingress-Path", "")
        events_list = []
        for event in result["events"]:
            media_urls = _resolve_media_urls(event, ingress_path)
            events_list.append({
                "id": event.id,
                "camera_id": event.camera_id,
                "timestamp": event.timestamp.isoformat() + "Z",
                "confidence": event.confidence,
                "event_type": event.event_type,
                "summary": event.summary,
                "collage_url": media_urls["collage_url"],
                "gif_url": media_urls["gif_url"],
                "mp4_url": media_urls["mp4_url"],
                "rejected_by_ai": getattr(event, "rejected_by_ai", False),
            })
        return {"page": result["page"], "page_size": result["page_size"], "total": result["total"], "events": events_list}
    except Exception as e:
        logger.error(f"Failed to get events: {e}")
        raise HTTPException(status_code=500, detail={"error": True, "code": "INTERNAL_ERROR", "message": f"Failed to retrieve events: {str(e)}"})


@router.get("/api/events/{event_id}")
async def get_event(request: Request, event_id: str, db: Session = Depends(get_session)) -> Dict[str, Any]:
    try:
        event = event_service.get_event_by_id(db=db, event_id=event_id)
        if not event:
            raise HTTPException(status_code=404, detail={"error": True, "code": "EVENT_NOT_FOUND", "message": f"Event with id {event_id} not found"})
        ingress_path = request.headers.get("X-Ingress-Path", "")
        media_urls = _resolve_media_urls(event, ingress_path)
        return {
            "id": event.id,
            "camera_id": event.camera_id,
            "timestamp": event.timestamp.isoformat() + "Z",
            "confidence": event.confidence,
            "event_type": event.event_type,
            "summary": event.summary,
            "ai": {"enabled": event.ai_enabled, "reason": event.ai_reason, "text": event.summary},
            "media": {"collage_url": media_urls["collage_url"], "gif_url": media_urls["gif_url"], "mp4_url": media_urls["mp4_url"]},
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get event {event_id}: {e}")
        raise HTTPException(status_code=500, detail={"error": True, "code": "INTERNAL_ERROR", "message": f"Failed to retrieve event: {str(e)}"})


@router.delete("/api/events/{event_id}")
async def delete_event(event_id: str, db: Session = Depends(get_session)) -> Dict[str, Any]:
    try:
        deleted = event_service.delete_event(db=db, event_id=event_id)
        if not deleted:
            raise HTTPException(status_code=404, detail={"error": True, "code": "EVENT_NOT_FOUND", "message": f"Event with id {event_id} not found"})
        return {"deleted": True, "id": event_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete event {event_id}: {e}")
        raise HTTPException(status_code=500, detail={"error": True, "code": "INTERNAL_ERROR", "message": f"Failed to delete event: {str(e)}"})


@router.post("/api/events/bulk-delete")
async def bulk_delete_events(request: Dict[str, Any], db: Session = Depends(get_session)) -> Dict[str, Any]:
    try:
        event_ids = request.get("event_ids", [])
        if not event_ids:
            raise HTTPException(status_code=400, detail={"error": True, "code": "VALIDATION_ERROR", "message": "event_ids is required"})
        deleted_count = 0
        failed_ids = []
        for event_id in event_ids:
            try:
                retention_worker.delete_event_media(event_id)
                if event_service.delete_event(db=db, event_id=event_id):
                    deleted_count += 1
                else:
                    failed_ids.append(event_id)
            except Exception as e:
                logger.error(f"Failed to delete event {event_id}: {e}")
                failed_ids.append(event_id)
        return {"deleted_count": deleted_count, "failed_ids": failed_ids}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bulk delete failed: {e}")
        raise HTTPException(status_code=500, detail={"error": True, "code": "INTERNAL_ERROR", "message": f"Bulk delete failed: {str(e)}"})


@router.post("/api/events/clear")
async def clear_events(request: Dict[str, Any], db: Session = Depends(get_session)) -> Dict[str, Any]:
    try:
        camera_id = request.get("camera_id")
        date_raw = request.get("date")
        min_confidence = request.get("min_confidence")
        date_filter = None
        if date_raw:
            try:
                date_filter = datetime.fromisoformat(date_raw).date()
            except Exception:
                raise HTTPException(status_code=400, detail={"error": True, "code": "VALIDATION_ERROR", "message": "Invalid date format. Use YYYY-MM-DD."})

        query = db.query(Event)
        filters = []
        if camera_id:
            filters.append(Event.camera_id == camera_id)
        if date_filter:
            start_of_day = datetime.combine(date_filter, datetime.min.time())
            end_of_day = datetime.combine(date_filter, datetime.max.time())
            filters.append(and_(Event.timestamp >= start_of_day, Event.timestamp <= end_of_day))
        if min_confidence is not None:
            try:
                filters.append(Event.confidence >= float(min_confidence))
            except Exception:
                raise HTTPException(status_code=400, detail={"error": True, "code": "VALIDATION_ERROR", "message": "min_confidence must be a number."})
        if filters:
            query = query.filter(and_(*filters))

        events = query.all()
        deleted_count = 0
        for event in events:
            try:
                retention_worker.delete_event_media(event.id)
                db.delete(event)
                deleted_count += 1
            except Exception as e:
                logger.error("Failed to delete event %s: %s", event.id, e)
        db.commit()
        return {"deleted_count": deleted_count}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clear events: {e}")
        raise HTTPException(status_code=500, detail={"error": True, "code": "INTERNAL_ERROR", "message": f"Failed to clear events: {str(e)}"})


@router.get("/api/events/{event_id}/collage")
async def get_event_collage(event_id: str) -> FileResponse:
    try:
        media_path = media_service.get_media_path(event_id, "collage")
        if not media_path or not media_path.exists():
            raise HTTPException(status_code=404, detail={"error": True, "code": "MEDIA_NOT_FOUND", "message": f"Collage not found for event {event_id}"})
        return FileResponse(path=str(media_path), media_type="image/jpeg", filename=f"event-{event_id}-collage.jpg", content_disposition_type="inline")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get collage for event {event_id}: {e}")
        raise HTTPException(status_code=500, detail={"error": True, "code": "INTERNAL_ERROR", "message": f"Failed to retrieve collage: {str(e)}"})


@router.get("/api/events/{event_id}/preview.gif")
async def get_event_gif(event_id: str) -> FileResponse:
    try:
        media_path = media_service.get_media_path(event_id, "gif")
        if not media_path or not media_path.exists():
            raise HTTPException(status_code=404, detail={"error": True, "code": "MEDIA_NOT_FOUND", "message": f"GIF not found for event {event_id}"})
        return FileResponse(path=str(media_path), media_type="image/gif", filename=f"event-{event_id}-preview.gif", content_disposition_type="inline")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get GIF for event {event_id}: {e}")
        raise HTTPException(status_code=500, detail={"error": True, "code": "INTERNAL_ERROR", "message": f"Failed to retrieve GIF: {str(e)}"})


@router.get("/api/events/{event_id}/timelapse.mp4")
async def get_event_mp4(event_id: str, request: Request) -> Response:
    try:
        media_path = media_service.get_media_path(event_id, "mp4")
        if not media_path or not media_path.exists():
            raise HTTPException(status_code=404, detail={"error": True, "code": "MEDIA_NOT_FOUND", "message": f"MP4 not found for event {event_id}"})

        file_size = os.path.getsize(media_path)
        range_header = request.headers.get("Range")

        if range_header and range_header.startswith("bytes="):
            try:
                ranges = range_header[6:].split("-")
                start = int(ranges[0]) if ranges[0] else 0
                end = int(ranges[1]) if len(ranges) > 1 and ranges[1] else file_size - 1
                end = min(end, file_size - 1)
                chunk_size = end - start + 1

                def _iter_file():
                    with open(media_path, "rb") as f:
                        f.seek(start)
                        remaining = chunk_size
                        while remaining > 0:
                            data = f.read(min(65536, remaining))
                            if not data:
                                break
                            remaining -= len(data)
                            yield data

                return StreamingResponse(
                    _iter_file(),
                    status_code=206,
                    media_type="video/mp4",
                    headers={
                        "Content-Range": f"bytes {start}-{end}/{file_size}",
                        "Accept-Ranges": "bytes",
                        "Content-Length": str(chunk_size),
                        "Content-Disposition": f'inline; filename="event-{event_id}-timelapse.mp4"',
                    },
                )
            except (ValueError, IndexError):
                pass  # Fall through to full response

        return FileResponse(
            path=str(media_path),
            media_type="video/mp4",
            filename=f"event-{event_id}-timelapse.mp4",
            content_disposition_type="inline",
            headers={"Accept-Ranges": "bytes", "Content-Length": str(file_size)},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get MP4 for event {event_id}: {e}")
        raise HTTPException(status_code=500, detail={"error": True, "code": "INTERNAL_ERROR", "message": f"Failed to retrieve MP4: {str(e)}"})
