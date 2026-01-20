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
SIMPLE_TEMPLATE = """
Bu thermal kamera görüntüsünde ne görüyorsun? 
Kişi sayısı, ne yaptıkları ve şüpheli bir durum var mı kısaca açıkla.
"""

SECURITY_FOCUSED_TEMPLATE = """
Sen bir ev güvenlik sistemi AI asistanısın.
Bu thermal kamera görüntüsünü analiz et:

Kamera: {camera_name}
Zaman: {timestamp}
Confidence: {confidence:.0%}

Şunları Türkçe olarak belirt:
1. İnsan var mı? Kaç kişi?
2. Ne görüyorsun? (görünüm, hareket, konum)
3. Şüpheli durum var mı?
4. Yanlış alarm olabilir mi? (ağaç, gölge, hayvan, araba)
5. Tehdit seviyesi: Düşük/Orta/Yüksek

Kısa ve net cevap ver (max 5 satır).
"""

DETAILED_TEMPLATE = """
Sen bir profesyonel güvenlik analisti AI'sısın.
Bu thermal kamera görüntü serisini (5 frame) analiz et:

Kamera: {camera_name}
Zaman: {timestamp}
YOLOv8 Confidence: {confidence:.0%}

Detaylı analiz yap:

1. İNSAN TESPİTİ:
   - Kaç kişi var?
   - Nerede konumlanmışlar?
   - Ne yapıyorlar?

2. GÖRSEL DETAYLAR:
   - Kıyafet rengi/tipi (varsa)
   - Boy/yapı
   - Taşıdığı eşya var mı?

3. HAREKET ANALİZİ:
   - Hareket yönü
   - Hız (yavaş, normal, hızlı)
   - Davranış (normal, şüpheli)

4. DURUM DEĞERLENDİRMESİ:
   - Şüpheli durum var mı?
   - Yanlış alarm olabilir mi?
   - Tehdit seviyesi: Düşük/Orta/Yüksek
   - Önerilen aksiyon

Türkçe, kısa ve net cevap ver (max 10 satır).
"""


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
                        "content": "Sen bir ev güvenlik sistemi AI asistanısın. Kısa ve net cevap ver."
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
        3. Global template (security_focused/simple/detailed)
        4. Default (simple)
        
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
        
        # 2. Global custom prompt
        elif hasattr(config.ai, 'custom_prompt') and config.ai.custom_prompt:
            base_prompt = config.ai.custom_prompt
            logger.debug("Using global custom prompt")
        
        # 3. Global template
        elif hasattr(config.ai, 'prompt_template'):
            template = config.ai.prompt_template
            if template == "security_focused":
                base_prompt = SECURITY_FOCUSED_TEMPLATE
            elif template == "detailed":
                base_prompt = DETAILED_TEMPLATE
            else:
                base_prompt = SIMPLE_TEMPLATE
            logger.debug(f"Using template: {template}")
        
        # 4. Default
        else:
            base_prompt = SIMPLE_TEMPLATE
            logger.debug("Using default simple template")
        
        # Format with context
        camera_name = camera.get('name', 'Unknown') if camera else event.get('camera_id', 'Unknown')
        timestamp = event.get('timestamp', 'Unknown')
        confidence = event.get('confidence', 0)
        
        prompt = base_prompt.format(
            camera_name=camera_name,
            timestamp=timestamp,
            confidence=confidence
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
