#!/usr/bin/env python3
"""
Джарвис — гласов помощник за компютъра.

  • Двойно пляскане            -> сутрешната рутина
  • „Джарвис <команда> край“    -> изпълнява командата
    Например: „Джарвис, пусни в YouTube лофи музика, край“

Режими:
  python jarvis.py              # слуша за пляскане и за „Джарвис … край“
  python jarvis.py --no-clap    # само гласови команди
  python jarvis.py --mic-test   # показва нивата на микрофона (за настройка)
  python jarvis.py --run        # пуска рутината веднага (за проба)
"""
import argparse
import datetime as dt
import difflib
import json
import os
import platform
import re
import subprocess
import sys
import time
import urllib.parse
import webbrowser
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
CONFIG_PATH = HERE / "config.json"
SAMPLERATE = 16000
BLOCK = 320  # 20 ms
STEP = BLOCK / SAMPLERATE
CLAP = "CLAP"


# ---------------------------------------------------------------- събития към интерфейса
def _print_event(kind, **data):
    if kind == "status":
        print(f"[{data['state']}] {data.get('text', '')}")
    elif kind in ("heard", "say", "result", "info"):
        print({"heard": "Чух: ", "say": "Джарвис: ", "result": "", "info": ""}[kind] + data.get("text", ""))


emit = _print_event  # интерфейсът го подменя


def set_emitter(fn):
    global emit
    emit = fn


def load_config(path=CONFIG_PATH):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------- пляскане
class ClapDetector:
    """Двойно пляскане: два кратки, резки звука през 0.12–0.8 s, всеки след кратка тишина.
    Говор и музика са по-дълги или без тишина преди тях, затова не се броят."""

    def __init__(self, sensitivity=6.0, min_level=0.12, max_clap_len=0.12,
                 quiet_before=0.12, min_gap=0.12, max_gap=0.8):
        self.factor, self.min_level = sensitivity, min_level
        self.max_clap_len, self.quiet_before = max_clap_len, quiet_before
        self.min_gap, self.max_gap = min_gap, max_gap
        self.noise = 0.01
        self.loud_since = None
        self.loud_end = -10.0
        self.last_clap = None

    def process(self, block, t):
        """t = времето в края на блока (секунди). Връща True при двойно пляскане."""
        peak = float(np.max(np.abs(block))) if len(block) else 0.0
        if peak > max(self.min_level, self.noise * self.factor):
            if self.loud_since is None:
                self.loud_since = t - STEP
            return False

        self.noise = 0.97 * self.noise + 0.03 * peak
        if self.loud_since is None:
            return False
        onset, duration = self.loud_since, t - STEP - self.loud_since
        quiet = onset - self.loud_end
        self.loud_since, self.loud_end = None, t - STEP
        if duration > self.max_clap_len or quiet < self.quiet_before:
            self.last_clap = None  # не е пляскане
            return False
        if self.last_clap is not None and self.min_gap <= onset - self.last_clap <= self.max_gap:
            self.last_clap = None
            return True
        self.last_clap = onset
        return False


# ---------------------------------------------------------------- „Джарвис … край“
def find_word(text, words):
    """Първата поява на някоя от думите като отделна дума. Връща (начало, край) или None."""
    best = None
    for w in words:
        m = re.search(r"(?<!\w)" + re.escape(w.lower()) + r"(?!\w)", text)
        if m and (best is None or m.start() < best[0]):
            best = (m.start(), m.end())
    return best


