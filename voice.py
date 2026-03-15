import speech_recognition as sr
import threading
import queue
import argparse
import sys

class VoiceListener:
    def __init__(self):
        self.voice_queue = queue.Queue()
        self.is_listening = False
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        # MAXIMUM sensitivity settings
        self.recognizer.energy_threshold = 100        # Extremely sensitive to quiet speech
        self.recognizer.dynamic_energy_threshold = False # Fixed sensitive threshold
        self.recognizer.pause_threshold = 0.4         # Process immediately after very short pause
        self.recognizer.non_speaking_duration = 0.2    # Lower silence requirement

    def _listen_loop(self, testing_mode=False):
        with self.microphone as source:
            if testing_mode:
                print("Calibrating for ambient noise... Please stay quiet for 0.5 seconds.")
            # Skip ambient noise adjustment as it can sometimes mask the user
            # self.recognizer.adjust_for_ambient_noise(source, duration=0.2)
            
            if testing_mode:
                # Get device info for testing
                try:
                    import pyaudio
                    p = pyaudio.PyAudio()
                    default_device = p.get_default_input_device_info()
                    print(f"--- TESTING MODE ---")
                    print(f"Using Input Device: {default_device.get('name')}")
                    print(f"Threshold: {self.recognizer.energy_threshold}")
                    print(f"Listening for any speech... (Say 'click', 'klick', 'dabao', 'click kardo')")
                    print(f"--------------------")
                except:
                    print("Listening for speech...")

            # Common variations for Hinglish/Hindi-English users
            while self.is_listening:
                try:
                    # Listen for very short bursts (fast detection)
                    audio = self.recognizer.listen(self.microphone, timeout=0.8, phrase_time_limit=1.5)
                    text = self.recognizer.recognize_google(audio, language="en-IN").lower()
                    
                    # ALWAYS PRINT DETECTED WORDS (as requested by user)
                    print(f"[VOICE DETECTED]: {text}")
                    
                    # Broad substring matching for natural speech
                    if any(t in text for t in ["mouse mode", "chalu karo", "start mouse"]):
                        print(f"VOICE: Mouse Mode ON")
                        self.voice_queue.put("mouse_on")
                    elif any(t in text for t in ["stop mouse", "mouse stop", "band karo"]):
                        print(f"VOICE: Mouse Mode OFF")
                        self.voice_queue.put("mouse_off")
                    elif any(t in text for t in ["hold", "dabao", "daba", "rakho", "drag"]):
                        print(f"VOICE: Hold command detected (Keyword in: '{text}')")
                        self.voice_queue.put("hold")
                    elif any(t in text for t in ["release", "chhodo", "chhod", "up", "free"]):
                        print(f"VOICE: Release command detected (Keyword in: '{text}')")
                        self.voice_queue.put("release")
                    elif any(t in text for t in ["click", "dab", "press", "tap", "kardo", "klik"]):
                        print(f"VOICE: Click command detected (Keyword in: '{text}')")
                        self.voice_queue.put("click")
                        
                except sr.WaitTimeoutError:
                    continue
                except sr.UnknownValueError:
                    continue
                except Exception as e:
                    if testing_mode:
                        print(f"[ERROR]: {e}")
                    continue

    def start(self, testing_mode=False):
        self.is_listening = True
        self.thread = threading.Thread(target=self._listen_loop, args=(testing_mode,), daemon=True)
        self.thread.start()

    def get_command(self):
        if not self.voice_queue.empty():
            return self.voice_queue.get()
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Voice Recognition Module")
    parser.add_argument("--testing", action="store_true", help="Run in test mode to see all detected words")
    args = parser.parse_args()

    listener = VoiceListener()
    listener.start(testing_mode=args.testing)
    
    try:
        while True:
            # Keep main thread alive
            import time
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopping Voice Listener...")
        sys.exit()
