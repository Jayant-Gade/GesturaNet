import cv2
import time
import numpy as np
import keyboard  
from hand_tracker import HandTracker
from actions import ActionController
from config_manager import ConfigManager
from voice import VoiceListener

# GLOBAL VARIABLES
camera_active = True
system_engaged = False  
last_toggle_time = 0    

# --- STATE FLAGS (Fixes Machine-Gun Clicking) ---
last_app_time = 0
pinky_hold_start = 0 
pinch_triggered = False       # Locks the pinch click
last_gesture_seen = None      # Remembers your hand shape
gesture_triggered = False     # Locks the custom gesture click

# --- VOICE & CLICK CONFIG ---
next_click_source = "voice"   # Alternates: "voice" -> "gesture" -> "voice"
voice_listener = VoiceListener()

def toggle_camera():
    global camera_active
    camera_active = not camera_active
    print(f"--- Camera Active: {camera_active} ---")

keyboard.add_hotkey('ctrl+shift+g', toggle_camera)

def main():
    global system_engaged, last_toggle_time, last_app_time, pinky_hold_start
    global pinch_triggered, last_gesture_seen, gesture_triggered, next_click_source
    
    # Start voice listening
    voice_listener.start()

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    tracker = HandTracker(detection_con=0.5, track_con=0.5)
    controller = ActionController()
    cfg = ConfigManager() 
    
    p_time = 0

    while cap.isOpened():
        if not camera_active:
            black_img = np.zeros((480, 640, 3), np.uint8)
            cv2.putText(black_img, "PRIVACY MODE: ON", (150, 220), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.imshow("GesturaNet Main Engine", black_img)
            if cv2.waitKey(1) & 0xFF == ord('q'): break
            continue

        success, img = cap.read()
        if not success: break

        img = cv2.flip(img, 1)
        img = tracker.find_hands(img, draw=False)
        lm_list = tracker.get_position(img)
        
        if len(lm_list) != 0:
            fingers = tracker.fingers_up(lm_list)
            
            # --- EDGE DETECTION RESET ---
            # If your fingers change shape, unlock the gesture click!
            if fingers != last_gesture_seen:
                gesture_triggered = False
                last_gesture_seen = fingers

            # --- DEBOUNCED PINKY TOGGLE ---
            if fingers == [0, 0, 0, 0, 1]:
                if pinky_hold_start == 0:
                    pinky_hold_start = time.time()
                elif (time.time() - pinky_hold_start > 0.5) and (time.time() - last_toggle_time > 1.5):
                    system_engaged = not system_engaged
                    last_toggle_time = time.time()
                    if system_engaged:
                        controller.center_box(lm_list[8][1], lm_list[8][2])
            else:
                pinky_hold_start = 0

            # --- MAIN EXECUTION LAYER ---
            if system_engaged:
                cv2.putText(img, "STATUS: ACTIVE", (10, 450), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # --- PROCESS VOICE RECOGNITION ---
                v_cmd = voice_listener.get_command()
                if v_cmd == "click" and next_click_source == "voice":
                    print("VOICE: Click recognized! Now waiting for gesture click...")
                    controller.left_click()
                    next_click_source = "gesture"

                pt1_x, pt1_y, pt2_x, pt2_y = controller.get_box()
                cv2.rectangle(img, (int(pt1_x), int(pt1_y)), (int(pt2_x), int(pt2_y)), (255, 0, 255), 2)

                thumb_tip = lm_list[4]
                index_tip = lm_list[8]
                dist = np.hypot(index_tip[1] - thumb_tip[1], index_tip[2] - thumb_tip[2])

                # --- SINGLE-SHOT PINCH CLICK ---
                if dist < 40:
                    if not pinch_triggered and next_click_source == "gesture":
                        print(f"PINCH CLICK! Dist: {int(dist)}. Now waiting for voice click...")
                        controller.left_click()
                        pinch_triggered = True # Lock it until fingers separate!
                        next_click_source = "voice"
                    cv2.circle(img, (index_tip[1], index_tip[2]), 15, (0, 255, 0), cv2.FILLED)
                else:
                    pinch_triggered = False # Unlock pinch when fingers separate
                
                # --- DYNAMIC GESTURE MAPPING ---
                for action_name, saved_gesture in cfg.config.items():
                    if action_name == "paths": continue 
                    # Only allow explicit features for right now:
                    if action_name not in ["click", "play_pause"]: continue
                    
                    if fingers == saved_gesture:
                        if action_name == "click":
                            # --- SINGLE-SHOT GESTURE CLICK ---
                            if not gesture_triggered and next_click_source == "gesture":
                                print("GESTURE: Single-Shot Click. Now waiting for voice click...")
                                controller.left_click()
                                gesture_triggered = True # Lock it until fingers change shape!
                                next_click_source = "voice"

                        elif action_name == "play_pause" and (time.time() - last_app_time > 2.0):
                            controller.play_pause()
                            last_app_time = time.time()
            else:
                cv2.putText(img, "STATUS: STANDBY (Hold Pinky to Toggle)", (10, 450), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        c_time = time.time()
        fps = 1 / (c_time - p_time)
        p_time = c_time
        cv2.putText(img, f'FPS: {int(fps)}', (10, 50), cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 0), 2)

        cv2.imshow("GesturaNet Main Engine", img)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()