class CommandAssembler:
    """Сглобява команда между думата за начало и думата за край, дори когато
    тя е казана на няколко части."""

    def __init__(self, wake_words, end_words, timeout=20.0):
        self.wake = [w.lower() for w in wake_words]
        self.end = [w.lower() for w in end_words]
        self.timeout = timeout
        self.reset()

    def reset(self):
        self.active, self.buffer, self.started = False, "", 0.0

    def timed_out(self, now):
        if self.active and now - self.started > self.timeout:
            self.reset()
            return True
        return False

    def feed(self, text, now):
        """Връща ("command", текст), ("listening", None) или (None, None)."""
        text = text.lower().strip(" .,!?")
        w = find_word(text, self.wake)
        if w:  # „Джарвис“ (пак) — започваме отначало
            self.active, self.started, self.buffer = True, now, text[w[1]:]
        elif self.active:
            self.buffer += " " + text
        else:
            return None, None
        e = find_word(self.buffer, self.end)
        if e:
            cmd = self.buffer[:e[0]].strip(" ,.!?")
            self.reset()
            return ("command", cmd) if cmd else (None, None)
        return "listening", None


# ---------------------------------------------------------------- глас
class Voice:
    def __init__(self, cfg):
        self.engine = None
        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            want = (cfg.get("voice_name") or "").lower()
            if want:
                for v in self.engine.getProperty("voices"):
                    if want in (v.name or "").lower() or want in (v.id or "").lower():
                        self.engine.setProperty("voice", v.id)
                        break
            self.engine.setProperty("rate", cfg.get("voice_rate", 175))
        except Exception as e:
            emit("info", text=f"Гласът е недостъпен ({e}); отговарям само с текст.")

    def say(self, text):
        emit("say", text=text)
        if self.engine:
            try:
                self.engine.say(text)
                self.engine.runAndWait()
            except Exception:
                pass


def record_phrase(detector=None, max_seconds=8.0, silence_after=0.9, start_timeout=3.0, stop=None):
    """Записва една фраза. Връща CLAP при двойно пляскане, None ако няма реч,
    иначе int16 масив."""
    import sounddevice as sd
    frames, started, quiet_for, waited, voiced, noise = [], False, 0.0, 0.0, 0.0, None
    n = 0
    with sd.InputStream(samplerate=SAMPLERATE, channels=1, dtype="float32", blocksize=BLOCK) as s:
        while True:
            block = s.read(BLOCK)[0][:, 0]
            n += 1
            if n % 3 == 0:
                emit("level", value=round(float(np.max(np.abs(block))), 3))
            if stop is not None and stop():
                return None
            if detector and detector.process(block, time.monotonic()):
                return CLAP
            rms = float(np.sqrt(np.mean(block ** 2)))
            noise = rms if noise is None else noise
            speaking = rms > max(0.015, noise * 3)
            if not started:
                noise = 0.9 * noise + 0.1 * rms
                waited += STEP
                if speaking:
                    started = True
                elif waited > start_timeout:
                    return None
            if started:
                frames.append(block)
                voiced += STEP if speaking else 0
                quiet_for = 0.0 if speaking else quiet_for + STEP
                if quiet_for > silence_after or len(frames) * STEP > max_seconds:
                    break
    if voiced < 0.25:  # само шум или пляскане — не пращаме за разпознаване
        return None
    return (np.clip(np.concatenate(frames), -1, 1) * 32767).astype(np.int16)


def recognize(pcm, language):
    import speech_recognition as sr
    try:
        data = sr.AudioData(pcm.tobytes(), SAMPLERATE, 2)
        return sr.Recognizer().recognize_google(data, language=language).lower()
    except sr.UnknownValueError:
        return ""
    except sr.RequestError as e:
        emit("info", text=f"Няма връзка с разпознаването на реч: {e}")
        return ""


# ---------------------------------------------------------------- действия
SYSTEM = {
    "Windows": {
        "shutdown": "shutdown /s /t 30",
        "restart": "shutdown /r /t 30",
        "cancel": "shutdown /a",
        "sleep": "rundll32.exe powrprof.dll,SetSuspendState 0,1,0",
        "lock": "rundll32.exe user32.dll,LockWorkStation",
    },
    "Darwin": {
        "shutdown": "osascript -e 'tell app \"System Events\" to shut down'",
        "restart": "osascript -e 'tell app \"System Events\" to restart'",
        "cancel": "",
        "sleep": "pmset sleepnow",
        "lock": "pmset displaysleepnow",
    },
    "Linux": {
        "shutdown": "shutdown -h +1",
        "restart": "shutdown -r +1",
        "cancel": "shutdown -c",
        "sleep": "systemctl suspend",
        "lock": "loginctl lock-session",
    },
}


