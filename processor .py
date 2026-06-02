import os
import subprocess
import json
import requests
import random
from video_analyzer import analyze_inspiration_video

FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"

PEXELS_API_KEY = "Spge8kLTTWQs4SqeVwl5mZ59KwjPoXBexECfQHCZiz7OkxMWljgufu0d"
PIXABAY_API_KEY = "48337968-4b1e8e6c2e7c9d1a3f2b0e7c4"  # Free key — replace with yours from pixabay.com/api

# Fallback music (used only if Jamendo fails)
FALLBACK_MUSIC = {
    "upbeat":      "https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3",
    "cinematic":   "https://cdn.pixabay.com/download/audio/2022/01/27/audio_d0ef389a7e.mp3",
    "ambient":     "https://cdn.pixabay.com/download/audio/2022/03/10/audio_c8c8a73467.mp3",
    "motivational":"https://cdn.pixabay.com/download/audio/2021/08/09/audio_88447e769a.mp3",
}

# Jamendo mood → tag mapping
JAMENDO_TAGS = {
    "upbeat":      "upbeat",
    "cinematic":   "cinematic",
    "ambient":     "ambient",
    "motivational":"motivational",
    "happy":       "happy",
    "epic":        "epic",
    "romantic":    "romantic",
    "dark":        "dark",
}


