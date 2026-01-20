"""
AI test service for Smart Motion Detector v2.

Handles OpenAI connection testing.
"""
import logging
import openai

logger = logging.getLogger(__name__)


async def test_openai_connection(api_key: str, model: str = "gpt-4o") -> dict:
    """
    Test OpenAI API connection.
    
    Args:
        api_key: OpenAI API key
        model: Model to test
        
    Returns:
        Dict with success status and message
    """
    try:
        openai.api_key = api_key
        
        # Simple test query
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant."
                },
                {
                    "role": "user",
                    "content": "Say 'OK' if you can read this."
                }
            ],
            max_tokens=10,
            temperature=0.3
        )
        
        result = response.choices[0].message.content.strip()
        
        return {
            "success": True,
            "message": "OpenAI connection successful",
            "response": result,
            "model": model
        }
        
    except Exception as e:
        logger.error(f"OpenAI test failed: {e}")
        return {
            "success": False,
            "message": str(e),
            "response": None,
            "model": model
        }
