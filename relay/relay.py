"""
SENTINEL — Local Relay Script
==============================
Run this on the machine that is on the same network as your camera.
It captures the camera and serves it as an MJPEG stream on port 5001.

Usage:
  1. Edit config.json with your camera source
  2. Run: python relay.py
  3. Start Cloudflare tunnel: cloudflared tunnel --url http://localhost:5001
  4. Copy the https://xxxx.trycloudflare.com URL
  5. Add /stream to the end and paste it into the Sentinel admin panel
"""

import json
import os
import sys
import time
import threading

import cv2
from flask import Flask, Response
from flask_cors import CORS

# ── Config ─────────────────────────────────────────────────────────────────────

CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.json')

def load_config():
    if not os.path.exists(CONFIG_FILE):
        print(f'[ERROR] config.json not found at {CONFIG_FILE}')
        print('[INFO]  Copy config.example.json to config.json and edit it.')
        sys.exit(1)
    with open(CONFIG_FILE) as f:
        return json.load(f)

config     = load_config()
CAMERA_SRC = config.get('camera_source', '0')   # '0' = webcam, or RTSP URL
PORT       = int(config.get('port', 5001))
QUALITY    = int(config.get('jpeg_quality', 75))  # 1-100
FPS_CAP    = int(config.get('fps_cap', 25))

# Convert '0' string to integer for webcam index
if isinstance(CAMERA_SRC, str) and CAMERA_SRC.isdigit():
    CAMERA_SRC = int(CAMERA_SRC)

# ── Camera thread ──────────────────────────────────────────────────────────────

class Camera:
    """
    Runs a background thread that continuously reads camera frames.
    Multiple HTTP clients share the same capture object (no duplicate opens).
    Auto-reconnects if the camera drops.
    """
    def __init__(self, src):
        self.src     = src
        self._frame  = None
        self._lock   = threading.Lock()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        while True:
            print(f'[RELAY] Connecting to camera: {self.src}')
            cap = cv2.VideoCapture(self.src)

            if not cap.isOpened():
                print('[RELAY] Camera not available — retrying in 5 s...')
                time.sleep(5)
                continue

            print('[RELAY] Camera connected.')
            while True:
                ok, frame = cap.read()
                if not ok:
                    print('[RELAY] Frame read failed — reconnecting...')
                    break
                with self._lock:
                    self._frame = frame
            cap.release()
            time.sleep(2)

    def get_frame(self):
        with self._lock:
            return self._frame.copy() if self._frame is not None else None


camera = Camera(CAMERA_SRC)

# ── Connection tracking ────────────────────────────────────────────────────────
active_connections = 0
connections_lock   = threading.Lock()
MAX_CONNECTIONS    = 15  # hard ceiling

# ── Flask app ──────────────────────────────────────────────────────────────────

app = Flask(__name__)
CORS(app)   # allow the Render app to embed the stream cross-origin

def generate():
    """Yield MJPEG frames for one viewer. Tracks connection count and cleans up on disconnect."""
    global active_connections
    interval      = 1.0 / FPS_CAP
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, QUALITY]

    with connections_lock:
        active_connections += 1
        count = active_connections
    print(f'[RELAY] Viewer connected — active: {count}')

    try:
        last_frame = None
        while True:
            frame = camera.get_frame()
            if frame is None:
                time.sleep(0.1)
                continue

            # Skip encoding if frame hasn't changed (saves CPU at low FPS cap)
            if last_frame is not None and frame.data == last_frame.data:
                time.sleep(interval)
                continue
            last_frame = frame

            ok, buf = cv2.imencode('.jpg', frame, encode_params)
            if not ok:
                continue

            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n'
                + buf.tobytes()
                + b'\r\n'
            )
            time.sleep(interval)
    except GeneratorExit:
        pass
    finally:
        with connections_lock:
            active_connections -= 1
            count = active_connections
        print(f'[RELAY] Viewer disconnected — active: {count}')


@app.route('/stream')
def stream():
    with connections_lock:
        if active_connections >= MAX_CONNECTIONS:
            return 'Stream at capacity', 503
    return Response(
        generate(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/health')
def health():
    """Simple health-check endpoint."""
    frame = camera.get_frame()
    return {
        'status'     : 'ok',
        'camera'     : frame is not None,
        'viewers'    : active_connections,
        'capacity'   : MAX_CONNECTIONS
    }


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print('=' * 50)
    print(f'  SENTINEL Relay')
    print(f'  Camera : {CAMERA_SRC}')
    print(f'  Stream : http://localhost:{PORT}/stream')
    print(f'  Health : http://localhost:{PORT}/health')
    print('=' * 50)
    print()
    print('  Next step: open a second terminal and run:')
    print('  cloudflared tunnel --url http://localhost:' + str(PORT))
    print()
    app.run(host='0.0.0.0', port=PORT, debug=False, threaded=True)
