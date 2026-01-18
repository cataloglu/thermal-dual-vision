"""API routes for Smart Motion Detector web server."""

import io
import os
import time
from dataclasses import asdict
from datetime import datetime

from flask import Blueprint, jsonify, request, send_file, Response

from src.config import Config
from src.screenshot_manager import ScreenshotManager
from src.utils import build_event_collage, build_event_video_bytes, encode_frame_to_bytes


# Create Blueprint for API routes
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Track server start time for uptime calculation
SERVER_START_TIME = time.time()

# Global configuration instance
_config = Config.from_env()

# Global screenshot manager instance
_screenshot_manager = ScreenshotManager(
    config=_config.screenshots,
    storage_path=os.getenv("SCREENSHOT_PATH", "/data/screenshots")
)


@api_bp.route('/status', methods=['GET'])
def get_status() -> tuple:
    """
    Get system status.

    Returns:
        JSON response with system status and HTTP 200
    """
    uptime_seconds = int(time.time() - SERVER_START_TIME)
    hours = uptime_seconds // 3600
    minutes = (uptime_seconds % 3600) // 60
    seconds = uptime_seconds % 60

    status_data = {
        'status': 'running',
        'service': 'smart-motion-detector',
        'version': '1.0.0',
        'uptime': f"{hours}h {minutes}m {seconds}s",
        'uptime_seconds': uptime_seconds,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'components': {
            'web_server': 'ok',
            'camera': 'disconnected',
            'motion_detection': 'inactive',
            'mqtt': 'disconnected',
            'telegram': 'disabled'
        }
    }

    return jsonify(status_data), 200


@api_bp.route('/stats', methods=['GET'])
def get_stats() -> tuple:
    """
    Get system statistics.

    Returns:
        JSON response with statistics and HTTP 200
    """
    stats_data = {
        'detections': {
            'total': 0,
            'today': 0,
            'this_week': 0,
            'this_month': 0
        },
        'objects_detected': {
            'person': 0,
            'car': 0,
            'dog': 0,
            'cat': 0,
            'other': 0
        },
        'screenshots': {
            'total': 0,
            'storage_used_mb': 0,
            'oldest': None,
            'newest': None
        },
        'performance': {
            'avg_processing_time_ms': 0,
            'fps': 0,
            'dropped_frames': 0
        },
        'recent_events': [],
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }

    return jsonify(stats_data), 200


@api_bp.route('/config', methods=['GET'])
def get_config() -> tuple:
    """
    Get current configuration.

    Returns:
        JSON response with configuration and HTTP 200
    """
    try:
        config_dict = asdict(_config)
        # Mask sensitive values in response
        if config_dict.get('llm', {}).get('api_key'):
            config_dict['llm']['api_key'] = '***REDACTED***'
        if config_dict.get('mqtt', {}).get('password'):
            config_dict['mqtt']['password'] = '***REDACTED***'
        if config_dict.get('telegram', {}).get('bot_token'):
            config_dict['telegram']['bot_token'] = '***REDACTED***'

        return jsonify(config_dict), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/config', methods=['POST'])
