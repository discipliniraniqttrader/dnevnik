# run with voice/venv/bin/python ; HF_HUB_DISABLE_XET=1
import json, os, sys, torch, soundfile as sf
from pathlib import Path
from chatterbox.tts import ChatterboxTTS
torch.set_num_threads(4)
H = Path("/home/user/zenit/noah")
beats = json.load(open(H / "script.json"))["beats"]
TTS = json.load(open(H / "tts_text.json"))
m = ChatterboxTTS.from_pretrained(device="cpu")
for i, b in enumerate(beats, 1):
    p = H / "voice" / f"beat{i:02d}.wav"
    if p.exists(): continue
    txt = TTS.get(str(i), b["text"])
    torch.manual_seed(100 + i)
    wav = m.generate(txt, audio_prompt_path="/home/user/zenit/out/voice_am_michael.wav", exaggeration=0.6, cfg_weight=0.45)
    sf.write(str(p), wav.squeeze().numpy(), m.sr)
    print("done", i, txt, flush=True)
