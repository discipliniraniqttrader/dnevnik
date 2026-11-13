# run with /home/user/zenit/voice/venv/bin/python  (HF_HUB_DISABLE_XET=1):  tts_worker.py jobs.json
# jobs.json = {"prompt": wav, "exaggeration": .6, "cfg": .45, "jobs": [[idx, text, out_wav], ...]}
import json, sys, torch, soundfile as sf
from pathlib import Path
from chatterbox.tts import ChatterboxTTS
torch.set_num_threads(4)
J = json.load(open(sys.argv[1]))
m = ChatterboxTTS.from_pretrained(device="cpu")
for idx, text, out in J["jobs"]:
    if Path(out).exists(): continue
    torch.manual_seed(100 + idx)
    wav = m.generate(text, audio_prompt_path=J["prompt"], exaggeration=J["exaggeration"], cfg_weight=J["cfg"])
    sf.write(out, wav.squeeze().numpy(), m.sr)
    print("done", idx, text, flush=True)
