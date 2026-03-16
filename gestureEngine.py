"""
Gesture Engine - OpenCV + MediaPipe
Controls OS cursor via hand gestures and streams state via WebSocket
"""

import cv2
import mediapipe as mp
import pyautogui
import asyncio
import websockets
import json
import time
import threading
import math
from dataclasses import dataclass
from typing import Optional

# ── Config ────────────────────────────────────────────────────────────────────
WEBSOCKET_HOST = "localhost"
WEBSOCKET_PORT = 8765
INACTIVE_TIMEOUT = 60          # seconds before going inactive
ACTIVE_FPS = 30                # frames per second when active
INACTIVE_FPS = 5               # frames per second when inactive
SMOOTHING = 0.15               # cursor smoothing factor (0=no smooth, 1=frozen)
PINCH_THRESHOLD = 0.08        # normalized distance for pinch detection
SCROLL_SENSITIVITY = 20        # pixels per scroll unit
MIN_PINCH_HOLD = 0.0         # seconds pinch must be held before move starts
MIN_OPEN_TIME = 0.05         # seconds hand must be open before left click fires

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0
# ── Gesture State Machine ─────────────────────────────────────────────
gesture_hold_start = 0
gesture_last = "none"

CLICK_HOLD_TIME = 0.15
SCROLL_HOLD_TIME = 0.1
# ── Data Structures ───────────────────────────────────────────────────────────
@dataclass
class GestureState:
    gesture: str = "none"          # none | move | left_click | right_click | scroll
    active: bool = False           # system active state
    cursor_x: float = 0.0
    cursor_y: float = 0.0
    fps: int = INACTIVE_FPS
    last_gesture_time: float = 0.0
    scroll_delta: float = 0.0

state = GestureState()
connected_clients: set = set()
prev_cursor_x, prev_cursor_y = 0.0, 0.0

# ── MediaPipe Setup (new API for mediapipe 0.10.30+) ─────────────────────────
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions, RunningMode
import urllib.request
import os

# Download hand landmarker model if not present
MODEL_PATH = "hand_landmarker.task"
if not os.path.exists(MODEL_PATH):
    print("[Engine] Downloading hand landmarker model...")
    urllib.request.urlretrieve(
        "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task",
        MODEL_PATH
    )
    print("[Engine] Model downloaded ✓")

options = HandLandmarkerOptions(
    base_options=mp_python.BaseOptions(model_asset_path=MODEL_PATH),
    running_mode=RunningMode.IMAGE,
    num_hands=1,
    min_hand_detection_confidence=0.7,
    min_hand_presence_confidence=0.7,
    min_tracking_confidence=0.7,
)
hands = HandLandmarker.create_from_options(options)

# Keep drawing utils via cv2 manually
def draw_landmarks_on_frame(frame, hand_landmarks_list):
    for hand_landmarks in hand_landmarks_list:
        pts = [(int(lm.x * frame.shape[1]), int(lm.y * frame.shape[0])) for lm in hand_landmarks]
        # Draw connections
        connections = [
            (0,1),(1,2),(2,3),(3,4),
            (0,5),(5,6),(6,7),(7,8),
            (0,9),(9,10),(10,11),(11,12),
            (0,13),(13,14),(14,15),(15,16),
            (0,17),(17,18),(18,19),(19,20),
            (5,9),(9,13),(13,17),
        ]
        for a, b in connections:
            cv2.line(frame, pts[a], pts[b], (0, 200, 100), 1)
        for pt in pts:
            cv2.circle(frame, pt, 3, (0, 255, 150), -1)

def get_landmark(landmarks, idx):
    lm = landmarks[idx]
    return lm.x, lm.y

def distance(p1, p2):
    return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

