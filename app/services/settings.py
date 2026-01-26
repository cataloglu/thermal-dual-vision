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
    SECRET_FIELDS = ["api_key", "bot_token"]
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
        self._cache_ttl: float = 5.0  # Cache for 5 seconds
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
        result = base.copy()
        
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result

    def _sanitize_config_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize legacy config fields."""
        if not isinstance(data, dict):
            return data
        result = data.copy()
        record = result.get("record")
        if isinstance(record, dict):
            delete_order = record.get("delete_order")
            allowed = ["mp4", "collage"]
            if isinstance(delete_order, list):
                filtered: list[str] = []
                for item in delete_order:
                    item_str = str(item).lower()
                    if item_str in allowed and item_str not in filtered:
                        filtered.append(item_str)
                record["delete_order"] = filtered or allowed.copy()
            else:
                record["delete_order"] = allowed.copy()
            result["record"] = record
        return result
    
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