class VideoProcessor:
    def __init__(self, input_path, output_folder, job_id, options, status_callback):
        self.input_path = input_path
        self.output_folder = output_folder
        self.job_id = job_id
        self.options = options
        self.cb = status_callback
        self.work_dir = os.path.join(output_folder, job_id)
        os.makedirs(self.work_dir, exist_ok=True)

    def process(self):
        try:
            if 'inspiration_path' in self.options:
                return self.process_with_inspiration()
            return self.process_quick()
        except Exception as e:
            print(f"❌ ERROR: {e}")
            raise

    # ─── QUICK EDIT ───────────────────────────────────────────────────────────

    def process_quick(self):
        self.cb(10, "🔍 Detecting silence in footage...")
        segments = self.detect_silence()

        self.cb(25, "✂️ Removing silent parts...")
        video = self.cut_and_join(segments)

        self.cb(50, "🎵 Fetching trending music from Jamendo...")
        video = self.add_music(video, "cinematic")

        self.cb(75, "🎨 Applying color grading...")
        video = self.apply_effects(video, {})

        self.cb(90, "📦 Final encoding...")
        return self.final_encode(video)

    # ─── INSPIRATION EDIT ─────────────────────────────────────────────────────

    def process_with_inspiration(self):
        self.cb(5,  "🤖 Analyzing inspiration video with Gemini AI...")
        analysis = analyze_inspiration_video(self.options.get('inspiration_path'))
        self.cb(8,  "📊 Processing AI analysis results...", analysis=analysis)

        self.cb(20, "🔍 Scanning raw footage for silence...")
        segments = self.detect_silence()

        self.cb(35, "✂️ Cutting and joining clean segments...")
        video = self.cut_and_join(segments)

        broll_types = analysis.get("broll_analysis", {}).get("primary_types", ["lifestyle"])
        self.cb(50, f"🎥 Searching stock footage: {', '.join(broll_types[:2])}...")
        video = self.add_stock_footage_smart(video, broll_types)

        mood = analysis.get("music_insights", {}).get("mood", "cinematic")
        self.cb(65, f"🎵 Finding {mood} music on Jamendo...")
        video = self.add_music(video, mood)

        self.cb(80, "🎨 Applying detected color grade & effects...")
        video = self.apply_effects(video, analysis)

        self.cb(90, "📦 Final encoding...")
        return self.final_encode(video)

    # ─── SILENCE DETECTION ────────────────────────────────────────────────────

    def detect_silence(self):
        try:
            cmd = [FFMPEG, "-i", self.input_path,
                   "-af", "silencedetect=noise=-30dB:d=0.5", "-f", "null", "-"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            starts, ends = [], []
            for line in result.stderr.split("\n"):
                if "silence_start" in line:
                    try: starts.append(float(line.split()[-1]))
                    except: pass
                if "silence_end" in line:
                    try: ends.append(float(line.split()[4]))
                    except: pass

            total = self.get_duration(self.input_path)
            if total == 0:
                return [{"start": 0, "end": 9999}]

            segments, prev = [], 0
            for s, e in zip(starts, ends):
                if s > prev:
                    segments.append({"start": prev, "end": s})
                prev = e
            if prev < total:
                segments.append({"start": prev, "end": total})

            return segments if segments else [{"start": 0, "end": total}]
        except:
            return [{"start": 0, "end": self.get_duration(self.input_path)}]

    # ─── CUT & JOIN ───────────────────────────────────────────────────────────

    def cut_and_join(self, clips):
        if len(clips) <= 1:
            return self.input_path

        clip_files = []
        for i, c in enumerate(clips):
            temp = os.path.join(self.work_dir, f"clip_{i}.mp4")
            subprocess.run([FFMPEG, "-y", "-ss", str(c["start"]), "-i", self.input_path,
                            "-t", str(c["end"] - c["start"]),
                            "-c:v", "libx264", "-c:a", "aac", temp],
                           capture_output=True, text=True, timeout=60)
            if os.path.exists(temp) and os.path.getsize(temp) > 1000:
                clip_files.append(temp)

        if not clip_files:
            return self.input_path

        txt = os.path.join(self.work_dir, "list.txt")
        with open(txt, "w") as f:
            for c in clip_files:
                f.write(f"file '{os.path.abspath(c)}'\n")

        out = os.path.join(self.work_dir, "joined.mp4")
        subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", txt, "-c", "copy", out],
                       capture_output=True, text=True, timeout=60)

        return out if os.path.exists(out) else self.input_path

    # ─── STOCK FOOTAGE (Pexels + Pixabay) ────────────────────────────────────

    def add_stock_footage_smart(self, video, keywords):
        try:
            for keyword in keywords:
                # Try Pexels first
                stock = self._get_pexels_video(keyword)
                # Fallback to Pixabay
                if not stock:
                    stock = self._get_pixabay_video(keyword)
                if stock:
                    return self._insert_stock(video, stock)
            return video
        except:
            return video

    def _get_pexels_video(self, keyword):
        try:
            headers = {"Authorization": PEXELS_API_KEY}
            url = f"https://api.pexels.com/videos/search?query={keyword}&per_page=5&min_duration=3&max_duration=15"
            resp = requests.get(url, headers=headers, timeout=10)
            videos = resp.json().get("videos", [])
            if not videos:
                return None

            selected = random.choice(videos)
            files = selected.get("video_files", [])
            # Pick smallest HD file to save time
            files = [f for f in files if f.get("quality") in ("hd", "sd")]
            if not files:
                return None

            path = os.path.join(self.work_dir, f"stock_pexels_{keyword}.mp4")
            r = requests.get(files[0]["link"], timeout=30)
            with open(path, "wb") as f:
                f.write(r.content)
            return path if os.path.getsize(path) > 10000 else None
        except:
            return None

    def _get_pixabay_video(self, keyword):
        try:
            url = (f"https://pixabay.com/api/videos/"
                   f"?key={PIXABAY_API_KEY}&q={keyword}&per_page=5&min_width=1280")
            resp = requests.get(url, timeout=10)
            hits = resp.json().get("hits", [])
            if not hits:
                return None

            selected = random.choice(hits)
            videos = selected.get("videos", {})
            # Pick medium quality
            link = (videos.get("medium") or videos.get("small") or {}).get("url")
            if not link:
                return None

            path = os.path.join(self.work_dir, f"stock_pixabay_{keyword}.mp4")
            r = requests.get(link, timeout=30)
            with open(path, "wb") as f:
                f.write(r.content)
            return path if os.path.getsize(path) > 10000 else None
        except:
            return None

    def _insert_stock(self, video, stock):
        try:
            out = os.path.join(self.work_dir, "with_stock.mp4")
            txt = os.path.join(self.work_dir, "concat_list.txt")
            with open(txt, "w") as f:
                f.write(f"file '{os.path.abspath(video)}'\n")
                f.write(f"file '{os.path.abspath(stock)}'\n")

            result = subprocess.run(
                [FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", txt, "-c", "copy", out],
                capture_output=True, text=True, timeout=300)
            return out if result.returncode == 0 and os.path.exists(out) else video
        except:
            return video

    # ─── MUSIC (Jamendo API — free & legal) ──────────────────────────────────

    def add_music(self, video, mood):
        music_path = self._fetch_jamendo_music(mood)
        if not music_path:
            music_path = self._fetch_fallback_music(mood)
        if not music_path:
            return video
        return self._mix_music(video, music_path)

    def _fetch_jamendo_music(self, mood):
        try:
            tag = JAMENDO_TAGS.get(mood.lower(), "cinematic")
            # Jamendo public API — client_id is their open demo key
            url = (f"https://api.jamendo.com/v3.0/tracks/"
                   f"?client_id=b6747d04&format=json&limit=10"
                   f"&tags={tag}&include=musicinfo&audioformat=mp32"
                   f"&order=popularity_total")
            resp = requests.get(url, timeout=10)
            tracks = resp.json().get("results", [])
            if not tracks:
                return None

            track = random.choice(tracks[:5])
            audio_url = track.get("audio")
            if not audio_url:
                return None

            path = os.path.join(self.work_dir, "music_jamendo.mp3")
            r = requests.get(audio_url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code != 200 or len(r.content) < 5000:
                return None
            with open(path, "wb") as f:
                f.write(r.content)
            return path
        except:
            return None

    def _fetch_fallback_music(self, mood):
        try:
            url = FALLBACK_MUSIC.get(mood, FALLBACK_MUSIC["cinematic"])
            path = os.path.join(self.work_dir, "music_fallback.mp3")
            r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code != 200 or len(r.content) < 1000:
                return None
            with open(path, "wb") as f:
                f.write(r.content)
            return path
        except:
            return None

    def _mix_music(self, video, music_path):
        try:
            out = os.path.join(self.work_dir, "with_music.mp4")
            result = subprocess.run(
                [FFMPEG, "-y", "-i", video,
                 "-stream_loop", "-1", "-i", music_path,
                 "-filter_complex",
                 "[1:a]volume=0.15[music];[0:a][music]amix=inputs=2:duration=first[a]",
                 "-map", "0:v", "-map", "[a]",
                 "-c:v", "libx264", "-c:a", "aac", "-shortest", out],
                capture_output=True, text=True, timeout=300)
            return out if result.returncode == 0 and os.path.exists(out) else video
        except:
            return video

    # ─── COLOR EFFECTS ────────────────────────────────────────────────────────

    def apply_effects(self, video, analysis):
        try:
            out = os.path.join(self.work_dir, "with_effects.mp4")
            color = analysis.get("visual_characteristics", {}).get("color_grade", "neutral")

            vf = {
                "warm":    "eq=contrast=1.2:brightness=0.1:saturation=1.3",
                "cool":    "eq=contrast=1.2:brightness=-0.05:saturation=1.1",
                "vibrant": "eq=contrast=1.25:brightness=0:saturation=1.4",
                "dark":    "eq=contrast=1.3:brightness=-0.15:saturation=1.1",
            }.get(color, "eq=contrast=1.15:brightness=0.05:saturation=1.2")

            result = subprocess.run(
                [FFMPEG, "-y", "-i", video, "-vf", vf,
                 "-c:v", "libx264", "-c:a", "copy", out],
                capture_output=True, text=True, timeout=600)
            return out if result.returncode == 0 and os.path.exists(out) else video
        except:
            return video

    # ─── FINAL ENCODE ─────────────────────────────────────────────────────────

    def final_encode(self, video):
        final = os.path.join(self.output_folder, f"{self.job_id}_final.mp4")
        subprocess.run(
            [FFMPEG, "-y", "-i", video,
             "-c:v", "libx264", "-preset", "medium", "-crf", "18",
             "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", final],
            capture_output=True, text=True, timeout=600)

        if not os.path.exists(final) or os.path.getsize(final) < 10000:
            raise Exception("Final encoding failed — output too small or missing")

        self.cb(100, "✅ Done! Your video is ready.")
        return final

    # ─── UTILS ────────────────────────────────────────────────────────────────

    def get_duration(self, path):
        try:
            result = subprocess.run(
                [FFPROBE, "-v", "error", "-show_entries", "format=duration",
                 "-of", "json", path],
                capture_output=True, text=True, timeout=10)
            return float(json.loads(result.stdout)["format"]["duration"])
        except:
            return 0
