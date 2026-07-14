"""
n8n ↔ 流水线 Webhook 桥
供 n8n 调用的 HTTP API，接收外部输入并触发流水线处理
"""

import os, sys, json, traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HOST = "127.0.0.1"
PORT = 9876


def _decode_body(raw: bytes) -> dict:
    """尝试多种编码解析 JSON 请求体"""
    for enc in ("utf-8", "gbk", "gb2312", "gb18030"):
        try:
            return json.loads(raw.decode(enc))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    return {}


class BridgeHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b"{}"
        data = _decode_body(body)

        if path == "/process":
            self._handle_process(data)
        elif path == "/ping":
            self._send_json({"status": "ok"})
        else:
            self._send_json({"error": f"未知路径: {path}"}, 404)

    def _handle_process(self, data: dict):
        from main import process_url, process_file, process_content
        file_path = data.get("file", "")
        url = data.get("url", "")
        text = data.get("text", "")
        source = data.get("source", "n8n")

        try:
            result = None
            if file_path and os.path.exists(file_path):
                process_file(file_path)
                result = {"status": "done", "file": file_path}
            elif url:
                process_url(url)
                result = {"status": "done", "url": url}
            elif text:
                output = process_content(text, source)
                result = {"status": "done", "length": len(output) if output else 0}
            else:
                self._send_json({"error": "请提供 file / url / text 之一"}, 400)
                return
            self._send_json(result)
        except Exception as e:
            self._send_json({"error": str(e), "traceback": traceback.format_exc()}, 500)

    def _send_json(self, data: dict, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def log_message(self, fmt, *args):
        pass


def start_bridge():
    server = HTTPServer((HOST, PORT), BridgeHandler)
    print(f"🌉 Webhook Bridge: http://{HOST}:{PORT}")
    print(f"   POST /process - {{\"url\":\"...\"}} / {{\"file\":\"...\"}} / {{\"text\":\"...\"}}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n⏹  Bridge 已停止")
        server.server_close()


if __name__ == "__main__":
    start_bridge()
