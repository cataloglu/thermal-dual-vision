/**
 * API types for Smart Motion Detector v2
 */

export interface DetectionConfig {
  model: 'yolov8n-person' | 'yolov8s-person' | 'yolov9t' | 'yolov9s';
  confidence_threshold: number;
  thermal_confidence_threshold: number;
  nms_iou_threshold: number;
  inference_resolution: [number, number];
  inference_fps: number;
  aspect_ratio_preset?: 'person' | 'thermal_person' | 'custom';
  aspect_ratio_min: number;
  aspect_ratio_max: number;
  enable_tracking: boolean;
}

export interface MotionConfig {
  algorithm?: 'frame_diff' | 'mog2' | 'knn';
  sensitivity: number;
  min_area: number;
  cooldown_seconds: number;
  presets: {
    thermal_recommended: {
      sensitivity: number;
      min_area: number;
      cooldown_seconds: number;
    };
    color_recommended?: {
      sensitivity: number;
      min_area: number;
      cooldown_seconds: number;
    };
  };
}

export interface ThermalConfig {
  enable_enhancement: boolean;
  enhancement_method: 'clahe' | 'histogram' | 'none';
  clahe_clip_limit: number;
  clahe_tile_size: [number, number];
  gaussian_blur_kernel: [number, number];
}

export interface StreamConfig {
  protocol: 'tcp' | 'udp';
  capture_backend: 'auto' | 'opencv' | 'ffmpeg';
  buffer_size: number;
  reconnect_delay_seconds: number;
  max_reconnect_attempts: number;
  read_failure_threshold: number;
  read_failure_timeout_seconds: number;
}

export interface LiveConfig {
  output_mode: 'mjpeg' | 'webrtc';
  webrtc: {
    enabled: boolean;
    go2rtc_url: string;
  };
}

export interface RecordConfig {
  enabled: boolean;
  retention_days: number;
  record_segments_seconds: number;
  disk_limit_percent: number;
  cleanup_policy: string;
  delete_order: string[];
}

export interface EventConfig {
  cooldown_seconds: number;
  prebuffer_seconds: number;
  postbuffer_seconds: number;
  record_fps: number;
  frame_buffer_size: number;
  frame_interval: number;
  min_event_duration: number;
}

export interface MediaConfig {
  retention_days: number;
  cleanup_interval_hours: number;
  disk_limit_percent: number;
}

export interface AIConfig {
  enabled: boolean;
  api_key: string;
  model: string;
  prompt_template: 'default' | 'custom';
  custom_prompt: string;
  language: 'tr' | 'en';
  max_tokens: number;
  timeout: number;
  temperature: number;
}

export interface TelegramConfig {
  enabled: boolean;
  bot_token: string;
  chat_ids: string[];
  rate_limit_seconds: number;
  send_images: boolean;
  video_speed: number;
  cooldown_seconds: number;
  max_messages_per_min: number;
  snapshot_quality: number;
}

export interface MqttConfig {
  enabled: boolean;
  host: string;
  port: number;
  username?: string;
  password?: string;
  topic_prefix: string;
}

export interface AppearanceConfig {
  theme: 'slate' | 'carbon' | 'pure-black' | 'matrix';
  language: 'tr' | 'en';
}

export interface PerformanceConfig {
  worker_mode: 'threading' | 'multiprocessing';
  enable_metrics: boolean;
  metrics_port: number;
}

export interface Settings {
  detection: DetectionConfig;
  motion: MotionConfig;
  thermal: ThermalConfig;
  stream: StreamConfig;
  live: LiveConfig;
  record: RecordConfig;
  event: EventConfig;
  media: MediaConfig;
  ai: AIConfig;
  telegram: TelegramConfig;
  performance: PerformanceConfig;
  mqtt: MqttConfig;
  appearance: AppearanceConfig;
}

export interface CameraTestRequest {
  type: 'color' | 'thermal' | 'dual';
  rtsp_url_thermal?: string;
  rtsp_url_color?: string;
  channel_thermal?: number;
  channel_color?: number;
}

export interface CameraTestResponse {
  success: boolean;
  snapshot_base64?: string;
  latency_ms?: number;
  error_reason?: string;
}

export interface Zone {
  id: string;
  name: string;
  enabled: boolean;
  mode: 'person' | 'motion' | 'both';
  polygon: Array<[number, number]>;
}