def open_app(target):
    system = platform.system()
    if target.startswith(("http://", "https://")):
        webbrowser.open(target)
    elif system == "Windows":
        os.startfile(target)
    elif system == "Darwin":
        subprocess.Popen(["open", "-a", target])
    else:
        subprocess.Popen([target], start_new_session=True)


def fill(text, cfg):
    now = dt.datetime.now()
    return text.format(name=cfg.get("your_name", ""), time=now.strftime("%H:%M"),
                       date=now.strftime("%d.%m.%Y"))


def run_action(action, cfg, voice, arg=""):
    kind, target = action.get("type"), action.get("target", "")
    if action.get("reply"):  # първо казва, после действа (важно за изключване)
        voice.say(fill(action["reply"], cfg))
    try:
        if kind == "say":
            voice.say(fill(target, cfg))
        elif kind == "open_url":
            webbrowser.open(target.replace("{query}", urllib.parse.quote_plus(arg)))
        elif kind == "open_app":
            open_app(target)
        elif kind == "system":
            cmd = SYSTEM.get(platform.system(), SYSTEM["Linux"]).get(target)
            if cmd:
                subprocess.Popen(cmd, shell=True)
            else:
                voice.say("Това не се поддържа на този компютър.")
                return False
        elif kind == "shell":
            subprocess.Popen(target, shell=True)
        elif kind == "wait":
            time.sleep(float(target or 1))
    except Exception as e:
        voice.say("Не успях.")
        emit("info", text=f"Грешка: {e}")
        return False
    return True


def run_routine(cfg, voice):
    for action in cfg.get("routine", []):
        run_action(action, cfg, voice)


def match_command(text, commands):
    """Намира команда по фраза. Връща (команда, остатък от текста) или (None, '')."""
    text = text.lower().strip()
    best, best_score, rest = None, 0.0, ""
    for cmd in commands:
        for phrase in cmd["phrases"]:
            p = phrase.lower()
            if text.startswith(p):  # „търси котки“ -> остатък „котки“
                score, r = 1.0 + len(p) / 100, text[len(p):].strip()
            elif p in text:
                score, r = 0.9 + len(p) / 100, text.replace(p, "", 1).strip()
            else:
                score, r = difflib.SequenceMatcher(None, text, p).ratio(), ""
            if score > best_score:
                best, best_score, rest = cmd, score, r
    return (best, rest) if best_score >= 0.75 else (None, "")


def execute(text, cfg, voice):
    """Изпълнява команда и съобщава резултата. Връща True при успех."""
    cmd, rest = match_command(text, cfg.get("commands", []))
    if cmd is None:
        emit("result", ok=False, command=text, text=f"✗ Няма такава команда: „{text}“")
        voice.say(f"Не разбрах „{text}“.")
        return False
    emit("status", state="executing", text=text)
    ok = all([run_action(a, cfg, voice, rest) for a in cmd["actions"]])
    emit("result", ok=ok, command=text, text=("✓ Изпълнено: " if ok else "✗ Неуспешно: ") + text)
    return ok


def routine(cfg, voice):
    emit("status", state="executing", text="Сутрешна рутина")
    run_routine(cfg, voice)
    emit("result", ok=True, command="сутрешна рутина", text="✓ Изпълнено: сутрешна рутина")


# ---------------------------------------------------------------- основен цикъл
class Control:
    """Връзка между интерфейса и слушащия цикъл."""

    def __init__(self):
        import queue
        import threading
        self.paused = threading.Event()
        self.typed = queue.Queue()  # команди, написани в интерфейса


