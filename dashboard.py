import tkinter as tk
from tkinter import messagebox
import subprocess
import os
import keyboard
import sys # Add this at the top


def launch_script(script_name):
    """Launches a python script using the CURRENT interpreter."""
    if not os.path.exists(script_name):
        messagebox.showerror("Error", f"Could not find '{script_name}' in the current folder.")
        return
    try:
        # sys.executable points to the python.exe inside your (env)
        subprocess.Popen([sys.executable, script_name]) 
    except Exception as e:
        messagebox.showerror("Execution Error", f"Failed to run {script_name}.\nError: {e}")

        
def open_settings():
    """Opens the settings.json file in the default text editor."""
    if not os.path.exists("settings.json"):
        messagebox.showinfo("Info", "settings.json does not exist yet. Run the Trainer to generate it.")
        return
    try:
        # This works on Windows to open the file in Notepad/VS Code
        os.startfile("settings.json")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to open settings.json\nError: {e}")

# --- UI Setup ---
root = tk.Tk()
root.title("GesturaNet Control Panel")
root.geometry("450x400")
root.configure(bg="#1E272E") # Sleek dark gray background
root.resizable(False, False) # Lock window size

# --- UI Elements ---
# Title Area
title_label = tk.Label(root, text="GesturaNet", font=("Segoe UI", 28, "bold"), bg="#1E272E", fg="#0FB9B1")
title_label.pack(pady=(30, 0))

subtitle_label = tk.Label(root, text="Unified Gesture Control Environment", font=("Segoe UI", 10, "italic"), bg="#1E272E", fg="#808E9B")
subtitle_label.pack(pady=(0, 30))

# Button Styling
btn_style = {
    "font": ("Segoe UI", 12, "bold"), 
    "fg": "white", 
    "width": 30, 
    "height": 2,
    "bd": 0,               # Flat modern look
    "cursor": "hand2"
}

# 1. Main Engine Button
btn_main = tk.Button(root, text="▶ Start Core Engine", bg="#3867D6", activebackground="#4B7BEC", activeforeground="white", command=lambda: launch_script("main.py"), **btn_style)
btn_main.pack(pady=10)

# 2. Trainer Button
btn_train = tk.Button(root, text="⚙ Train Custom Gestures", bg="#F7B731", activebackground="#FED330", activeforeground="black", command=lambda: launch_script("trainer.py"), **btn_style)
btn_train.pack(pady=10)

# 3. View Config Button
btn_config = tk.Button(root, text="📂 View Saved Settings (.json)", bg="#20BF6B", activebackground="#26DE81", activeforeground="white", command=open_settings, **btn_style)
btn_config.pack(pady=10)

# Footer
footer = tk.Label(root, text="Group 14 Mini Project", font=("Segoe UI", 8), bg="#1E272E", fg="#485460")
footer.pack(side="bottom", pady=10)

# Run the UI Loop
root.mainloop()