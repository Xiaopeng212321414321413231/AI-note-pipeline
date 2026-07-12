"""音频转写模块 — 支持长音频自动分段（>5分钟切片）"""
import warnings; warnings.filterwarnings('ignore', message='FP16 is not supported')
import os, subprocess, json, tempfile, whisper

def _duration(path):
    r = subprocess.run(['ffprobe','-v','quiet','-print_format','json','-show_format',path], capture_output=True, text=False)
    return float(json.loads(r.stdout.decode("utf-8", errors="replace"))['format']['duration'])

def _chunk(path, max_min=5):
    d = _duration(path)
    if d <= max_min * 60:
        return [path]
    tmp = tempfile.mkdtemp(prefix='achunk_')
    seg = max_min * 60
    parts = []
    s = 0
    while s < d:
        out = os.path.join(tmp, f'c{len(parts):03d}.wav')
        subprocess.run(['ffmpeg','-y','-ss',str(s),'-t',str(seg),'-i',path,out], capture_output=True)
        parts.append(out)
        s += seg
    print(f"   ✂️ 音频 {d:.0f}s > {max_min}分钟，切为 {len(parts)} 段")
    return parts

def transcribe_audio(file_path):
    chunks = _chunk(file_path)
    results = []
    for i, c in enumerate(chunks):
        if len(chunks) > 1: print(f"   ⏳ 段{i+1}/{len(chunks)}")
        model = whisper.load_model('tiny')
        r = model.transcribe(c, language='zh')
        results.append(r['text'].strip())
        if c != file_path:
            try: os.remove(c)
            except: pass
    return ' '.join(results)