def main_loop(cfg, voice, use_clap, control=None):
    control = control or Control()
    c = cfg.get("clap", {})
    detector = ClapDetector(sensitivity=c.get("sensitivity", 6.0),
                            min_level=c.get("min_level", 0.12)) if use_clap else None
    asm = CommandAssembler(cfg["wake_words"], cfg["end_words"], cfg.get("command_timeout", 20))
    wake, end = cfg["wake_words"][0].capitalize(), cfg["end_words"][0]
    idle = f"Чакам „{wake} … {end}“" + (" или двойно пляскане" if use_clap else "")
    emit("status", state="idle", text=idle)

    mic_error = None

    def interrupt():
        return control.paused.is_set() or not control.typed.empty()

    while True:
        while not control.typed.empty():
            item = control.typed.get()
            if item == "__routine__":
                routine(cfg, voice)
            else:
                emit("heard", text=item + "  (написано)")
                execute(item, cfg, voice)
            emit("status", state="error" if mic_error else "idle", text=mic_error or idle)
        if control.paused.is_set():
            emit("status", state="paused", text="Микрофонът е на пауза")
            while control.paused.is_set() and control.typed.empty():
                time.sleep(0.2)
            emit("status", state="idle", text=idle)
            continue

        if mic_error:
            time.sleep(0.2)  # без микрофон: работят само написаните команди
            continue
        try:
            result = record_phrase(detector, stop=interrupt)
        except Exception as e:
            mic_error = f"Няма достъп до микрофона ({e}). Написаните команди работят."
            emit("status", state="error", text=mic_error)
            continue
        if asm.timed_out(time.monotonic()):
            emit("result", ok=False, command="", text=f"✗ Не чух „{end}“, командата е отменена")
            voice.say(f"Не чух „{end}“, командата е отменена.")
            emit("status", state="idle", text=idle)
        if result is CLAP:
            asm.reset()
            emit("clap")
            routine(cfg, voice)
            emit("status", state="idle", text=idle)
            continue
        if result is None:
            continue
        emit("status", state="recognizing", text="Разпознавам…")
        text = recognize(result, cfg.get("language", "bg-BG"))
        if not text:
            emit("status", state="listening" if asm.active else "idle",
                 text=f"Слушам… завърши с „{end}“" if asm.active else idle)
            continue
        emit("heard", text=text)
        status, command = asm.feed(text, time.monotonic())
        if status == "listening":
            emit("status", state="listening", text=f"Слушам… завърши с „{end}“")
        elif status == "command":
            execute(command, cfg, voice)
            emit("status", state="idle", text=idle)
        else:
            emit("status", state="idle", text=idle)


def mic_test():
    import sounddevice as sd
    print("Говори и пляскай. Пикът на пляскане трябва да е над clap.min_level. Ctrl+C за изход.")
    with sd.InputStream(samplerate=SAMPLERATE, channels=1, dtype="float32", blocksize=BLOCK) as s:
        while True:
            peak = float(np.max(np.abs(s.read(BLOCK * 5)[0])))
            print(f"{peak:5.2f} " + "#" * int(peak * 60))


def main():
    ap = argparse.ArgumentParser(description="Джарвис")
    ap.add_argument("--no-clap", action="store_true", help="само гласови команди")
    ap.add_argument("--mic-test", action="store_true", help="покажи нивата на микрофона")
    ap.add_argument("--run", action="store_true", help="пусни рутината веднага")
    ap.add_argument("--console", action="store_true", help="без прозорец, само в терминала")
    ap.add_argument("--demo", action="store_true", help="интерфейсът без микрофон (за преглед)")
    args = ap.parse_args()
    if args.mic_test:
        return mic_test()
    cfg = load_config()
    use_clap = not args.no_clap and cfg.get("clap", {}).get("enabled", True)
    if args.console:
        voice = Voice(cfg)
        if args.run:
            routine(cfg, voice)
        return main_loop(cfg, voice, use_clap)
    import jarvis_ui
    jarvis_ui.serve(cfg, use_clap, run_first=args.run, demo=args.demo)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nДовиждане.")
        sys.exit(0)
