import cv2
import mediapipe as mp

class HandTracker:
    def __init__(self, mode=False, max_hands=1, detection_con=0.5, track_con=0.5):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(static_image_mode=mode, 
                                         max_num_hands=max_hands, 
                                         min_detection_confidence=detection_con, 
                                         min_tracking_confidence=track_con)
        self.mp_draw = mp.solutions.drawing_utils
        self.tip_ids = [8, 12, 16, 20]

    def find_hands(self, img, draw=True):
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.results = self.hands.process(img_rgb)

        if self.results.multi_hand_landmarks:
            for hand_lms in self.results.multi_hand_landmarks:
                if draw:
                    self.mp_draw.draw_landmarks(img, hand_lms, self.mp_hands.HAND_CONNECTIONS)
        return img

    def get_position(self, img):
        lm_list = []
        if self.results.multi_hand_landmarks:
            my_hand = self.results.multi_hand_landmarks[0]
            for id, lm in enumerate(my_hand.landmark):
                h, w, c = img.shape
                cx, cy = int(lm.x * w), int(lm.y * h)
                lm_list.append([id, cx, cy])
        return lm_list

    def fingers_up(self, lm_list):
        fingers = []
        if len(lm_list) != 0:
            # --- FOOLPROOF LEFT/RIGHT HAND DETECTION ---
            # We ignore MediaPipe's AI label and use spatial geometry.
            # In a mirrored camera, your Right Hand's index finger (5) 
            # will always have a smaller X coordinate than the pinky base (17).
            is_right_hand = lm_list[5][1] < lm_list[17][1]

            # 1. THUMB LOGIC
            if is_right_hand:
                if lm_list[4][1] < lm_list[3][1]: fingers.append(1)
                else: fingers.append(0)
            else:
                if lm_list[4][1] > lm_list[3][1]: fingers.append(1)
                else: fingers.append(0)

            # 2. FOUR FINGERS LOGIC (Vertical)
            for id in self.tip_ids:
                if lm_list[id][2] < lm_list[id - 2][2]:
                    fingers.append(1)
                else:
                    fingers.append(0)
        return fingers