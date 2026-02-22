"""
Settings service for Smart Motion Detector v2.

This service handles configuration file management including:
- Loading config from config.json
- Saving config to config.json
- Partial updates
- Secret masking
- File locking for concurrent access
- Default config generation
- In-memory caching for performance
"""
import copy
import json
import logging
import os
import time
from threading import Lock
from typing import Any, Dict, Optional

from pydantic import ValidationError

from app.models.config import AppConfig
from app.utils.paths import DATA_DIR


logger = logging.getLogger(__name__)


class SettingsService:
    """Service for managing application settings."""
    
    # Singleton instance
    _instance: Optional["SettingsService"] = None
    _lock = Lock()
    
    # Config file path
    CONFIG_FILE = DATA_DIR / "config.json"
    
    # Secrets to mask in responses
    SECRET_FIELDS = ["api_key", "bot_token", "password"]
    MASKED_VALUE = "***REDACTED***"
    
    def __new__(cls) -> "SettingsService":
        """Ensure singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        """Initialize settings service."""
        if self._initialized:
            return
        
        self._config: Optional[AppConfig] = None
        self._config_cache: Optional[AppConfig] = None
        self._cache_time: float = 0.0
        self._cache_ttl: float = 30.0  # Cache for 30 seconds
        self._file_lock = Lock()
        self._cache_lock = Lock()
        self._initialized = True
        
        # Ensure data directory exists
        self.CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info("SettingsService initialized with caching enabled")
    
    def load_config(self) -> AppConfig:
        """
        Load configuration from config.json with caching.
        
        If config file doesn't exist, creates it with default values.
        If config file is invalid, raises ValidationError.
        Uses in-memory cache to reduce disk I/O.
        
        Returns:
            AppConfig: Loaded configuration
            
        Raises:
            ValidationError: If config validation fails
            json.JSONDecodeError: If config file is invalid JSON
        """
        # Check cache first
        with self._cache_lock:
            now = time.time()
            if self._config_cache is not None and (now - self._cache_time) < self._cache_ttl:
                return self._config_cache
        
        # Cache miss or expired, load from file
        with self._file_lock:
            if not self.CONFIG_FILE.exists():
                logger.info(f"Config file not found at {self.CONFIG_FILE}, creating default config")
                self._config = AppConfig()
                self._save_config_internal(self._config)
                
                # Update cache
                with self._cache_lock:
                    self._config_cache = self._config
                    self._cache_time = time.time()
                
                return self._config
            
            try:
                with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)

                data = self._sanitize_config_dict(raw_data)
                self._config = AppConfig(**data)
                if data != raw_data:
                    self._save_config_internal(self._config)
                
                # Update cache
                with self._cache_lock:
                    self._config_cache = self._config
                    self._cache_time = time.time()
                
                logger.debug(f"Config loaded from disk and cached")
                return self._config
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in config file: {e}")
                raise
            except ValidationError as e:
                logger.error(f"Config validation failed: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error loading config: {e}")
                raise
    
    def save_config(self, config: AppConfig) -> None:
        """
        Save configuration to config.json and invalidate cache.
        
        Args:
            config: Configuration to save
            
        Raises:
            IOError: If file write fails
        """
        with self._file_lock:
            self._save_config_internal(config)
            self._config = config
            
            # Invalidate cache
            with self._cache_lock:
                self._config_cache = config
                self._cache_time = time.time()
    
    def _save_config_internal(self, config: AppConfig) -> None:
        """
        Internal method to save config without acquiring lock.
        
        Args:
            config: Configuration to save
        """
        try:
            # Convert to dict and write to file
            config_dict = config.model_dump()
            
            # Write to temp file first, then rename (atomic operation)
            temp_file = self.CONFIG_FILE.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
            
            # Atomic rename
            temp_file.replace(self.CONFIG_FILE)
            
            logger.info(f"Config saved successfully to {self.CONFIG_FILE}")
            
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            raise
    
    def get_settings(self) -> Dict[str, Any]:
        """
        Get current settings with secrets masked.
        
        Returns:
            Dict containing current settings with masked secrets
        """
        if self._config is None:
            self._config = self.load_config()
        
        config_dict = self._config.model_dump()
        return self._mask_secrets(config_dict)
    
    def update_settings(self, partial_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update settings with partial data.
        
        Only provided fields are updated. Nested updates are supported.
        Secrets are unmasked if they contain the masked value.
        
        Args:
            partial_data: Partial configuration data
            
        Returns:
            Dict containing updated settings with masked secrets
            
        Raises:
            ValidationError: If validation fails
        """
        if self._config is None:
            self._config = self.load_config()
        
        # Convert current config to dict
        current_dict = self._config.model_dump()
        
        # Deep merge partial data into current config
        merged_dict = self._deep_merge(current_dict, partial_data)
        merged_dict = self._sanitize_config_dict(merged_dict)
        merged_dict = self._restore_masked_secrets(current_dict, merged_dict)
        
        # Validate merged config
        try:
            new_config = AppConfig(**merged_dict)
        except ValidationError as e:
            logger.error(f"Config validation failed during update: {e}")
            raise
        
        # Save new config
        self.save_config(new_config)
        
        logger.info("Settings updated successfully")
        
        # Return masked config
        return self._mask_secrets(new_config.model_dump())
    
    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge two dictionaries.
        
        Args:
            base: Base dictionary
            update: Dictionary with updates
            
        Returns:
            Merged dictionary
        """
        result = copy.deepcopy(base)
        
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = copy.deepcopy(value)
        
        return result

    def _sanitize_config_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize legacy config fields."""
        if not isinstance(data, dict):
            return data
        result = copy.deepcopy(data)
        # Migrate thermal CLAHE tile size: 8x8 caused blockiness, 32x32 is smoother
        thermal = result.get("thermal")
        if isinstance(thermal, dict):
            tile = thermal.get("clahe_tile_size")
            if tile == [8, 8] or tile == (8, 8):
                thermal["clahe_tile_size"] = [32, 32]
                result["thermal"] = thermal
        # Migrate detection: revert aggressive 0.35/0.45 (caused zero detections on thermal)
        detection = result.get("detection")
        if isinstance(detection, dict):
            if detection.get("confidence_threshold") in (0.25, 0.35):
                detection["confidence_threshold"] = 0.30
            if detection.get("thermal_confidence_threshold") in (0.25, 0.45):
                detection["thermal_confidence_threshold"] = 0.35  # Thermal needs lower threshold
            result["detection"] = detection
        # Migrate motion defaults: align with tuned prefilter values
        motion = result.get("motion")
        if isinstance(motion, dict):
            # Product policy: always run adaptive global auto motion.
            motion["mode"] = "auto"
            if motion.get("auto_profile") not in {"low", "normal", "high"}:
                motion["auto_profile"] = "low"
            else:
                motion["auto_profile"] = "low"
            try:
                sensitivity = int(motion.get("sensitivity", 0))
                min_area = int(motion.get("min_area", 0))
                cooldown = int(motion.get("cooldown_seconds", 0))
            except Exception:
                sensitivity = min_area = cooldown = None
            if sensitivity == 7 and min_area == 500 and cooldown == 5:
                motion["sensitivity"] = 8
                motion["min_area"] = 450
                motion["cooldown_seconds"] = 6
            # Stable defaults to reduce motion spam on production installs.
            motion["algorithm"] = "mog2"
            motion["sensitivity"] = 4
            motion["min_area"] = 250
            motion["cooldown_seconds"] = 3
            motion["auto_update_seconds"] = 20
            motion["auto_min_area_floor"] = max(120, int(motion.get("auto_min_area_floor", 120) or 120))
            motion["auto_warmup_seconds"] = max(30, int(motion.get("auto_warmup_seconds", 45) or 45))

            floor = int(motion.get("auto_min_area_floor", 120) or 120)
            ceil = int(motion.get("auto_min_area_ceiling", 2500) or 2500)
            if floor > ceil:
                floor, ceil = ceil, floor
            motion["auto_min_area_floor"] = max(0, floor)
            motion["auto_min_area_ceiling"] = max(1, ceil)
            presets = motion.get("presets")
            if isinstance(presets, dict):
                thermal = presets.get("thermal_recommended")
                if isinstance(thermal, dict):
                    try:
                        t_sens = int(thermal.get("sensitivity", 0))
                        t_area = int(thermal.get("min_area", 0))
                        t_cd = int(thermal.get("cooldown_seconds", 0))
                    except Exception:
                        t_sens = t_area = t_cd = None
                    if t_sens == 8 and t_area == 450 and t_cd == 4:
                        thermal.update({"sensitivity": 9, "min_area": 350, "cooldown_seconds": 6})
                color = presets.get("color_recommended")
                if isinstance(color, dict):
                    try:
                        c_sens = int(color.get("sensitivity", 0))
                        c_area = int(color.get("min_area", 0))
                        c_cd = int(color.get("cooldown_seconds", 0))
                    except Exception:
                        c_sens = c_area = c_cd = None
                    if c_sens == 7 and c_area == 500 and c_cd == 5:
                        color.update({"sensitivity": 8, "min_area": 400, "cooldown_seconds": 6})
            result["motion"] = motion
        # Migrate event: ensure cooldown_seconds exists (do not override user value)
        event = result.get("event")
        if isinstance(event, dict):
            if event.get("cooldown_seconds") is None:
                legacy_cooldown = event.get("cooldown")
                event["cooldown_seconds"] = legacy_cooldown if legacy_cooldown is not None else 7
            # Production defaults to suppress short noise bursts.
            if float(event.get("min_event_duration", 0) or 0) < 1.5:
                event["min_event_duration"] = 1.5
            if int(event.get("cooldown_seconds", 0) or 0) < 3:
                event["cooldown_seconds"] = 3
            # prebuffer < 5 caused ~3 sec event videos (too few frames)
            pb = event.get("prebuffer_seconds")
            if pb is not None and float(pb) < 5.0:
                event["prebuffer_seconds"] = 5.0
            # Product policy: postbuffer is fixed at 2s (hidden from UI).
            event["postbuffer_seconds"] = 2.0
            result["event"] = event
        performance = result.get("performance")
        if isinstance(performance, dict):
            # Product policy: keep stable worker mode.
            performance["worker_mode"] = "threading"
            result["performance"] = performance
        record = result.get("record")
        if isinstance(record, dict):
            result["record"] = {"enabled": True}  # Sabit, parametre yok
        return result

    def _restore_masked_secrets(self, current: Any, merged: Any) -> Any:
        if isinstance(merged, dict) and isinstance(current, dict):
            restored: Dict[str, Any] = {}
            for key, value in merged.items():
                if isinstance(value, dict):
                    restored[key] = self._restore_masked_secrets(current.get(key, {}), value)
                elif key in self.SECRET_FIELDS and value == self.MASKED_VALUE:
                    restored[key] = current.get(key)
                else:
                    restored[key] = value
            return restored
        return merged
    
    def _mask_secrets(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively mask secret fields in configuration.
        
        Args:
            data: Configuration dictionary
            
        Returns:
            Dictionary with masked secrets
        """
        result = {}
        
        for key, value in data.items():
            if key in self.SECRET_FIELDS and value and value != self.MASKED_VALUE:
                # Mask non-empty secrets
                result[key] = self.MASKED_VALUE
            elif isinstance(value, dict):
                # Recursively mask nested dicts
                result[key] = self._mask_secrets(value)
            else:
                result[key] = value
        
        return result
    
    def get_default_config(self) -> Dict[str, Any]:
        """
        Get default configuration as dictionary.
        
        Returns:
            Dict containing default configuration
        """
        default_config = AppConfig()
        return default_config.model_dump()


# Global singleton instance
_settings_service: Optional[SettingsService] = None


def get_settings_service() -> SettingsService:
    """
    Get or create the global settings service instance.
    
    Returns:
        SettingsService: Global settings service instance
    """
    global _settings_service
    if _settings_service is None:
        _settings_service = SettingsService()
    return _settings_service
