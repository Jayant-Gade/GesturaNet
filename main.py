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
gesture_triggered = False     # Locks the custom gesture click
mouse_mode = False            # When False, pinch movement is disabled

# --- GESTURE TIMERS ---
play_pause_start = 0          # Tracks how long hand is in Open Palm
play_pause_cooldown = 0       # Prevents double triggers
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
        global mouse_mode, play_pause_start, play_pause_cooldown
        
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
        
        # Draw the control box always
        pt1_x, pt1_y, pt2_x, pt2_y = controller.get_box()
        box_color = (0, 255, 0) if system_engaged else (0, 0, 255)
        if not mouse_mode: box_color = (128, 128, 128) # Gray if mouse mode is off
        cv2.rectangle(img, (int(pt1_x), int(pt1_y)), (int(pt2_x), int(pt2_y)), box_color, 2)
        cv2.putText(img, f"MOUSE BOX ({'ON' if mouse_mode else 'OFF'})", (int(pt1_x), int(pt1_y)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 1)

        # --- PROCESS VOICE RECOGNITION (GLOBAL) ---
        v_cmd = voice_listener.get_command()
        if v_cmd == "mouse_on": mouse_mode = True
        elif v_cmd == "mouse_off": mouse_mode = False

        if len(lm_list) != 0:
            fingers = tracker.fingers_up(lm_list)
            
            # --- EDGE DETECTION RESET ---
            if fingers != [0, 0, 0, 0, 0]: # Reset if hand is seen
                # We handle gesture_triggered inside the loop now
                pass

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
                
                # Voice Mouse Actions (Only if system_engaged)
                if v_cmd == "click":
                    controller.left_click()
                elif v_cmd == "hold":
                    controller.mouse_down()
                elif v_cmd == "release":
                    controller.mouse_up()

                # --- MOUSE MODE & PINCH ---
                if mouse_mode:
                    thumb_tip = lm_list[4]
                    index_tip = lm_list[8]
                    dist = np.hypot(index_tip[1] - thumb_tip[1], index_tip[2] - thumb_tip[2])
                    if dist < 40:
                        controller.move_mouse(index_tip[1], index_tip[2])
                        cv2.circle(img, (index_tip[1], index_tip[2]), 15, (0, 255, 0), cv2.FILLED)
                        cv2.putText(img, "GRABBED", (index_tip[1]+20, index_tip[2]), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                else:
                    cv2.putText(img, "MOUSE MODE: OFF (Say 'Mouse Mode' to start)", (10, 410), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

                # --- DYNAMIC GESTURE MAPPING (PLAY/PAUSE DELAY) ---
                is_palm = (fingers == [1, 1, 1, 1, 1])
                
                if is_palm:
                    if play_pause_start == 0:
                        play_pause_start = time.time()
                    
                    elapsed = time.time() - play_pause_start
                    # Target depends on state: 2s to Play, 1s to Pause
                    # We'll use a 1.5s middle ground or just check if media is playing?
                    # Since we don't know media state, we'll use 2 seconds of hold to toggle.
                    target_time = 2.0 
                    
                    # Visual Feedback for the hold
                    bar_width = int(np.interp(elapsed, [0, target_time], [0, 200]))
                    cv2.rectangle(img, (220, 400), (220 + bar_width, 410), (0, 255, 255), cv2.FILLED)
                    cv2.putText(img, "HOLD PALM...", (220, 390), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

                    if elapsed > target_time and (time.time() - play_pause_cooldown > 2.0):
                        controller.play_pause()
                        play_pause_cooldown = time.time()
                        print("GESTURE: Play/Pause Triggered!")
                else:
                    play_pause_start = 0

                # Other gestures (like click remapping)
                for action_name, saved_gesture in cfg.config.items():
                    if action_name == "click" and fingers == saved_gesture:
                        if not gesture_triggered:
                            controller.left_click()
                            gesture_triggered = True
                    # release trigger logic
                    if fingers != saved_gesture: gesture_triggered = False

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