def update_config() -> tuple:
    """
    Update configuration.

    Expects JSON body with configuration values to update.
    Only updates provided fields, leaves others unchanged.

    Returns:
        JSON response with updated configuration and HTTP 200, or error and HTTP 400/500
    """
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400

        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Update camera config
        if 'camera' in data:
            camera_data = data['camera']
            if 'url' in camera_data:
                _config.camera.url = str(camera_data['url'])
            if 'fps' in camera_data:
                _config.camera.fps = int(camera_data['fps'])
            if 'resolution' in camera_data:
                res = camera_data['resolution']
                if isinstance(res, (list, tuple)) and len(res) == 2:
                    _config.camera.resolution = tuple(res)

        # Update motion config
        if 'motion' in data:
            motion_data = data['motion']
            if 'sensitivity' in motion_data:
                _config.motion.sensitivity = int(motion_data['sensitivity'])
            if 'min_area' in motion_data:
                _config.motion.min_area = int(motion_data['min_area'])
            if 'cooldown_seconds' in motion_data:
                _config.motion.cooldown_seconds = int(motion_data['cooldown_seconds'])

        # Update YOLO config
        if 'yolo' in data:
            yolo_data = data['yolo']
            if 'model' in yolo_data:
                _config.yolo.model = str(yolo_data['model'])
            if 'confidence' in yolo_data:
                _config.yolo.confidence = float(yolo_data['confidence'])
            if 'classes' in yolo_data:
                _config.yolo.classes = list(yolo_data['classes'])

        # Update LLM config
        if 'llm' in data:
            llm_data = data['llm']
            if 'api_key' in llm_data:
                _config.llm.api_key = str(llm_data['api_key'])
            if 'model' in llm_data:
                _config.llm.model = str(llm_data['model'])
            if 'max_tokens' in llm_data:
                _config.llm.max_tokens = int(llm_data['max_tokens'])
            if 'timeout' in llm_data:
                _config.llm.timeout = int(llm_data['timeout'])

        # Update screenshot config
        if 'screenshots' in data:
            screenshot_data = data['screenshots']
            if 'window_seconds' in screenshot_data:
                _config.screenshots.window_seconds = int(screenshot_data['window_seconds'])
            if 'quality' in screenshot_data:
                _config.screenshots.quality = int(screenshot_data['quality'])
            if 'max_stored' in screenshot_data:
                _config.screenshots.max_stored = int(screenshot_data['max_stored'])
            if 'buffer_seconds' in screenshot_data:
                _config.screenshots.buffer_seconds = int(screenshot_data['buffer_seconds'])

        # Update MQTT config
        if 'mqtt' in data:
            mqtt_data = data['mqtt']
            if 'host' in mqtt_data:
                _config.mqtt.host = str(mqtt_data['host'])
            if 'port' in mqtt_data:
                _config.mqtt.port = int(mqtt_data['port'])
            if 'username' in mqtt_data:
                _config.mqtt.username = str(mqtt_data['username'])
            if 'password' in mqtt_data:
                _config.mqtt.password = str(mqtt_data['password'])
            if 'topic_prefix' in mqtt_data:
                _config.mqtt.topic_prefix = str(mqtt_data['topic_prefix'])
            if 'discovery' in mqtt_data:
                _config.mqtt.discovery = bool(mqtt_data['discovery'])
            if 'discovery_prefix' in mqtt_data:
                _config.mqtt.discovery_prefix = str(mqtt_data['discovery_prefix'])
            if 'qos' in mqtt_data:
                _config.mqtt.qos = int(mqtt_data['qos'])

        # Update Telegram config
        if 'telegram' in data:
            telegram_data = data['telegram']
            if 'enabled' in telegram_data:
                _config.telegram.enabled = bool(telegram_data['enabled'])
            if 'bot_token' in telegram_data:
                _config.telegram.bot_token = str(telegram_data['bot_token'])
            if 'chat_ids' in telegram_data:
                _config.telegram.chat_ids = list(telegram_data['chat_ids'])
            if 'rate_limit_seconds' in telegram_data:
                _config.telegram.rate_limit_seconds = int(telegram_data['rate_limit_seconds'])
            if 'video_speed' in telegram_data:
                _config.telegram.video_speed = int(telegram_data['video_speed'])

        # Update log level
        if 'log_level' in data:
            _config.log_level = str(data['log_level'])

        # Validate configuration
        errors = _config.validate()
        if errors:
            return jsonify({'error': 'Validation failed', 'details': errors}), 400

        # Return updated config with masked sensitive values
        config_dict = asdict(_config)
        if config_dict.get('llm', {}).get('api_key'):
            config_dict['llm']['api_key'] = '***REDACTED***'
        if config_dict.get('mqtt', {}).get('password'):
            config_dict['mqtt']['password'] = '***REDACTED***'
        if config_dict.get('telegram', {}).get('bot_token'):
            config_dict['telegram']['bot_token'] = '***REDACTED***'

        return jsonify(config_dict), 200

    except ValueError as e:
        return jsonify({'error': f'Invalid value: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/events', methods=['GET'])
def get_events() -> tuple:
    """
    Get events/detections history.

    Query Parameters:
        limit (int, optional): Maximum number of events to return

    Returns:
        JSON response with list of detection events and HTTP 200, or error and HTTP 400/500
    """
    try:
        # Get limit from query parameter
        limit_str = request.args.get('limit')
        limit = int(limit_str) if limit_str else None

        # Get all screenshots (each represents a detection event)
        screenshots = _screenshot_manager.list_all(limit=limit)

        # Convert to events format
        events_data = []
        for screenshot in screenshots:
            event = {
                'id': screenshot.id,
                'timestamp': screenshot.timestamp,
                'has_screenshots': {
                    'before': screenshot.has_before,
                    'early': screenshot.has_early,
                    'peak': screenshot.has_peak,
                    'late': screenshot.has_late,
                    'after': screenshot.has_after
                }
            }

            # Add analysis data if available
            if screenshot.analysis:
                event['detection'] = {
                    'real_motion': screenshot.analysis.get('gercek_hareket', False),
                    'confidence_score': screenshot.analysis.get('guven_skoru', 0.0),
                    'description': screenshot.analysis.get('degisiklik_aciklamasi', ''),
                    'detected_objects': screenshot.analysis.get('tespit_edilen_nesneler', []),
                    'threat_level': screenshot.analysis.get('tehdit_seviyesi', 'yok'),
                    'recommended_action': screenshot.analysis.get('onerilen_aksiyon', ''),
                    'detailed_analysis': screenshot.analysis.get('detayli_analiz', ''),
                    'processing_time': screenshot.analysis.get('processing_time', 0.0)
                }

            events_data.append(event)

        return jsonify({
            'events': events_data,
            'count': len(events_data),
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }), 200

    except ValueError as e:
        return jsonify({'error': f'Invalid parameter: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/screenshots', methods=['GET'])
def list_screenshots() -> tuple:
    """
    List all stored screenshots with metadata.

    Query Parameters:
        limit (int, optional): Maximum number of screenshots to return

    Returns:
        JSON response with list of screenshots and HTTP 200, or error and HTTP 500
    """
    try:
        # Get limit from query parameter
        limit_str = request.args.get('limit')
        limit = int(limit_str) if limit_str else None

        # Get all screenshots
        screenshots = _screenshot_manager.list_all(limit=limit)

        # Convert to JSON-serializable format
        screenshots_data = []
        for screenshot in screenshots:
            screenshot_dict = {
                'id': screenshot.id,
                'timestamp': screenshot.timestamp,
                'has_before': screenshot.has_before,
                'has_early': screenshot.has_early,
                'has_peak': screenshot.has_peak,
                'has_late': screenshot.has_late,
                'has_after': screenshot.has_after,
                'analysis': screenshot.analysis
            }
            screenshots_data.append(screenshot_dict)

        return jsonify({
            'screenshots': screenshots_data,
            'count': len(screenshots_data),
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }), 200

    except ValueError as e:
        return jsonify({'error': f'Invalid parameter: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/screenshots/<screenshot_id>', methods=['GET'])
def get_screenshot_metadata(screenshot_id: str) -> tuple:
    """
    Get metadata for a specific screenshot set.

    Args:
        screenshot_id: Screenshot set ID

    Returns:
        JSON response with screenshot metadata and HTTP 200,
        or error and HTTP 404/500
    """
    try:
        # Get metadata
        metadata = _screenshot_manager.get_metadata(screenshot_id)

        if metadata is None:
            return jsonify({'error': 'Screenshot not found'}), 404

        # Convert to JSON-serializable format
        metadata_dict = {
            'id': metadata.id,
            'timestamp': metadata.timestamp,
            'has_before': metadata.has_before,
            'has_early': metadata.has_early,
            'has_peak': metadata.has_peak,
            'has_late': metadata.has_late,
            'has_after': metadata.has_after,
            'analysis': metadata.analysis
        }

        return jsonify(metadata_dict), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/screenshots/<screenshot_id>/<image_type>', methods=['GET'])
def get_screenshot_image(screenshot_id: str, image_type: str) -> tuple:
    """
    Get a specific image from a screenshot set.

    Args:
        screenshot_id: Screenshot set ID
        image_type: Type of image ("before", "early", "peak", "late", or "after")

    Returns:
        Image file (JPEG) or error and HTTP 400/404/500
    """
    try:
        # Validate image type
        if image_type not in ['before', 'early', 'peak', 'late', 'after']:
            return jsonify({'error': 'Invalid image type. Must be "before", "early", "peak", "late", or "after"'}), 400

        # Get image path
        image_path = _screenshot_manager.get_image_path(screenshot_id, image_type)

        if image_path is None:
            return jsonify({'error': 'Image not found'}), 404

        # Send file
        return send_file(str(image_path), mimetype='image/jpeg'), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/screenshots/<screenshot_id>/collage', methods=['GET'])
def get_screenshot_collage(screenshot_id: str) -> tuple:
    """Get a collage image for a screenshot set."""
    try:
        screenshot_set = _screenshot_manager.get(screenshot_id)
        if screenshot_set is None:
            return jsonify({'error': 'Screenshot not found'}), 404

        frames = [
            screenshot_set.before,
            screenshot_set.early,
            screenshot_set.peak,
            screenshot_set.late,
            screenshot_set.after,
        ]
        collage = build_event_collage(
            frames=frames,
            labels=["before", "early", "peak", "late", "after"],
            camera_name="Camera",
            timestamp=screenshot_set.timestamp,
            is_thermal=False,
        )
        collage_bytes = encode_frame_to_bytes(collage, quality=_config.screenshots.quality)
        return send_file(io.BytesIO(collage_bytes), mimetype='image/jpeg'), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/screenshots/<screenshot_id>/clip.mp4', methods=['GET'])
def get_screenshot_clip(screenshot_id: str) -> tuple:
    """Get a short MP4 clip for a screenshot set."""
    try:
        screenshot_set = _screenshot_manager.get(screenshot_id)
        if screenshot_set is None:
            return jsonify({'error': 'Screenshot not found'}), 404

        frames = [
            screenshot_set.before,
            screenshot_set.early,
            screenshot_set.peak,
            screenshot_set.late,
            screenshot_set.after,
        ]
        video_bytes = build_event_video_bytes(
            frames=frames,
            camera_name="Camera",
            timestamp=screenshot_set.timestamp,
            event_type="motion_detected",
            speed_multiplier=_config.telegram.video_speed,
        )
        return send_file(io.BytesIO(video_bytes), mimetype='video/mp4'), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/screenshots/<screenshot_id>', methods=['DELETE'])
def delete_screenshot(screenshot_id: str) -> tuple:
    """
    Delete a screenshot set.

    Args:
        screenshot_id: Screenshot set ID

    Returns:
        JSON response with success message and HTTP 200,
        or error and HTTP 404/500
    """
    try:
        # Delete screenshot
        success = _screenshot_manager.delete(screenshot_id)

        if not success:
            return jsonify({'error': 'Screenshot not found or could not be deleted'}), 404

        return jsonify({
            'message': 'Screenshot deleted successfully',
            'id': screenshot_id,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


def generate_mjpeg_frames():
    """
    Generate MJPEG frames for streaming.

    Yields MJPEG frame boundaries with JPEG image data.
    Currently returns a placeholder as camera integration is pending.

    Yields:
        bytes: MJPEG multipart frame data
    """
    import cv2
    import numpy as np

    # Create a placeholder frame with text indicating camera is not available
    # In production, this would pull frames from the camera feed
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(
        frame,
        "Camera feed not available",
        (100, 240),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (255, 255, 255),
        2
    )

    # Encode frame to JPEG bytes
    frame_bytes = encode_frame_to_bytes(frame, quality=85)

    # Format as MJPEG multipart response
    # Each frame is sent with the multipart boundary and content type
    yield (b'--frame\r\n'
           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')


@api_bp.route('/stream', methods=['GET'])
def stream_video():
    """
    Stream live video feed as MJPEG.

    Returns MJPEG stream with multipart/x-mixed-replace content type.
    Currently returns a placeholder frame as camera integration is pending.

    Returns:
        Response with MJPEG stream and HTTP 200
    """
    return Response(
        generate_mjpeg_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )
