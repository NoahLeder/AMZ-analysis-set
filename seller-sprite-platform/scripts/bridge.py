#!/usr/bin/env python3
"""SellerSprite AI Platform - Bridge Server

Architecture:
  Browser (Web UI) <-> Bridge Server (this) <-> Codex (skill) <-> SellerSprite MCP

Usage: python bridge.py
URL:   http://127.0.0.1:9876
"""

import http.server
import io
import json
import os
import sys
import threading
import time
import uuid
import webbrowser
from urllib.parse import urlparse

# Force UTF-8 stdout for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

HOST = "127.0.0.1"
PORT = 9876
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "ui")

# ---- SSE Connection Management ----
sse_clients = []

class SSEClient:
    def __init__(self, wfile):
        self.id = str(uuid.uuid4())[:8]
        self.wfile = wfile
        self.alive = True

def broadcast_sse(event, data):
    dead = []
    for c in sse_clients:
        try:
            c.wfile.write(f"event: {event}\n".encode())
            c.wfile.write(f"data: {json.dumps(data, ensure_ascii=False)}\n\n".encode())
            c.wfile.flush()
        except Exception:
            c.alive = False
            dead.append(c)
    for c in dead:
        sse_clients.remove(c)

# ---- Analysis Task Handling ----
def handle_analysis(module, params, request_id):
    tasks_dir = os.path.join(os.path.dirname(__file__), "..", "tasks")
    os.makedirs(tasks_dir, exist_ok=True)

    task_file = os.path.join(tasks_dir, f"{request_id}.json")
    result_file = os.path.join(tasks_dir, f"{request_id}_result.json")

    task = {
        "id": request_id,
        "module": module,
        "params": params,
        "status": "pending",
        "created_at": time.time()
    }
    with open(task_file, "w", encoding="utf-8") as f:
        json.dump(task, f, ensure_ascii=False, indent=2)

    broadcast_sse("task_submitted", {"requestId": request_id, "status": "pending"})

    def poll_result():
        timeout = 120
        start = time.time()
        while time.time() - start < timeout:
            if os.path.exists(result_file):
                try:
                    with open(result_file, "r", encoding="utf-8") as f:
                        result = json.load(f)
                    result["requestId"] = request_id
                    broadcast_sse("result", result)
                    os.remove(result_file)
                    os.remove(task_file)
                    return
                except (json.JSONDecodeError, IOError):
                    pass
            time.sleep(1)

        broadcast_sse("error", {
            "requestId": request_id,
            "error": "Analysis timeout. Ensure Codex is running with SellerSprite MCP configured."
        })
        if os.path.exists(task_file):
            os.remove(task_file)

    threading.Thread(target=poll_result, daemon=True).start()
    return task


class BridgeHandler(http.server.BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        print(f"[Bridge] {args[0]}")

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def _send_sse_headers(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def _serve_static(self, path):
        if path == "/" or path == "":
            path = "/index.html"
        file_path = os.path.join(ASSETS_DIR, path.lstrip("/"))
        if os.path.exists(file_path) and os.path.isfile(file_path):
            ct = "text/html"
            if file_path.endswith(".css"): ct = "text/css"
            elif file_path.endswith(".js"): ct = "application/javascript"
            elif file_path.endswith(".json"): ct = "application/json"
            with open(file_path, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", ct)
            self.send_header("Content-Length", len(data))
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/sse":
            self._send_sse_headers()
            client = SSEClient(self.wfile)
            sse_clients.append(client)
            self.wfile.write(f"event: connected\ndata: {{\"clientId\":\"{client.id}\"}}\n\n".encode())
            self.wfile.flush()
            while client.alive:
                try:
                    self.wfile.write(": keepalive\n\n".encode())
                    self.wfile.flush()
                    time.sleep(15)
                except Exception:
                    client.alive = False
                    break
            if client in sse_clients:
                sse_clients.remove(client)
            return

        if parsed.path == "/api/status":
            self._send_json({
                "status": "running",
                "connectedClients": len([c for c in sse_clients if c.alive]),
                "pendingTasks": len([f for f in os.listdir(os.path.join(os.path.dirname(__file__), "..", "tasks")) if f.endswith(".json") and not f.endswith("_result.json")]) if os.path.exists(os.path.join(os.path.dirname(__file__), "..", "tasks")) else 0,
                "modules": [
                    "product-research", "competitor-analysis", "keyword-research",
                    "advertising-analytics", "listing-generator", "review-analysis",
                    "price-monitor", "dashboard"
                ]
            })
            return
        if parsed.path == "/api/pending-tasks":
            tasks_dir = os.path.join(os.path.dirname(__file__), "..", "tasks")
            os.makedirs(tasks_dir, exist_ok=True)
            tasks = []
            for f in os.listdir(tasks_dir):
                if f.endswith(".json") and not f.endswith("_result.json"):
                    p = os.path.join(tasks_dir, f)
                    try:
                        with open(p, "r", encoding="utf-8") as tf:
                            task = json.load(tf)
                            task["_file"] = f
                            tasks.append(task)
                    except (json.JSONDecodeError, IOError):
                        pass
            self._send_json({"pendingTasks": tasks, "count": len(tasks)})
            return


        if parsed.path == "/api/tasks":
            tasks_dir = os.path.join(os.path.dirname(__file__), "..", "tasks")
            os.makedirs(tasks_dir, exist_ok=True)
            tasks = []
            for f in os.listdir(tasks_dir):
                if f.endswith(".json") and not f.endswith("_result.json"):
                    p = os.path.join(tasks_dir, f)
                    with open(p, "r", encoding="utf-8") as tf:
                        tasks.append(json.load(tf))
            self._send_json({"tasks": tasks})
            return

        self._serve_static(parsed.path)

    def do_POST(self):
        parsed = urlparse(self.path)

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length else b"{}"
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON"}, 400)
            return

        api_routes = [
            "/api/product-research",
            "/api/competitor-analysis",
            "/api/keyword-research",
            "/api/advertising-analytics",
            "/api/listing-generator",
            "/api/review-analysis",
            "/api/price-monitor",
            "/api/dashboard",
        ]

        if parsed.path in api_routes:
            module = parsed.path.replace("/api/", "")
            request_id = str(uuid.uuid4())[:12]
            handle_analysis(module, data, request_id)
            self._send_json({
                "requestId": request_id,
                "status": "submitted",
                "message": "Task submitted. Codex + SellerSprite MCP analysis in progress..."
            })
            return

        if parsed.path == "/api/submit-result":
            request_id = data.get("requestId", "")
            tasks_dir = os.path.join(os.path.dirname(__file__), "..", "tasks")
            result_file = os.path.join(tasks_dir, f"{request_id}_result.json")
            os.makedirs(tasks_dir, exist_ok=True)
            with open(result_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self._send_json({"status": "ok"})
            return

        self._send_json({"error": "Unknown endpoint"}, 404)


def main():
    os.makedirs(ASSETS_DIR, exist_ok=True)

    server = http.server.HTTPServer((HOST, PORT), BridgeHandler)
    url = f"http://{HOST}:{PORT}"
    print(f"\n  [AMZ analysis set]")
    print(f"  Bridge Server: {url}")
    print(f"  Press Ctrl+C to stop\n")

    threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.")
        server.shutdown()


if __name__ == "__main__":
    main()
