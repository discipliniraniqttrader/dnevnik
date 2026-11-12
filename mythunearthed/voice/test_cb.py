import time, torch, soundfile as sf
from chatterbox.tts import ChatterboxTTS
torch.set_num_threads(4)
t=time.time(); m = ChatterboxTTS.from_pretrained(device="cpu"); print("load", round(time.time()-t,1))
txt = "Four mountains claim they hold Noah's Ark. But the Bible names only a region. So which one is it?"
for ex in (0.5, 0.75):
    t=time.time(); wav = m.generate(txt, exaggeration=ex, cfg_weight=0.5)
    a = wav.squeeze().numpy(); sf.write(f"/home/user/zenit/out/voice_cb_ex{ex}.wav", a, m.sr)
    print(ex, round(len(a)/m.sr,1), "s audio in", round(time.time()-t,1), "s")
