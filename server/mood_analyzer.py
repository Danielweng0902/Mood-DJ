# -*- coding: utf-8 -*-
def analyze_text(prompt: str) -> str:
    prompt = (prompt or "").lower()
    if any(k in prompt for k in ["sad", "lonely", "tired", "cry", "down"]):
        return "sad"
    if any(k in prompt for k in ["happy", "excited", "love", "good"]):
        return "happy"
    if any(k in prompt for k in ["relax", "calm", "focus", "quiet"]):
        return "calm"
    if any(k in prompt for k in ["party", "energetic", "run", "dance"]):
        return "energetic"
    return "calm"