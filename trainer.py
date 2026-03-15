import cv2
import numpy as np
import tkinter as tk
from tkinter import filedialog, simpledialog
from hand_tracker import HandTracker
from config_manager import ConfigManager

def get_app_input():
    """Opens pop-up boxes to get a new App Name and File Path."""
    root = tk.Tk()
    root.withdraw() 
    action_name = simpledialog.askstring("Input", "Enter App Name (e.g. Chrome, VLC):")
    
    if action_name:
        file_path = filedialog.askopenfilename(title="Select Application Executable", 
                                              filetypes=[("Executable files", "*.exe"), ("All files", "*.*")])
        root.destroy()
        return action_name.lower(), file_path
    root.destroy()
    return None, None

def get_system_input():
    """Opens a clean UI menu to select a system control to remap."""
    root = tk.Tk()
    root.withdraw() 

    dialog = tk.Toplevel()
    dialog.title("Map System Control")
    dialog.geometry("300x300")
    dialog.configure(bg="#2C3E50")
    
    tk.Label(dialog, text="Select Action to Remap:", font=("Helvetica", 12, "bold"), 
             bg="#2C3E50", fg="white").pack(pady=15)

    actions = ["click", "browser", "close_app", "play_pause", "volume_up", "volume_down", "scroll"]
    
    listbox = tk.Listbox(dialog, font=("Helvetica", 12), height=7, selectmode=tk.SINGLE, 
                         bg="#34495E", fg="white", selectbackground="#3498DB")
    for action in actions:
        listbox.insert(tk.END, action)
    listbox.pack(pady=5, padx=20, fill=tk.BOTH)

    selected_action = [None]

    def on_select():
        selection = listbox.curselection()
        if selection:
            selected_action[0] = listbox.get(selection[0])
        dialog.destroy()

    tk.Button(dialog, text="Confirm", command=on_select, font=("Helvetica", 10, "bold"), 
              bg="#27AE60", fg="white", width=15).pack(pady=15)

    dialog.wait_window() 
    root.destroy()
    return selected_action[0]

def trainer():
    cap = cv2.VideoCapture(0)
    tracker = HandTracker()
    cfg = ConfigManager()
    last_seen = [0, 0, 0, 0, 0]
    
    print("--- GesturaNet Universal Trainer ---")
    print("Press 'n' to map a NEW Custom App (.exe).")
    print("Press 's' to REMAP a System Control (Volume, Media, etc).")
    print("Press 'q' to Quit.")

    while cap.isOpened():
        success, img = cap.read()
        if not success: break
        img = cv2.flip(img, 1)
        img = tracker.find_hands(img)
        lm_list = tracker.get_position(img)
        
        if len(lm_list) != 0:
            last_seen = tracker.fingers_up(lm_list)

        cv2.putText(img, f"Current Fingers: {last_seen}", (10, 450), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.imshow("GesturaNet Trainer", img)
        
        key = cv2.waitKey(1) & 0xFF
        
        # 1. MAP NEW APP (.exe)
        if key == ord('n'):
            name, path = get_app_input()
            if name and path:
                cfg.update_gesture(name, last_seen)
                if "paths" not in cfg.config: cfg.config["paths"] = {}
                cfg.config["paths"][name] = path
                cfg.save_config(cfg.config)
                print(f"Success! App '{name}' mapped to {last_seen}")

        # 2. REMAP SYSTEM CONTROL
        elif key == ord('s'):
            action = get_system_input()
            if action:
                cfg.update_gesture(action, last_seen)
                print(f"Success! System Control '{action}' is now mapped to {last_seen}")
            else:
                print("Mapping canceled.")

        elif key == ord('q'): break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    trainer()