# ── Gesture Detection ─────────────────────────────────────────────────────────
def detect_gesture(landmarks) -> dict:
    index_tip  = get_landmark(landmarks, 8)
    thumb_tip  = get_landmark(landmarks, 4)
    middle_tip = get_landmark(landmarks, 12)
    index_mcp  = get_landmark(landmarks, 5)

    thumb_index_dist  = distance(thumb_tip, index_tip)
    thumb_middle_dist = distance(thumb_tip, middle_tip)
    index_middle_dist = distance(index_tip, middle_tip)

    # MOVE: thumb + index pinch
    if thumb_index_dist < PINCH_THRESHOLD:
        return {"gesture": "move", "point": thumb_tip}

    # RIGHT CLICK: thumb + middle pinch
    if thumb_middle_dist < PINCH_THRESHOLD:
        return {"gesture": "right_click", "point": index_tip}

    # SCROLL: only if index+middle are VERY close (raised threshold)
    # and thumb is clearly away from both (not an open hand)
    if index_middle_dist < PINCH_THRESHOLD * 1.2 and thumb_index_dist > PINCH_THRESHOLD * 2:
        mid_y = (index_tip[1] + middle_tip[1]) / 2
        return {"gesture": "scroll", "point": index_tip, "scroll_y": mid_y}

    # OPEN: everything else
    return {"gesture": "open", "point": index_tip}
# ── Cursor Control ────────────────────────────────────────────────────────────
scroll_prev_y: Optional[float] = None
prev_gesture = "none"
pinch_was_held = False
click_fired = False

def apply_gesture(gesture_data):
    global prev_cursor_x, prev_cursor_y
    global scroll_prev_y, prev_gesture
    global pinch_was_held, click_fired
    global state

    screen_w, screen_h = pyautogui.size()
    gesture = gesture_data["gesture"]
    point = gesture_data["point"]

    # ── Remap active zone to full screen ─────────────────────────────
    MARGIN = 0.2
    clamped_x = max(MARGIN, min(1.0 - MARGIN, point[0]))
    clamped_y = max(MARGIN, min(1.0 - MARGIN, point[1]))
    norm_x = (clamped_x - MARGIN) / (1.0 - 2 * MARGIN)
    norm_y = (clamped_y - MARGIN) / (1.0 - 2 * MARGIN)

    raw_x = norm_x * screen_w
    raw_y = norm_y * screen_h

    alpha = SMOOTHING
    smooth_x = prev_cursor_x * (1 - alpha) + raw_x * alpha
    smooth_y = prev_cursor_y * (1 - alpha) + raw_y * alpha
    prev_cursor_x = smooth_x
    prev_cursor_y = smooth_y

    state.cursor_x = smooth_x
    state.cursor_y = smooth_y
    state.last_gesture_time = time.time()

    # ── MOVE ─────────────────────────────────────────────────────────
    if gesture == "move":
        pyautogui.moveTo(smooth_x, smooth_y)
        pinch_was_held = True
        click_fired = False
        scroll_prev_y = None
        state.gesture = "move"

    # ── OPEN → LEFT CLICK on first frame of release ───────────────────
    elif gesture == "open":
        # Fire click exactly once when transitioning from move → open
        if pinch_was_held and not click_fired:
            pyautogui.click(smooth_x, smooth_y)
            state.gesture = "left_click"
            click_fired = True
            pinch_was_held = False
        scroll_prev_y = None

    # ── RIGHT CLICK ───────────────────────────────────────────────────
    elif gesture == "right_click":
        if prev_gesture != "right_click":
            pyautogui.rightClick(smooth_x, smooth_y)
            state.gesture = "right_click"
        pinch_was_held = False
        click_fired = False
        scroll_prev_y = None

    # ── SCROLL ────────────────────────────────────────────────────────
    elif gesture == "scroll":
        scroll_y = gesture_data.get("scroll_y", point[1])
        if scroll_prev_y is not None:
            delta = (scroll_prev_y - scroll_y) * SCROLL_SENSITIVITY * 120
            if abs(delta) > 2:
                pyautogui.scroll(int(delta))
                state.scroll_delta = delta
        scroll_prev_y = scroll_y
        pinch_was_held = False
        click_fired = False
        state.gesture = "scroll"

    prev_gesture = gesture
