#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fuckZHS 扫码登录网页服务

在服务器上提供一个小网页，用手机扫页面上的二维码完成登录。
解决「无人值守时 cookies 失效、需要人工扫码但拿不到二维码」的问题。

安全设计（二维码就是登录凭据，谁看到谁就能登这个号）：
  * 所有路径都带一个随机 secret，首次启动时生成，存在 data/qr_web_secret（600）
  * 不带 secret 的请求一律 404，不泄露任何信息
  * 二维码只在登录进行中存在，登录成功后立即停止提供
  * 建议只在需要登录时开着，登录完把端口关掉

环境变量：
  ZHS_QR_PORT   监听端口，默认 18080
  ZHS_APP_DIR   实例目录，默认 /opt/fuckzhs
"""
import http.server
import json
import os
import re
import secrets
import subprocess
import sys
import threading
import time

APP_DIR = os.environ.get("ZHS_APP_DIR", "/opt/fuckzhs")
QR_DIR = os.path.join(APP_DIR, "data", "qr")
PY = os.path.join(APP_DIR, ".venv", "bin", "python")
MAIN = os.path.join(APP_DIR, "main.py")
SECRET_FILE = os.path.join(APP_DIR, "data", "qr_web_secret")
LOGIN_LOG = os.path.join(APP_DIR, "data", "qr_web_login.out")
PORT = int(os.environ.get("ZHS_QR_PORT", "18080"))

_lock = threading.Lock()
_login_proc = None
_cookie_cache = {"t": 0.0, "ok": None, "msg": ""}


def get_secret() -> str:
    if not os.path.exists(SECRET_FILE):
        os.makedirs(os.path.dirname(SECRET_FILE), exist_ok=True)
        with open(SECRET_FILE, "w", encoding="utf-8") as f:
            f.write(secrets.token_urlsafe(24))
        os.chmod(SECRET_FILE, 0o600)
    with open(SECRET_FILE, encoding="utf-8") as f:
        return f.read().strip()


def latest_qr():
    """返回最新的二维码文件路径与生成时间；没有则返回 (None, None)。"""
    try:
        files = [os.path.join(QR_DIR, n) for n in os.listdir(QR_DIR) if n.endswith(".png")]
    except OSError:
        return None, None
    if not files:
        return None, None
    newest = max(files, key=os.path.getmtime)
    return newest, os.path.getmtime(newest)


def login_running() -> bool:
    with _lock:
        if _login_proc is None:
            return False
        if _login_proc.poll() is None:
            return True
    # 进程已退出：顺便清理旧二维码，避免过期码被误扫
    return False


def cookie_ok(force=False):
    """调用 check_login.py 判断登录态，结果缓存 30 秒。"""
    now = time.time()
    if not force and _cookie_cache["ok"] is not None and now - _cookie_cache["t"] < 30:
        return _cookie_cache["ok"], _cookie_cache["msg"]
    ok, msg = None, ""
    try:
        r = subprocess.run(
            [PY, os.path.join(APP_DIR, "deploy", "check_login.py"), APP_DIR],
            capture_output=True, timeout=40, cwd=APP_DIR)
        out = (r.stdout or b"").decode("utf-8", "replace").strip().splitlines()
        msg = out[-1] if out else "(无输出)"
        ok = msg.startswith("LOGIN_OK")
    except Exception as e:
        msg = "检查失败: %s" % e
        ok = False
    _cookie_cache.update(t=now, ok=ok, msg=msg)
    return ok, msg


def start_login() -> str:
    global _login_proc
    with _lock:
        if _login_proc is not None and _login_proc.poll() is None:
            return "已在运行"
        try:
            for n in os.listdir(QR_DIR):
                if n.endswith(".png"):
                    os.remove(os.path.join(QR_DIR, n))
        except OSError:
            pass
        os.makedirs(QR_DIR, exist_ok=True)
        env = dict(os.environ)
        env.update({
            "TIKTOKEN_CACHE_DIR": os.path.join(APP_DIR, "data", "tiktoken-cache"),
            "LANG": "C.UTF-8",
            "PYTHONIOENCODING": "utf-8",
        })
        log = open(LOGIN_LOG, "wb")
        _login_proc = subprocess.Popen(
            [PY, MAIN, "--fetch", "--show_in_terminal", "--image_path", QR_DIR],
            cwd=APP_DIR, env=env, stdout=log, stderr=subprocess.STDOUT)
        return "已启动"


PAGE = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>fuckZHS 扫码登录</title>
<style>
  :root{color-scheme:dark}
  *{box-sizing:border-box}
  body{margin:0;background:#0e1116;color:#e6edf3;min-height:100vh;
       font-family:"Segoe UI",system-ui,"Microsoft YaHei",sans-serif;
       display:flex;flex-direction:column;align-items:center;justify-content:center;
       gap:16px;padding:28px}
  h1{font-size:17px;font-weight:600;margin:0}
  .card{background:#fff;padding:14px;border-radius:12px;line-height:0;
        box-shadow:0 0 0 1px #30363d,0 8px 24px rgba(0,0,0,.5)}
  img{display:block;width:330px;height:330px;image-rendering:pixelated}
  .st{font-size:14px;font-variant-numeric:tabular-nums}
  .ok{color:#4ade80}.warn{color:#fbbf24}.bad{color:#f87171}.dim{color:#8b949e}
  a.btn{display:inline-block;background:#238636;color:#fff;text-decoration:none;
        padding:11px 26px;border-radius:8px;font-size:15px;font-weight:600}
  a.btn:hover{background:#2ea043}
  .hint{font-size:12px;color:#8b949e;text-align:center;line-height:1.8;max-width:430px}
  code{background:#161b22;padding:1px 5px;border-radius:4px;color:#79c0ff}
</style></head><body>
  <h1>智慧树登录二维码</h1>
  __BODY__
  <div class="hint">
    用手机「智慧树」或「知到」App 的<b>扫一扫</b>扫描上方二维码。<br>
    页面每 4 秒自动刷新，过期会自动换成新的。
  </div>
<script>
setTimeout(function(){location.reload()},4000);
</script>
</body></html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def log_message(self, *a):
        pass

    def _send(self, code, ctype, body, extra=None):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        sec = get_secret()
        path = self.path.split("?")[0]

        # 所有路径都必须带正确 secret，否则一律 404
        if not path.startswith("/" + sec + "/"):
            self._send(404, "text/plain; charset=utf-8", b"not found")
            return
        sub = path[len(sec) + 2:]

        if sub == "qr.png":
            f, _ = latest_qr()
            if not f or not login_running():
                self._send(404, "text/plain; charset=utf-8", b"no qr")
                return
            try:
                with open(f, "rb") as fp:
                    self._send(200, "image/png", fp.read())
            except OSError:
                self._send(404, "text/plain; charset=utf-8", b"no qr")
            return

        if sub == "start":
            msg = start_login()
            _cookie_cache["ok"] = None  # 让下次状态检查重新跑
            self._send(200, "text/html; charset=utf-8",
                       PAGE.replace("__BODY__",
                                    '<div class="st warn">%s，正在生成二维码…</div>' % msg))
            return

        # 首页
        running = login_running()
        f, mt = latest_qr()
        ck, ckmsg = cookie_ok()

        if ck is True and not running:
            body = ('<div class="st ok">✅ 登录态有效</div>'
                    '<div class="st dim" style="font-size:12px">%s</div>' % ckmsg)
        elif running and f:
            age = int(time.time() - mt)
            body = ('<div class="card"><img src="/%s/qr.png?t=%d" alt="登录二维码"></div>'
                    '<div class="st %s">二维码已生成 %d 秒（有效期约 180 秒）</div>'
                    % (sec, int(time.time()), "ok" if age < 140 else "warn", age))
        elif running:
            body = '<div class="st warn">正在生成二维码…</div>'
        else:
            body = ('<div class="st bad">登录态已失效</div>'
                    '<a class="btn" href="/%s/start">开始扫码登录</a>' % sec)
            if ckmsg:
                body += '<div class="st dim" style="font-size:12px">%s</div>' % ckmsg

        self._send(200, "text/html; charset=utf-8", PAGE.replace("__BODY__", body))


class Server(http.server.ThreadingHTTPServer):
    # ThreadingHTTPServer = ThreadingMixIn + HTTPServer，已经设了 daemon_threads
    allow_reuse_address = True


if __name__ == "__main__":
    os.makedirs(QR_DIR, exist_ok=True)
    sec = get_secret()
    with Server(("0.0.0.0", PORT), Handler) as httpd:
        print("listening on 0.0.0.0:%d" % PORT, flush=True)
        print("url: http://<server-ip>:%d/%s/" % (PORT, sec), flush=True)
        httpd.serve_forever()
