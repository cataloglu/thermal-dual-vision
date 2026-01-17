"""API routes for Smart Motion Detector web server."""

import os
import time
from datetime import datetime
from typing import Dict, Any

from flask import Blueprint, jsonify, request


# Create Blueprint for API routes
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Track server start time for uptime calculation
SERVER_START_TIME = time.time()


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
