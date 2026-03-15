import json
import os

class ConfigManager:
    def __init__(self, filename="settings.json"):
        self.filename = filename
        # Default gestures. Users can remap these in trainer.py!
        self.default_config = {
            #"click": [0, 1, 1, 0, 0],        # Index + Middle (For clicking)
            #"browser": [0, 1, 0, 0, 0],      # Index only (For mouse movement)
            #"close_app": [0, 1, 0, 0, 1],    # Index + Pinky
            "play_pause": [1, 1, 1, 1, 1],   # Open Hand
            #"volume_up": [1, 0, 0, 0, 0],    # Thumb Only
            #"volume_down": [1, 0, 0, 0, 1],  # Thumb + Pinky
            #"scroll": [0, 1, 1, 0, 0],       # Index + Middle (If dist > 40)
            "paths": {}                      # Custom App paths go here
        }
        self.config = self.load_config()

    def load_config(self):
        """Reads the JSON file. If it doesn't exist, creates one with defaults."""
        if not os.path.exists(self.filename):
            self.save_config(self.default_config)
            return self.default_config
        try:
            with open(self.filename, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return self.default_config

    def save_config(self, new_config):
        """Writes the dictionary data into the physical JSON file."""
        with open(self.filename, 'w') as f:
            json.dump(new_config, f, indent=4)
        self.config = new_config

    def update_gesture(self, action_name, finger_list):
        """Updates a specific gesture and saves it immediately."""
        self.config[action_name] = finger_list
        self.save_config(self.config)