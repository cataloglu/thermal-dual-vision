"""
AI response parsing constants.

These strings MUST match the prompts defined in app/services/ai.py.
If the AI prompt changes, update these lists accordingly.
"""

AI_NEGATIVE_MARKERS = [
    "insan tespit edilmedi",
    "no human",
    "muhtemel yanlış alarm",
    "muhtemel yanlis alarm",
    "false alarm",
]

AI_POSITIVE_MARKERS = [
    "kişi tespit edildi",
    "kisi tespit edildi",
    "insan tespit edildi",
    "person detected",
]
