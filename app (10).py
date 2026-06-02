import os, sys, uuid, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from processor import VideoProcessor

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

jobs = {}

# ─── ROUTES ───────────────────────────────────────────────────────────────────

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>ClipForge — AI Video Editor</title>
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@300;400;500&display=swap" rel="stylesheet" />
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    :root {
      --bg: #0a0a0f; --surface: #111118; --card: #16161f; --border: #2a2a38;
      --accent: #e2ff5d; --accent2: #7c5cfc; --text: #e8e8f0; --muted: #6b6b88;
      --success: #5dff9a; --danger: #ff5d5d; --r: 14px;
    }
    html { scroll-behavior: smooth; }
    body {
      font-family: 'DM Mono', monospace; background: var(--bg); color: var(--text);
      min-height: 100vh; overflow-x: hidden;
    }
    body::before {
      content: ''; position: fixed; inset: 0; z-index: 0;
      background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E");
      pointer-events: none; opacity: .6;
    }
    .wrap { position: relative; z-index: 1; max-width: 1000px; margin: 0 auto; padding: 0 24px 80px; }
    header { padding: 48px 0 36px; display: flex; align-items: flex-end; gap: 16px; }
    .logo { font-family: 'Syne', sans-serif; font-weight: 800; font-size: 2.2rem; color: var(--accent); letter-spacing: -1px; }
    .logo span { color: var(--accent2); }
    .tagline { font-size: .75rem; color: var(--muted); text-transform: uppercase; letter-spacing: .1em; }
    .card { background: var(--card); border: 1px solid var(--border); border-radius: var(--r); padding: 28px; margin-bottom: 20px; }
    .card-title { font-family: 'Syne', sans-serif; font-weight: 700; font-size: 1rem; text-transform: uppercase; letter-spacing: .08em; margin-bottom: 20px; display: flex; align-items: center; gap: 10px; }
    .card-title span { color: var(--accent); font-size: 1.1rem; }
    .tabs { display: flex; gap: 10px; margin-bottom: 20px; border-bottom: 1px solid var(--border); }
    .tab-btn { background: none; border: none; color: var(--muted); font-family: 'DM Mono', monospace; font-size: .85rem; padding: 12px 18px; border-bottom: 2px solid transparent; cursor: pointer; transition: all .2s; text-transform: uppercase; letter-spacing: .06em; }
    .tab-btn:hover { color: var(--text); }
    .tab-btn.active { color: var(--accent); border-bottom-color: var(--accent); }
    .tab-content { display: none; }
    .tab-content.active { display: block; }
    .drop-zone { border: 2px dashed var(--border); border-radius: var(--r); padding: 40px 24px; text-align: center; cursor: pointer; transition: all .2s; position: relative; margin-bottom: 16px; }
    .drop-zone:hover, .drop-zone.drag-over { border-color: var(--accent); background: rgba(226,255,93,.04); }
    .drop-zone input[type=file] { position: absolute; inset: 0; opacity: 0; cursor: pointer; }
    .upload-icon { font-size: 2.4rem; margin-bottom: 14px; display: block; animation: bob 2s ease-in-out infinite; }
    @keyframes bob { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-6px); } }
    .upload-title { font-family: 'Syne', sans-serif; font-size: 1rem; font-weight: 700; margin-bottom: 6px; }
    .upload-sub { color: var(--muted); font-size: .78rem; }
    .file-chip { display: none; align-items: center; gap: 10px; background: rgba(226,255,93,.08); border: 1px solid rgba(226,255,93,.3); border-radius: 50px; padding: 8px 12px; margin-top: 12px; font-size: .8rem; }
    .file-chip .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--accent); }
    .file-chip .clear-btn { background: none; border: none; color: var(--danger); cursor: pointer; padding: 0 4px; font-size: .9rem; transition: all .2s; margin-left: 6px; }
    .file-chip .clear-btn:hover { transform: scale(1.2); }
    label.opt-label { display: block; font-size: .72rem; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); margin-bottom: 7px; }
    input[type=text], textarea, select { width: 100%; background: var(--surface); border: 1px solid var(--border); border-radius: 8px; color: var(--text); font-family: 'DM Mono', monospace; font-size: .82rem; padding: 9px 12px; outline: none; transition: border-color .15s; }
    input:focus, textarea:focus, select:focus { border-color: var(--accent2); }
    textarea { min-height: 80px; resize: vertical; }
    select option { background: #1a1a28; }
    .divider { border: none; border-top: 1px solid var(--border); margin: 20px 0; }
    .btn-primary { display: flex; align-items: center; justify-content: center; gap: 10px; width: 100%; background: var(--accent); color: #0a0a0f; font-family: 'Syne', sans-serif; font-weight: 700; font-size: 1rem; letter-spacing: .04em; border: none; border-radius: 50px; padding: 16px; cursor: pointer; transition: all .15s; }
    .btn-primary:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 10px 30px rgba(226,255,93,.25); }
    .btn-primary:disabled { opacity: .4; cursor: not-allowed; }
    .btn-secondary { display: flex; align-items: center; justify-content: center; gap: 10px; width: 100%; background: transparent; color: var(--accent2); font-family: 'Syne', sans-serif; font-weight: 700; font-size: .9rem; border: 2px solid var(--accent2); border-radius: 50px; padding: 14px; cursor: pointer; transition: all .15s; text-decoration: none; }
    .btn-secondary:hover { background: rgba(124,92,252,.12); transform: translateY(-2px); }
    .progress-bar-wrap { height: 6px; background: var(--border); border-radius: 50px; overflow: hidden; margin-bottom: 20px; }
    .progress-bar { height: 100%; background: linear-gradient(90deg, var(--accent2), var(--accent)); border-radius: 50px; transition: width .4s ease; width: 0%; }
    .progress-msg { font-size: .8rem; color: var(--muted); margin-bottom: 14px; min-height: 20px; }
    #progress-card, #inspiration-progress-card { display: none; }
    #result-card, #inspiration-result-card { display: none; }
    .success-banner { display: flex; align-items: center; gap: 12px; background: rgba(93,255,154,.06); border: 1px solid rgba(93,255,154,.25); border-radius: 10px; padding: 14px 18px; margin-bottom: 18px; font-size: .82rem; }
    .success-banner .icon { font-size: 1.3rem; }
    .error-banner { display: none; align-items: center; gap: 12px; background: rgba(255,93,93,.06); border: 1px solid rgba(255,93,93,.25); border-radius: 10px; padding: 14px 18px; margin-top: 14px; font-size: .8rem; color: var(--danger); }
    .info-box { background: rgba(226,255,93,.04); border: 1px solid rgba(226,255,93,.2); border-radius: 10px; padding: 12px 16px; margin-top: 12px; font-size: .78rem; color: var(--muted); line-height: 1.5; }
    .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
    @media(max-width: 640px) { .two-col { grid-template-columns: 1fr; } }
    footer { text-align: center; padding: 32px 0; color: var(--muted); font-size: .72rem; border-top: 1px solid var(--border); margin-top: 40px; }
    footer a { color: var(--accent2); text-decoration: none; }
    .fade-in { animation: fadeIn .4s ease both; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }
    
    /* ANALYSIS DISPLAY */
    #analysis-display { display: none; margin-top: 20px; padding: 20px; background: rgba(226,255,93,.06); border: 1px solid rgba(226,255,93,.2); border-radius: 10px; }
    #analysis-display.show { display: block; animation: fadeIn .4s ease; }
    .analysis-section { margin-bottom: 16px; }
    .analysis-section-title { font-family: 'Syne', sans-serif; font-weight: 700; font-size: .9rem; color: var(--accent); margin-bottom: 8px; text-transform: uppercase; }
    .analysis-item { font-size: .78rem; color: var(--muted); margin: 6px 0; padding: 0 8px; border-left: 2px solid var(--accent2); padding-left: 12px; }
    .analysis-list { display: flex; flex-wrap: wrap; gap: 6px; margin: 8px 0; }
    .analysis-tag { background: rgba(124,92,252,.2); border: 1px solid rgba(124,92,252,.3); color: var(--accent2); padding: 4px 10px; border-radius: 20px; font-size: .75rem; }
  </style>
</head>
<body>
<div class="wrap">
  <header>
    <div>
      <div class="logo">Clip<span>Forge</span></div>
      <div class="tagline">AI-powered video editing</div>
    </div>
  </header>

  <div class="tabs" style="margin-bottom: 30px;">
    <button class="tab-btn active" onclick="switchTab('quick')">🎬 Quick Edit</button>
    <button class="tab-btn" onclick="switchTab('inspire')">✨ By Inspiration</button>
  </div>

  <!-- QUICK EDIT -->
  <div id="quick" class="tab-content active">
    <div class="card fade-in">
      <div class="card-title"><span>📁</span> Upload Video</div>
      <div class="drop-zone" id="quick-zone">
        <input type="file" id="quick-input" accept="video/*" />
        <span class="upload-icon">🎥</span>
        <div class="upload-title">Drop your video</div>
        <div class="upload-sub">MP4 · MOV · AVI · MKV</div>
      </div>
      <div style="display: flex; justify-content: center;">
        <div id="quick-chip" class="file-chip">
          <div class="dot"></div>
          <span id="quick-name">—</span>
          <button class="clear-btn" title="Remove video" onclick="clearQuickVideo()">✕</button>
        </div>
      </div>
    </div>

    <div class="card fade-in">
      <div class="card-title"><span>✍️</span> Describe Your Vision</div>
      <textarea id="quick-vision" placeholder="e.g., 'fast cuts with upbeat music' or 'cinematic travel video'"></textarea>
      <div class="info-box">💡 Helps AI choose music mood and stock footage style</div>
    </div>

    <button class="btn-primary" id="quick-btn" disabled onclick="processQuick()" style="margin-bottom: 20px;">
      <span>▶</span> Start Editing
    </button>

    <div class="card fade-in" id="progress-card">
      <div class="card-title"><span>⚡</span> Processing</div>
      <div class="progress-bar-wrap">
        <div class="progress-bar" id="progress-bar"></div>
      </div>
      <div class="progress-msg" id="progress-msg">Starting…</div>
      <div class="error-banner" id="error-banner">
        <span>❌</span><span id="error-text"></span>
      </div>
    </div>

    <div class="card fade-in" id="result-card">
      <div class="card-title"><span>🎉</span> Ready!</div>
      <div class="success-banner">
        <span class="icon">✅</span> Your video is ready
      </div>
      <a class="btn-secondary" id="download-btn" href="#" target="_blank">⬇ Download</a>
    </div>
  </div>

  <!-- INSPIRATION -->
  <div id="inspire" class="tab-content">
    <div class="card fade-in">
      <div class="card-title"><span>✨</span> Edit by Inspiration</div>
      <p style="color: var(--muted); font-size: .82rem; margin-bottom: 20px;">
        Upload inspiration video + raw footage. Gemini AI analyzes the style & applies it to your video.
      </p>

      <div class="two-col">
        <div>
          <label class="opt-label">Inspiration Video</label>
          <div class="drop-zone" id="inspire-zone">
            <input type="file" id="inspire-input" accept="video/*" />
            <span class="upload-icon">✨</span>
            <div class="upload-title">Drop style reference</div>
            <div class="upload-sub">Video with the style you want</div>
          </div>
          <div class="file-chip" id="inspire-chip">
            <div class="dot"></div>
            <span id="inspire-name">—</span>
            <button class="clear-btn" title="Remove video" onclick="clearInspirationVideo()">✕</button>
          </div>
        </div>

        <div>
          <label class="opt-label">Your Raw Footage</label>
          <div class="drop-zone" id="raw-zone">
            <input type="file" id="raw-input" accept="video/*" />
            <span class="upload-icon">🎥</span>
            <div class="upload-title">Drop your video</div>
            <div class="upload-sub">To be edited</div>
          </div>
          <div class="file-chip" id="raw-chip">
            <div class="dot"></div>
            <span id="raw-name">—</span>
            <button class="clear-btn" title="Remove video" onclick="clearRawVideo()">✕</button>
          </div>
        </div>
      </div>

      <hr class="divider" />

      <label class="opt-label">Describe Your Vision (Optional)</label>
      <textarea id="inspire-vision" placeholder="e.g., 'Make it a fast travel vlog with nature stock footage and upbeat music'"></textarea>
      <div class="info-box">💡 Combine inspiration style with your own creative direction</div>
    </div>

    <button class="btn-primary" id="inspire-btn" disabled onclick="processInspire()" style="margin-bottom: 20px;">
      <span>▶</span> Create Video
    </button>

    <div class="card fade-in" id="inspiration-progress-card">
      <div class="card-title"><span>⚡</span> Processing</div>
      <div class="progress-bar-wrap">
        <div class="progress-bar" id="inspiration-progress-bar"></div>
      </div>
      <div class="progress-msg" id="inspiration-progress-msg">Starting…</div>
      
      <!-- GEMINI ANALYSIS DISPLAY -->
      <div id="analysis-display">
        <div class="analysis-section">
          <div class="analysis-section-title">🎬 What Gemini Detected</div>
          <div class="analysis-item"><strong>Trend Type:</strong> <span id="trend-type">—</span></div>
          <div class="analysis-item"><strong>Category:</strong> <span id="content-category">—</span></div>
          <div class="analysis-item"><strong>Summary:</strong> <span id="summary">—</span></div>
        </div>

        <div class="analysis-section">
          <div class="analysis-section-title">✨ Editing Style Detected</div>
          <div class="analysis-item"><strong>Technique:</strong> <span id="technique">—</span></div>
          <div class="analysis-item"><strong>Pacing:</strong> <span id="cut-frequency">—</span></div>
          <div class="analysis-item"><strong>Transitions:</strong> <span id="transition-type">—</span></div>
        </div>

        <div class="analysis-section">
          <div class="analysis-section-title">🎨 Effects & Visual Style</div>
          <div class="analysis-item"><strong>Color Grade:</strong> <span id="color-grade">—</span></div>
          <div class="analysis-item"><strong>Brightness:</strong> <span id="brightness">—</span></div>
          <div class="analysis-item"><strong>Saturation:</strong> <span id="saturation">—</span></div>
          <div class="analysis-item"><strong>Color Effects:</strong></div>
          <div class="analysis-list" id="color-effects-list"></div>
          <div class="analysis-item"><strong>Text Overlays:</strong> <span id="text-overlays">—</span></div>
          <div class="analysis-item"><strong>Special Effects:</strong></div>
          <div class="analysis-list" id="special-effects-list"></div>
        </div>

        <div class="analysis-section">
          <div class="analysis-section-title">🎵 Music Analysis</div>
          <div class="analysis-item"><strong>Music Style:</strong> <span id="music-style">—</span></div>
          <div class="analysis-item"><strong>Tempo:</strong> <span id="music-tempo">—</span></div>
          <div class="analysis-item"><strong>Mood:</strong> <span id="music-mood">—</span></div>
          <div class="analysis-item"><strong>How Used:</strong> <span id="music-placement">—</span></div>
        </div>

        <div class="analysis-section">
          <div class="analysis-section-title">🎥 B-Roll & Stock Footage</div>
          <div class="analysis-item"><strong>Types Being Searched:</strong></div>
          <div class="analysis-list" id="broll-types-list"></div>
          <div class="analysis-item"><strong>B-Roll Style:</strong> <span id="broll-style">—</span></div>
        </div>

        <div class="analysis-section">
          <div class="analysis-section-title">⭐ Viral Elements Detected</div>
          <div class="analysis-list" id="viral-elements-list"></div>
        </div>

        <div style="margin-top: 16px; padding: 12px; background: rgba(93,255,154,.06); border-left: 3px solid var(--success); border-radius: 6px;">
          <div style="font-size: .75rem; color: var(--success); font-weight: 700;">✅ NOW APPLYING THIS STYLE TO YOUR VIDEO</div>
          <div style="font-size: .75rem; color: var(--muted); margin-top: 4px;">Inserting stock footage • Adding music • Adjusting colors • Matching transitions</div>
        </div>
      </div>

      <div class="error-banner" id="inspiration-error-banner">
        <span>❌</span><span id="inspiration-error-text"></span>
      </div>
    </div>

    <div class="card fade-in" id="inspiration-result-card">
      <div class="card-title"><span>🎉</span> Ready!</div>
      <div class="success-banner">
        <span class="icon">✅</span> Video created with inspiration style!
      </div>
      <a class="btn-secondary" id="inspiration-download-btn" href="#" target="_blank">⬇ Download</a>
    </div>
  </div>

</div>

<footer>
  ClipForge · AI-Powered Video Editing · Music: <a href="https://pixabay.com" target="_blank">Pixabay</a> · Stock: <a href="https://pexels.com" target="_blank">Pexels</a>
</footer>

<script>
let jobId = null, pollTimer = null;

function switchTab(tab) {
  document.querySelectorAll('.tab-content').forEach(e => e.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(e => e.classList.remove('active'));
  document.getElementById(tab).classList.add('active');
  event.target.classList.add('active');
}

function displayAnalysis(analysis) {
  if (!analysis) return;
  
  const a = analysis;
  
  // Basic info
  document.getElementById('trend-type').textContent = a.trend_type || '—';
  document.getElementById('content-category').textContent = a.content_category || '—';
  document.getElementById('summary').textContent = a.summary || '—';
  
  // Editing style
  const editing = a.editing_style || {};
  document.getElementById('technique').textContent = editing.technique || '—';
  document.getElementById('cut-frequency').textContent = editing.cut_frequency || '—';
  document.getElementById('transition-type').textContent = editing.transition_type || '—';
  
  // Visual characteristics
  const visual = a.visual_characteristics || {};
  document.getElementById('color-grade').textContent = visual.color_grade || '—';
  document.getElementById('brightness').textContent = visual.brightness || '—';
  document.getElementById('saturation').textContent = visual.saturation || '—';
  
  // Effects
  const effects = a.effects_detected || {};
  document.getElementById('text-overlays').textContent = effects.text_overlays || '—';
  
  const colorEffectsList = document.getElementById('color-effects-list');
  colorEffectsList.innerHTML = '';
  if (effects.color_effects && Array.isArray(effects.color_effects)) {
    effects.color_effects.forEach(e => {
      const tag = document.createElement('div');
      tag.className = 'analysis-tag';
      tag.textContent = e;
      colorEffectsList.appendChild(tag);
    });
  }
  
  const specialEffectsList = document.getElementById('special-effects-list');
  specialEffectsList.innerHTML = '';
  if (effects.special_effects && Array.isArray(effects.special_effects)) {
    effects.special_effects.forEach(e => {
      const tag = document.createElement('div');
      tag.className = 'analysis-tag';
      tag.textContent = e;
      specialEffectsList.appendChild(tag);
    });
  }
  
  // Music
  const music = a.music_insights || {};
  document.getElementById('music-style').textContent = music.music_style || '—';
  document.getElementById('music-tempo').textContent = music.tempo || '—';
  document.getElementById('music-mood').textContent = music.mood || '—';
  document.getElementById('music-placement').textContent = music.placement || '—';
  
  // B-roll
  const broll = a.broll_analysis || {};
  document.getElementById('broll-style').textContent = broll.style || '—';
  
  const brollList = document.getElementById('broll-types-list');
  brollList.innerHTML = '';
  if (broll.primary_types && Array.isArray(broll.primary_types)) {
    broll.primary_types.forEach(t => {
      const tag = document.createElement('div');
      tag.className = 'analysis-tag';
      tag.textContent = t;
      brollList.appendChild(tag);
    });
  }
  
  // Viral elements
  const viralList = document.getElementById('viral-elements-list');
  viralList.innerHTML = '';
  if (a.viral_elements && Array.isArray(a.viral_elements)) {
    a.viral_elements.forEach(e => {
      const tag = document.createElement('div');
      tag.className = 'analysis-tag';
      tag.textContent = e;
      viralList.appendChild(tag);
    });
  }
  
  // Show analysis
  document.getElementById('analysis-display').classList.add('show');
}

// ===== QUICK EDIT =====
const quickZone = document.getElementById('quick-zone');
const quickInput = document.getElementById('quick-input');
const quickChip = document.getElementById('quick-chip');
const quickName = document.getElementById('quick-name');
const quickBtn = document.getElementById('quick-btn');

quickZone.addEventListener('dragover', e => { e.preventDefault(); quickZone.classList.add('drag-over'); });
quickZone.addEventListener('dragleave', () => quickZone.classList.remove('drag-over'));
quickZone.addEventListener('drop', e => {
  e.preventDefault(); quickZone.classList.remove('drag-over');
  if (e.dataTransfer.files.length) uploadQuick(e.dataTransfer.files[0]);
});
quickInput.addEventListener('change', () => uploadQuick(quickInput.files[0]));

function clearQuickVideo() {
  quickName.textContent = '—';
  quickChip.style.display = 'none';
  quickInput.value = '';
  jobId = null;
  quickBtn.disabled = true;
}

async function uploadQuick(file) {
  quickName.textContent = file.name;
  quickChip.style.display = 'flex';
  quickBtn.disabled = true;
  quickBtn.innerHTML = '<span>⏳</span> Uploading…';

  const fd = new FormData();
  fd.append('video', file);
  
  try {
    const r = await fetch('/upload', { method: 'POST', body: fd });
    const d = await r.json();
    jobId = d.job_id;
    quickBtn.disabled = false;
    quickBtn.innerHTML = '<span>▶</span> Start Editing';
  } catch(e) {
    showError(e.message, 'quick');
    quickBtn.innerHTML = '<span>▶</span> Start Editing';
  }
}

async function processQuick() {
  if (!jobId) return;
  quickBtn.disabled = true;
  
  document.getElementById('progress-card').style.display = 'block';
  document.getElementById('result-card').style.display = 'none';
  document.getElementById('error-banner').style.display = 'none';

  try {
    const r = await fetch(`/process/${jobId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_vision: document.getElementById('quick-vision').value })
    });
    if (!r.ok) throw new Error((await r.json()).error);
    pollTimer = setInterval(() => poll('quick'), 1200);
  } catch(e) {
    showError(e.message, 'quick');
    quickBtn.disabled = false;
  }
}

// ===== INSPIRATION =====
const inspireZone = document.getElementById('inspire-zone');
const inspireInput = document.getElementById('inspire-input');
const inspireChip = document.getElementById('inspire-chip');
const inspireName = document.getElementById('inspire-name');

const rawZone = document.getElementById('raw-zone');
const rawInput = document.getElementById('raw-input');
const rawChip = document.getElementById('raw-chip');
const rawName = document.getElementById('raw-name');
const inspireBtn = document.getElementById('inspire-btn');

[inspireZone, rawZone].forEach(zone => {
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
});

inspireZone.addEventListener('drop', e => {
  e.preventDefault(); inspireZone.classList.remove('drag-over');
  if (e.dataTransfer.files.length) {
    inspireName.textContent = e.dataTransfer.files[0].name;
    inspireChip.style.display = 'flex';
    checkInspire();
  }
});

rawZone.addEventListener('drop', e => {
  e.preventDefault(); rawZone.classList.remove('drag-over');
  if (e.dataTransfer.files.length) {
    rawName.textContent = e.dataTransfer.files[0].name;
    rawChip.style.display = 'flex';
    checkInspire();
  }
});

inspireInput.addEventListener('change', () => {
  inspireName.textContent = inspireInput.files[0].name;
  inspireChip.style.display = 'flex';
  checkInspire();
});

rawInput.addEventListener('change', () => {
  rawName.textContent = rawInput.files[0].name;
  rawChip.style.display = 'flex';
  checkInspire();
});

function clearInspirationVideo() {
  inspireName.textContent = '—';
  inspireChip.style.display = 'none';
  inspireInput.value = '';
  checkInspire();
}

function clearRawVideo() {
  rawName.textContent = '—';
  rawChip.style.display = 'none';
  rawInput.value = '';
  checkInspire();
}

function checkInspire() {
  const hasInspo = inspireChip.style.display === 'flex';
  const hasRaw = rawChip.style.display === 'flex';
  inspireBtn.disabled = !(hasInspo && hasRaw);
}

async function processInspire() {
  inspireBtn.disabled = true;
  inspireBtn.innerHTML = '<span>⏳</span> Processing…';
  
  document.getElementById('inspiration-progress-card').style.display = 'block';
  document.getElementById('inspiration-result-card').style.display = 'none';
  document.getElementById('inspiration-error-banner').style.display = 'none';
  document.getElementById('analysis-display').classList.remove('show');

  const fd = new FormData();
  fd.append('inspiration_video', inspireInput.files[0]);
  fd.append('raw_video', rawInput.files[0]);
  fd.append('description', document.getElementById('inspire-vision').value);

  try {
    const r = await fetch('/process-inspiration', { method: 'POST', body: fd });
    const d = await r.json();
    if (!r.ok) throw new Error(d.error);
    jobId = d.job_id;
    pollTimer = setInterval(() => poll('inspire'), 1200);
  } catch(e) {
    showError(e.message, 'inspire');
    inspireBtn.disabled = false;
    inspireBtn.innerHTML = '<span>▶</span> Create Video';
  }
}

// ===== POLLING =====
async function poll(type) {
  try {
    const r = await fetch(`/status/${jobId}`);
    const d = await r.json();
    
    const pct = d.progress || 0;
    const bar = type === 'quick' ? '#progress-bar' : '#inspiration-progress-bar';
    const msg = type === 'quick' ? '#progress-msg' : '#inspiration-progress-msg';
    
    document.querySelector(bar).style.width = pct + '%';
    document.querySelector(msg).textContent = d.message || '…';

    // Display analysis if available
    if (d.analysis && type === 'inspire') {
      displayAnalysis(d.analysis);
    }

    if (d.status === 'done') {
      clearInterval(pollTimer);
      showResult(type);
    } else if (d.status === 'error') {
      clearInterval(pollTimer);
      showError(d.message, type);
      if (type === 'quick') quickBtn.disabled = false;
      else inspireBtn.disabled = false;
    }
  } catch(e) {}
}

function showResult(type) {
  if (type === 'quick') {
    document.getElementById('result-card').style.display = 'block';
    document.getElementById('progress-bar').style.width = '100%';
    document.getElementById('download-btn').href = `/download/${jobId}`;
  } else {
    document.getElementById('inspiration-result-card').style.display = 'block';
    document.getElementById('inspiration-progress-bar').style.width = '100%';
    document.getElementById('inspiration-download-btn').href = `/download/${jobId}`;
  }
}

function showError(msg, type) {
  const selector = type === 'quick' ? '#error-banner' : '#inspiration-error-banner';
  const textSelector = type === 'quick' ? '#error-text' : '#inspiration-error-text';
  document.querySelector(selector).style.display = 'flex';
  document.querySelector(textSelector).textContent = msg;
}
</script>
</body>
</html>
"""

@app.route('/')
def index():
    return HTML


@app.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('video')
    if not file:
        return jsonify({'error': 'No video file provided'}), 400

    job_id = str(uuid.uuid4())
    filepath = os.path.join(UPLOAD_FOLDER, f"{job_id}_{file.filename}")
    file.save(filepath)

    jobs[job_id] = {
        'status': 'uploaded', 'progress': 0,
        'message': 'Ready to process', 'file': filepath, 'analysis': None
    }
    return jsonify({'job_id': job_id, 'filename': file.filename})


@app.route('/process/<job_id>', methods=['POST'])
def process(job_id):
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404
    if jobs[job_id]['status'] == 'processing':
        return jsonify({'error': 'Already processing'}), 400

    options = request.get_json() or {}
    jobs[job_id]['status'] = 'processing'

    def run():
        try:
            def cb(progress, msg, analysis=None):
                jobs[job_id]['progress'] = progress
                jobs[job_id]['message'] = msg
                if analysis:
                    jobs[job_id]['analysis'] = analysis

            p = VideoProcessor(jobs[job_id]['file'], OUTPUT_FOLDER, job_id, options, cb)
            output = p.process()
            jobs[job_id].update({'status': 'done', 'progress': 100, 'message': '✅ Done!', 'output': output})
        except Exception as e:
            jobs[job_id].update({
                'status': 'error',
                'progress': jobs[job_id].get('progress', 0),
                'message': str(e), 'error': str(e)
            })

    threading.Thread(target=run, daemon=True).start()
    return jsonify({'message': 'Processing started'})


@app.route('/process-inspiration', methods=['POST'])
def process_inspiration():
    raw_file = request.files.get('raw_video')
    inspo_file = request.files.get('inspiration_video')
    if not raw_file or not inspo_file:
        return jsonify({'error': 'Both videos required'}), 400

    job_id = str(uuid.uuid4())
    raw_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_raw_{raw_file.filename}")
    inspo_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_inspo_{inspo_file.filename}")
    raw_file.save(raw_path)
    inspo_file.save(inspo_path)
    description = request.form.get('description', '')

    jobs[job_id] = {'status': 'processing', 'progress': 0,
                    'message': '🤖 Starting AI analysis...', 'file': raw_path,
                    'inspiration': inspo_path, 'analysis': None}

    def run():
        try:
            def cb(progress, msg, analysis=None):
                jobs[job_id]['progress'] = progress
                jobs[job_id]['message'] = msg
                if analysis:
                    jobs[job_id]['analysis'] = analysis
            options = {'user_vision': description, 'inspiration_path': inspo_path}
            p = VideoProcessor(raw_path, OUTPUT_FOLDER, job_id, options, cb)
            output = p.process()
            jobs[job_id].update({'status': 'done', 'progress': 100, 'message': '✅ Done!', 'output': output})
        except Exception as e:
            jobs[job_id].update({'status': 'error', 'progress': jobs[job_id].get('progress', 0), 'message': str(e)})

    threading.Thread(target=run, daemon=True).start()
    return jsonify({'job_id': job_id, 'message': 'Processing started'})


@app.route('/status/<job_id>')
def status(job_id):
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404
    info = {k: v for k, v in jobs[job_id].items() if k not in ('file', 'output', 'inspiration')}
    return jsonify(info)


@app.route('/download/<job_id>')
def download(job_id):
    if job_id not in jobs or jobs[job_id].get('status') != 'done':
        return jsonify({'error': 'Video not ready'}), 400
    return send_file(jobs[job_id]['output'], as_attachment=True,
                     download_name='clipforge_output.mp4', mimetype='video/mp4')


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 7860))
    app.run(host="0.0.0.0", port=port, debug=False)