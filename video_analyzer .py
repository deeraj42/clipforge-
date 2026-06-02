import os, subprocess, json, base64, requests

GEMINI_API_KEY = "AIzaSyBC_kXGjxKI15CUGhJvO99Qac9X4J6NZwc"
GEMINI_MODEL = "gemini-2.0-flash"

def extract_frames(video_path, num_frames=6):
    try:
        result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", video_path],
                               capture_output=True, text=True, timeout=10)
        duration = float(json.loads(result.stdout)["format"]["duration"])
        interval = duration / (num_frames + 1)
        
        frames = []
        os.makedirs("/tmp/frames", exist_ok=True)
        
        for i in range(num_frames):
            timestamp = interval * (i + 1)
            frame_path = f"/tmp/frames/frame_{i}.jpg"
            
            subprocess.run(["ffmpeg", "-y", "-ss", str(timestamp), "-i", video_path, "-vframes", "1", "-q:v", "2", frame_path],
                          capture_output=True, text=True, timeout=10)
            
            if os.path.exists(frame_path): frames.append(frame_path)
        
        return frames
    except: return []

def encode_image_to_base64(image_path):
    try:
        with open(image_path, "rb") as f: return base64.standard_b64encode(f.read()).decode("utf-8")
    except: return None

def analyze_with_gemini(frames):
    try:
        content = [{"type": "text", "text": """Analyze video frames. Return ONLY JSON:
{
    "trend_type": "type",
    "content_category": "category",
    "editing_style": {"technique": "x", "cut_frequency": "x", "jump_cuts": "yes/no", "transition_type": "x"},
    "effects_detected": {"color_effects": [], "text_overlays": "yes/no", "motion_graphics": "yes/no", "special_effects": [], "sound_effects": "yes/no"},
    "music_insights": {"music_style": "style", "tempo": "Fast/Medium/Slow", "mood": "mood", "placement": "where"},
    "broll_analysis": {"primary_types": ["type1", "type2"], "style": "style", "percentage_breakdown": {}},
    "visual_characteristics": {"color_grade": "grade", "brightness": "level", "saturation": "level", "aspect_ratio": "ratio"},
    "viral_elements": ["element1"],
    "summary": "summary"
}"""}]
        
        for frame_path in frames:
            b64 = encode_image_to_base64(frame_path)
            if b64: content.append({"type": "image", "image": {"data": b64, "mimeType": "image/jpeg"}})
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
        payload = {"contents": [{"role": "user", "parts": content}], "generationConfig": {"temperature": 0.3, "maxOutputTokens": 2000}}
        
        response = requests.post(url, json=payload, timeout=60)
        if response.status_code != 200: return get_default()
        
        result = response.json()
        if "candidates" not in result: return get_default()
        
        text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
        analysis = json.loads(text)
        return validate(analysis)
    except: return get_default()

def validate(analysis):
    defaults = {
        "trend_type": "General", "content_category": "Mixed",
        "editing_style": {"technique": "Standard", "cut_frequency": "Regular", "jump_cuts": "no", "transition_type": "cuts"},
        "effects_detected": {"color_effects": [], "text_overlays": "no", "motion_graphics": "no", "special_effects": [], "sound_effects": "no"},
        "music_insights": {"music_style": "Cinematic", "tempo": "Medium", "mood": "cinematic", "placement": "background"},
        "broll_analysis": {"primary_types": ["lifestyle"], "style": "professional", "percentage_breakdown": {}},
        "visual_characteristics": {"color_grade": "neutral", "brightness": "normal", "saturation": "normal", "aspect_ratio": "16:9"},
        "viral_elements": [], "summary": "Professional editing"
    }
    for key, val in defaults.items():
        if key not in analysis: analysis[key] = val
    return analysis

def get_default():
    return {
        "trend_type": "General", "content_category": "Mixed",
        "editing_style": {"technique": "Standard", "cut_frequency": "Regular", "jump_cuts": "no", "transition_type": "cuts"},
        "effects_detected": {"color_effects": [], "text_overlays": "no", "motion_graphics": "no", "special_effects": [], "sound_effects": "no"},
        "music_insights": {"music_style": "Cinematic", "tempo": "Medium", "mood": "cinematic", "placement": "background"},
        "broll_analysis": {"primary_types": ["lifestyle"], "style": "professional", "percentage_breakdown": {}},
        "visual_characteristics": {"color_grade": "neutral", "brightness": "normal", "saturation": "normal", "aspect_ratio": "16:9"},
        "viral_elements": [], "summary": "Professional editing"
    }

def analyze_inspiration_video(video_path):
    if not os.path.exists(video_path): return get_default()
    frames = extract_frames(video_path, num_frames=6)
    if not frames: return get_default()
    analysis = analyze_with_gemini(frames)
    return validate(analysis)
