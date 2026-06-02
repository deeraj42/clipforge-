def generate_edit_plan(vision):
    vision_lower = vision.lower()
    mood = "cinematic"
    if any(w in vision_lower for w in ['fast','quick','upbeat']): mood = "upbeat"
    elif any(w in vision_lower for w in ['chill','calm','ambient']): mood = "ambient"
    
    pace = "medium"
    if any(w in vision_lower for w in ['fast','quick']): pace = "fast"
    elif any(w in vision_lower for w in ['slow','cinematic']): pace = "slow"
    
    keywords = []
    for cat, words in [('travel',['travel','journey','explore']),('nature',['nature','landscape','forest']),('city',['city','urban','street']),('lifestyle',['lifestyle','vlog','daily'])]:
        if any(w in vision_lower for w in words): keywords.append(cat)
    
    if not keywords: keywords = ['cinematic','dynamic']
    
    return {"mood": mood, "pace": pace, "stock_keywords": keywords[:3], "music_mood": mood}
