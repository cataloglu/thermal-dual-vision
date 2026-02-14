"""
Prometheus metrics service for Smart Motion Detector v2.

Exports performance metrics for monitoring and alerting.
"""
import logging
from typing import Optional

try:
    from prometheus_client import Counter, Gauge, Histogram, start_http_server, REGISTRY
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


logger = logging.getLogger(__name__)


class MetricsService:
    """
    Prometheus metrics service.
    
    Tracks detection performance, system metrics, and stream health.
    """
    
    def __init__(self):
        """Initialize metrics service."""
        self.enabled = False
        self.server_started = False
        
        if not PROMETHEUS_AVAILABLE:
            logger.warning("Prometheus client not available, metrics disabled")
            logger.warning("Install with: pip install prometheus-client")
            return
        
        # Detection metrics
        self.events_total = Counter(
            'thermal_vision_events_total',
            'Total number of detection events',
            ['camera_id', 'event_type']
        )
        
        self.detections_total = Counter(
            'thermal_vision_detections_total',
            'Total number of detections (before filtering)',
            ['camera_id']
        )
        
        self.false_positives_total = Counter(
            'thermal_vision_false_positives_total',
            'Total number of filtered false positives',
            ['camera_id', 'filter_type']
        )
        
        self.detection_confidence = Histogram(
            'thermal_vision_detection_confidence',
            'Detection confidence distribution',
            ['camera_id'],
            buckets=[0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        )
        
        # Performance metrics
        self.inference_latency = Histogram(
            'thermal_vision_inference_latency_seconds',
            'YOLO inference latency',
            ['camera_id', 'model'],
            buckets=[0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 1.0, 2.0]
        )
        
        self.preprocessing_latency = Histogram(
            'thermal_vision_preprocessing_latency_seconds',
            'Frame preprocessing latency (CLAHE)',
            ['camera_id', 'method'],
            buckets=[0.001, 0.005, 0.01, 0.02, 0.05, 0.1]
        )
        
        self.fps = Gauge(
            'thermal_vision_fps',
            'Frames per second',
            ['camera_id']
        )
        
        # System metrics
        self.cpu_usage = Gauge(
            'thermal_vision_cpu_usage_percent',
            'CPU usage percentage',
            ['camera_id']
        )
        
        self.memory_usage = Gauge(
            'thermal_vision_memory_usage_bytes',
            'Memory usage in bytes',
            ['camera_id']
        )
        
        # Stream metrics
        self.stream_frames_read = Counter(
            'thermal_vision_stream_frames_read_total',
            'Total frames read from stream',
            ['camera_id', 'backend']
        )
        
        self.stream_frames_failed = Counter(
            'thermal_vision_stream_frames_failed_total',
            'Total frames failed to read',
            ['camera_id', 'backend']
        )
        
        self.stream_reconnects = Counter(
            'thermal_vision_stream_reconnects_total',
            'Total stream reconnections',
            ['camera_id', 'reason']
        )
        
        self.camera_status = Gauge(
            'thermal_vision_camera_status',
            'Camera status (1=connected, 0=down)',
            ['camera_id']
        )
        
        logger.info("MetricsService initialized (Prometheus available)")
    
    def start_server(self, port: int = 9090) -> None:
        """
        Start Prometheus HTTP server.
        
        Args:
            port: HTTP port for metrics endpoint
        """
        if not PROMETHEUS_AVAILABLE:
            logger.warning("Cannot start metrics server (Prometheus not available)")
            return
        
        if self.server_started:
            logger.warning("Metrics server already started")
            return
        
        try:
            start_http_server(port)
            self.server_started = True
            self.enabled = True
            logger.info(f"Prometheus metrics server started on port {port}")
            logger.info(f"Metrics endpoint: http://localhost:{port}/metrics")
        except Exception as e:
            logger.error(f"Failed to start metrics server: {e}")
    
    def record_event(self, camera_id: str, event_type: str = "person") -> None:
        """Record detection event."""
        if self.enabled:
            self.events_total.labels(camera_id=camera_id, event_type=event_type).inc()
    
    def record_detection(
        self,
        camera_id: str,
        confidence: float,
        filtered: bool = False,
        filter_type: Optional[str] = None
    ) -> None:
        """Record detection (before/after filtering)."""
        if self.enabled:
            self.detections_total.labels(camera_id=camera_id).inc()
            self.detection_confidence.labels(camera_id=camera_id).observe(confidence)
            
            if filtered and filter_type:
                self.false_positives_total.labels(
                    camera_id=camera_id,
                    filter_type=filter_type
                ).inc()
    
    def record_inference_latency(
        self,
        camera_id: str,
        model: str,
        latency_seconds: float
    ) -> None:
        """Record inference latency."""
        if self.enabled:
            self.inference_latency.labels(
                camera_id=camera_id,
                model=model
            ).observe(latency_seconds)
    
    def record_preprocessing_latency(
        self,
        camera_id: str,
        method: str,
        latency_seconds: float
    ) -> None:
        """Record preprocessing latency."""
        if self.enabled:
            self.preprocessing_latency.labels(
                camera_id=camera_id,
                method=method
            ).observe(latency_seconds)
    
    def set_fps(self, camera_id: str, fps: float) -> None:
        """Set current FPS."""
        if self.enabled:
            self.fps.labels(camera_id=camera_id).set(fps)
    
    def set_cpu_usage(self, camera_id: str, cpu_percent: float) -> None:
        """Set CPU usage percentage."""
        if self.enabled:
            self.cpu_usage.labels(camera_id=camera_id).set(cpu_percent)
    
    def set_memory_usage(self, camera_id: str, memory_bytes: int) -> None:
        """Set memory usage."""
        if self.enabled:
            self.memory_usage.labels(camera_id=camera_id).set(memory_bytes)
    
    def record_stream_frame_read(self, camera_id: str, backend: str = "opencv") -> None:
        """Record successful frame read."""
        if self.enabled:
            self.stream_frames_read.labels(camera_id=camera_id, backend=backend).inc()
    
    def record_stream_frame_failed(self, camera_id: str, backend: str = "opencv") -> None:
        """Record failed frame read."""
        if self.enabled:
            self.stream_frames_failed.labels(camera_id=camera_id, backend=backend).inc()
    
    def record_stream_reconnect(self, camera_id: str, reason: str = "unknown") -> None:
        """Record stream reconnection."""
        if self.enabled:
            self.stream_reconnects.labels(camera_id=camera_id, reason=reason).inc()
    
    def set_camera_status(self, camera_id: str, connected: bool) -> None:
        """Set camera connection status."""
        if self.enabled:
            self.camera_status.labels(camera_id=camera_id).set(1 if connected else 0)


# Global singleton instance
_metrics_service: Optional[MetricsService] = None


def get_metrics_service() -> MetricsService:
    """
    Get or create the global metrics service instance.
    
    Returns:
        MetricsService: Global service instance
    """
    global _metrics_service
    if _metrics_service is None:
        _metrics_service = MetricsService()
    return _metrics_service
