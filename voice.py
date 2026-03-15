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

    def _listen_loop(self, testing_mode=False):
        with self.microphone as source:
            if testing_mode:
                print("Calibrating for ambient noise... Please stay quiet for 1 second.")
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            
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
            click_triggers = ["click", "klick", "klik", "clic", "dabao", "dabaao", "daba", "dabayen", "dabana", "karo", "kardo", "hogy", "clicker"]

            while self.is_listening:
                try:
                    audio = self.recognizer.listen(self.microphone, timeout=1, phrase_time_limit=2)
                    text = self.recognizer.recognize_google(audio, language="en-IN").lower()
                    
                    if testing_mode:
                        print(f"[DETECTED]: {text}")
                    
                    # Check if any trigger word is in the detected text
                    if any(trigger in text for trigger in click_triggers):
                        if testing_mode:
                            print(f" >>> TRIGGER MATCHED! <<<")
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
