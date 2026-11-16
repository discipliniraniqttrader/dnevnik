"""Прозорец на Джарвис: локална страница в браузъра (http://127.0.0.1:8765).

Показва дали те чува (ниво на микрофона), какво е разпознал, какво изпълнява
и дали е успял. Може и да пишеш команди, без да говориш.
"""
import json
import queue
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import jarvis

PORT = 8765
UI_FILE = Path(__file__).resolve().parent / "ui.html"


class Hub:
    """Разпраща събитията до всички отворени страници."""

    def __init__(self):
        self.lock = threading.Lock()
        self.clients = []
        self.history = []  # последните чути/изпълнени неща — за нова страница
        self.state = {"kind": "status", "state": "starting", "text": "Стартирам…"}

    def emit(self, kind, **data):
        event = {"kind": kind, "time": time.strftime("%H:%M:%S"), **data}
        with self.lock:
            if kind == "status":
                self.state = event
            elif kind != "level":
                self.history = (self.history + [event])[-100:]
            for q in list(self.clients):
                try:
                    q.put_nowait(event)
                except queue.Full:
                    pass
        if kind not in ("level",):
            jarvis._print_event(kind, **data)

    def subscribe(self):
        q = queue.Queue(maxsize=500)
        with self.lock:
            self.clients.append(q)
            backlog = [self.state] + list(self.history)
        return q, backlog

    def unsubscribe(self, q):
        with self.lock:
            if q in self.clients:
                self.clients.remove(q)


def make_handler(hub, control, cfg):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, body, ctype):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/":
                return self._send(200, UI_FILE.read_bytes(), "text/html; charset=utf-8")
            if self.path == "/config":
                info = {"wake": cfg["wake_words"][0], "end": cfg["end_words"][0],
                        "commands": [c["phrases"][0] for c in cfg.get("commands", [])]}
                return self._send(200, json.dumps(info, ensure_ascii=False).encode(), "application/json")
            if self.path == "/events":
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                q, backlog = hub.subscribe()
                try:
                    for ev in backlog:
                        self.wfile.write(f"data: {json.dumps(ev, ensure_ascii=False)}\n\n".encode())
                    self.wfile.flush()
                    while True:
                        try:
                            ev = q.get(timeout=15)
                            self.wfile.write(f"data: {json.dumps(ev, ensure_ascii=False)}\n\n".encode())
                        except queue.Empty:
                            self.wfile.write(b": ping\n\n")
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError, OSError):
                    pass
                finally:
                    hub.unsubscribe(q)
                return
            self._send(404, b"not found", "text/plain")

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            try:
                body = json.loads(self.rfile.read(length) or b"{}")
            except ValueError:
                body = {}
            action = body.get("action")
            if action == "command" and body.get("text", "").strip():
                control.typed.put(body["text"].strip().lower())
            elif action == "routine":
                control.typed.put("__routine__")
            elif action == "pause":
                control.paused.set()
            elif action == "resume":
                control.paused.clear()
            else:
                return self._send(400, b"bad request", "text/plain")
            self._send(200, b"ok", "text/plain")

    return Handler


def demo_loop(hub, control):
    """Без микрофон: показва как изглежда интерфейсът."""
    import math
    script = [
        ("status", {"state": "idle", "text": "Чакам „Джарвис … край“ или двойно пляскане"}),
        ("heard", {"text": "джарвис пусни в youtube лофи музика край"}),
        ("status", {"state": "executing", "text": "пусни в youtube лофи музика"}),
        ("say", {"text": "Пускам."}),
        ("result", {"ok": True, "command": "пусни в youtube лофи музика", "text": "✓ Изпълнено: пусни в youtube лофи музика"}),
        ("heard", {"text": "джарвис"}),
        ("status", {"state": "listening", "text": "Слушам… завърши с „край“"}),
        ("heard", {"text": "кажи ми виц край"}),
        ("result", {"ok": False, "command": "кажи ми виц", "text": "✗ Няма такава команда: „кажи ми виц“"}),
        ("clap", {}),
        ("result", {"ok": True, "command": "сутрешна рутина", "text": "✓ Изпълнено: сутрешна рутина"}),
        ("status", {"state": "idle", "text": "Чакам „Джарвис … край“ или двойно пляскане"}),
    ]
    for kind, data in script:
        hub.emit(kind, **data)
        time.sleep(0.05)
    t = 0
    while True:
        t += 1
        if not control.paused.is_set():
            hub.emit("level", value=round(abs(math.sin(t / 7)) * 0.25 + (0.5 if t % 40 == 0 else 0), 3))
        while not control.typed.empty():
            item = control.typed.get()
            hub.emit("heard", text=item + "  (написано)")
            hub.emit("result", ok=True, command=item, text="✓ (демо) " + item)
        time.sleep(0.1)


def serve(cfg, use_clap, run_first=False, demo=False, open_browser=True):
    hub = Hub()
    jarvis.set_emitter(hub.emit)
    control = jarvis.Control()

    def worker():
        if demo:
            return demo_loop(hub, control)
        voice = jarvis.Voice(cfg)  # гласът се създава в нишката, която го ползва
        if run_first:
            jarvis.routine(cfg, voice)
        try:
            jarvis.main_loop(cfg, voice, use_clap, control)
        except Exception as e:
            hub.emit("status", state="error", text=f"Грешка с микрофона: {e}")

    threading.Thread(target=worker, daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", PORT), make_handler(hub, control, cfg))
    server.daemon_threads = True
    url = f"http://127.0.0.1:{PORT}"
    print(f"Прозорецът на Джарвис: {url}  (Ctrl+C за изход)")
    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    server.serve_forever()
