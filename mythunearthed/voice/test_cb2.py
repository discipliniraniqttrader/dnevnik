import torch, soundfile as sf
from chatterbox.tts import ChatterboxTTS
torch.set_num_threads(4)
m = ChatterboxTTS.from_pretrained(device="cpu")
txt = "Four mountains claim they hold Noah's Ark. But the Bible names only a region. So which one is it?"
wav = m.generate(txt, audio_prompt_path="/home/user/zenit/out/voice_am_michael.wav", exaggeration=0.6, cfg_weight=0.45)
sf.write("/home/user/zenit/out/voice_cb_michael.wav", wav.squeeze().numpy(), m.sr)
