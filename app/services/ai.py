"""
AI service for Smart Motion Detector v2.

Handles OpenAI Vision API integration for event analysis.
"""
import base64
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from openai import OpenAI

from app.services.settings import get_settings_service


logger = logging.getLogger(__name__)


# Prompt templates
THERMAL_PROMPT_TR = (
    "TERMAL güvenlik kamerası görüntüsü. Türkçe yaz, renk uydurma. "
    "Isı/sıcaklık ile ilgili hiçbir şey yazma (sıcak/ılık/soğuk dahil). "
    "Çıktıyı tam şu formatta yaz (2-3 satır):\n"
    "Kamera: {camera_name}\n"
    "Kişi tespit edildi: X (yoksa 0 yaz)\n"
    "Not: Kişi yoksa 'Muhtemel yanlış alarm.' yaz; kişi varsa kısa hareket/konum ekle.\n"
    "Bu tek bir kolaj görselidir, video değildir; akış uydurma.\n"
    "Kolaj 5 kare: 1-2 olay öncesi, 3 olay anı, 4-5 olay sonrası. Numaralara göre yorumla.\n"
    "Emin değilsen sayıyı 'en az X' yaz."
)

COLOR_PROMPT_TR = (
    "Renkli güvenlik kamerası görüntüsü. Türkçe yaz. "
    "Çıktıyı tam şu formatta yaz (2-3 satır):\n"
    "Kamera: {camera_name}\n"
    "Kişi tespit edildi: X (yoksa 0 yaz)\n"
    "Not: Kişi yoksa 'Muhtemel yanlış alarm.' yaz; kişi varsa kısa hareket/konum ekle.\n"
    "Bu tek bir kolaj görselidir, video değildir; akış uydurma.\n"
    "Kolaj 5 kare: 1-2 olay öncesi, 3 olay anı, 4-5 olay sonrası. Numaralara göre yorumla.\n"
    "Emin değilsen sayıyı 'en az X' yaz."
)


class AIService:
    """
    AI service for event analysis using OpenAI Vision API.
    
    Handles:
    - Event image analysis
    - Prompt template management
    - Per-camera prompt override
    - OpenAI API integration
    """
    
    def __init__(self):
        """Initialize AI service."""
        self.settings_service = get_settings_service()
        logger.info("AIService initialized")
    
    def analyze_event(
        self,
        event: Dict[str, Any],
        collage_path: Path,
        camera: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Analyze event using OpenAI Vision API.
        
        Args:
            event: Event data (id, camera_id, timestamp, confidence)
            collage_path: Path to collage image
            camera: Camera data (optional, for prompt override)
            
        Returns:
            AI summary text or None if disabled/failed
        """
        try:
            # Load config
            config = self.settings_service.load_config()
            
            # Check if AI is enabled
            if not config.ai.enabled:
                logger.debug("AI is disabled")
                return None
            
            # Check API key
            if not config.ai.api_key or config.ai.api_key == "***REDACTED***":
                logger.warning("AI API key not configured")
                return None
            
            # Get prompt
            prompt = self._get_prompt_for_event(event, camera)
            
            # Load and encode image
            image_base64 = self._encode_image(collage_path)
            if not image_base64:
                logger.error("Failed to encode image")
                return None
            
            # Call OpenAI API
            logger.info(f"Calling OpenAI API for event {event.get('id', 'unknown')}")
            
            client = OpenAI(api_key=config.ai.api_key)
            
            response = client.chat.completions.create(
                model=config.ai.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Kısa ama detaylı bir güvenlik raporu üret."
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=config.ai.max_tokens,
                temperature=config.ai.temperature or 0.3
            )
            
            # Extract summary
            summary = response.choices[0].message.content.strip()
            logger.info(f"AI analysis complete: {len(summary)} chars")
            
            return summary
            
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return None
    
    def _get_prompt_for_event(
        self,
        event: Dict[str, Any],
        camera: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Get AI prompt for event with hierarchy:
        1. Camera-level custom prompt (highest priority)
        2. Global custom prompt
        3. Global template (default/custom)
        4. Default (thermal)
        
        Args:
            event: Event data
            camera: Camera data (optional)
            
        Returns:
            Formatted prompt text
        """
        config = self.settings_service.load_config()
        
        # 1. Camera-level custom prompt (highest priority)
        if camera and camera.get('use_custom_prompt') and camera.get('ai_prompt_override'):
            base_prompt = camera['ai_prompt_override']
            logger.debug(f"Using camera-level prompt for {camera.get('name', 'unknown')}")
        
        # 2. Global custom prompt only when template is custom
        elif hasattr(config.ai, 'prompt_template') and config.ai.prompt_template == "custom":
            if getattr(config.ai, 'custom_prompt', ""):
                base_prompt = config.ai.custom_prompt
                logger.debug("Using global custom prompt")
            else:
                base_prompt = THERMAL_PROMPT_TR
                logger.debug("Custom template selected but empty, using default")

        # 3. Global template (default: color/thermal)
        elif hasattr(config.ai, 'prompt_template'):
            source = None
            if camera:
                camera_type = camera.get("type")
                if camera_type == "thermal":
                    source = "thermal"
                elif camera_type == "color":
                    source = "color"
                else:
                    source = camera.get("detection_source") or camera_type
            base_prompt = COLOR_PROMPT_TR if source == "color" else THERMAL_PROMPT_TR
            logger.debug("Using default prompt (%s)", source or "thermal")

        # 4. Default
        else:
            base_prompt = THERMAL_PROMPT_TR
            logger.debug("Using default thermal prompt")
        
        # Format with context
        camera_name = camera.get('name', 'Unknown') if camera else event.get('camera_id', 'Unknown')
        timestamp = event.get('timestamp', 'Unknown')
        confidence = event.get('confidence', 0)
        
        prompt = (
            base_prompt
            .replace("{camera_name}", str(camera_name))
            .replace("{timestamp}", str(timestamp))
            .replace("{confidence}", f"{confidence:.0%}")
        )
        
        return prompt

    
    def _encode_image(self, image_path: Path) -> Optional[str]:
        """
        Encode image to base64.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Base64 encoded image or None if failed
        """
        try:
            if not image_path.exists():
                logger.error(f"Image not found: {image_path}")
                return None
            
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
                
        except Exception as e:
            logger.error(f"Failed to encode image: {e}")
            return None
    
    def is_enabled(self) -> bool:
        """
        Check if AI is enabled.
        
        Returns:
            True if AI is enabled and configured
        """
        try:
            config = self.settings_service.load_config()
            has_key = config.ai.api_key and config.ai.api_key != "***REDACTED***"
            return bool(config.ai.enabled and has_key)
        except Exception:
            return False


# Global singleton instance
_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    """
    Get or create the global AI service instance.
    
    Returns:
        AIService: Global AI service instance
    """
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service