# ── Active / Inactive Management ─────────────────────────────────────────────
def check_activity():
    """Background thread that flips active/inactive based on gesture timeout."""
    while True:
        elapsed = time.time() - state.last_gesture_time
        if state.active and elapsed > INACTIVE_TIMEOUT:
            state.active = False
            state.fps = INACTIVE_FPS
            print("[Engine] → INACTIVE (timeout)")
        time.sleep(1)

# ── WebSocket Server ──────────────────────────────────────────────────────────
async def broadcast(message: dict):
    if connected_clients:
        data = json.dumps(message)
        await asyncio.gather(
            *[client.send(data) for client in connected_clients],
            return_exceptions=True
        )

async def ws_handler(websocket, path="/"):
    connected_clients.add(websocket)
    print(f"[WS] Client connected: {websocket.remote_address}")
    try:
        async for message in websocket:
            try:
                cmd = json.loads(message)
                if cmd.get("action") == "enable":
                    state.active = True
                    state.fps = ACTIVE_FPS
                    state.last_gesture_time = time.time()
                    print("[Engine] → ACTIVE (command)")
                elif cmd.get("action") == "disable":
                    state.active = False
                    state.fps = INACTIVE_FPS
                    print("[Engine] → INACTIVE (command)")
            except json.JSONDecodeError:
                pass
    finally:
        connected_clients.discard(websocket)
        print(f"[WS] Client disconnected")

async def ws_server():
    async with websockets.serve(ws_handler, WEBSOCKET_HOST, WEBSOCKET_PORT):
        print(f"[WS] Server listening on ws://{WEBSOCKET_HOST}:{WEBSOCKET_PORT}")
        await asyncio.Future()  # run forever

# ── Main Capture Loop ─────────────────────────────────────────────────────────
def run_capture(loop):
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    print("[Engine] Camera started")

    while cap.isOpened():
        target_fps = state.fps
        frame_delay = 1.0 / target_fps

        start = time.time()
        ret, frame = cap.read()
        frame = cv2.flip(frame, 1)
        frame = cv2.resize(frame, (640, 480))
        if not ret:
            break

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        results = hands.detect(mp_image)

        gesture_info = {"gesture": "none"}

        if results.hand_landmarks:
            draw_landmarks_on_frame(frame, results.hand_landmarks)
            gesture_info = detect_gesture(results.hand_landmarks[0])

            # Only apply gestures if enabled from frontend
            if state.active:
                apply_gesture(gesture_info)

        # Broadcast state over WebSocket
        payload = {
            "gesture": state.gesture,
            "active": state.active,
            "fps": state.fps,
            "cursor_x": state.cursor_x,
            "cursor_y": state.cursor_y,
            "scroll_delta": state.scroll_delta,
            "timestamp": time.time(),
        }
        asyncio.run_coroutine_threadsafe(broadcast(payload), loop)
        state.gesture = "none"
        state.scroll_delta = 0.0

        # Display overlay
        status = "ACTIVE" if state.active else "INACTIVE"
        color = (0, 255, 100) if state.active else (100, 100, 100)
        cv2.putText(frame, f"Status: {status} | FPS: {target_fps} | {gesture_info['gesture'].upper()}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.imshow("Gesture Engine", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        processing_time = time.time() - start
        sleep_time = max(0, frame_delay - processing_time)
        time.sleep(sleep_time)

    cap.release()
    cv2.destroyAllWindows()

# ── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    loop = asyncio.new_event_loop()

    # Start activity monitor
    activity_thread = threading.Thread(target=check_activity, daemon=True)
    activity_thread.start()

    # Start WebSocket server in async loop
    ws_thread = threading.Thread(
        target=lambda: loop.run_until_complete(ws_server()),
        daemon=True
    )
    ws_thread.start()

    # Give WS server a moment to start
    time.sleep(0.5)

    # Run capture in main thread
    run_capture(loop)