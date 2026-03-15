import pyautogui
import numpy as np
import os

pyautogui.PAUSE = 0
pyautogui.FAILSAFE = False

class ActionController:
    def __init__(self):
        self.screen_w, self.screen_h = pyautogui.size()
        self.p_loc_x, self.p_loc_y = 0, 0
        self.smoothening = 4
        
        self.box_w = 200 
        self.box_h = 130 
        self.anchor_x = 320
        self.anchor_y = 240

    def center_box(self, cx, cy):
        self.anchor_x = cx
        self.anchor_y = cy

    def get_box(self):
        return (self.anchor_x - self.box_w/2, self.anchor_y - self.box_h/2,
                self.anchor_x + self.box_w/2, self.anchor_y + self.box_h/2)

    def move_mouse(self, cx, cy):
        pt1_x, pt1_y, pt2_x, pt2_y = self.get_box()

        if cx > pt2_x: self.anchor_x += (cx - pt2_x) * 1.5
        elif cx < pt1_x: self.anchor_x -= (pt1_x - cx) * 1.5
        if cy > pt2_y: self.anchor_y += (cy - pt2_y) * 1.5
        elif cy < pt1_y: self.anchor_y -= (pt1_y - cy) * 1.5

        self.anchor_x = max(self.box_w/2, min(640 - self.box_w/2, self.anchor_x))
        self.anchor_y = max(self.box_h/2, min(480 - self.box_h/2, self.anchor_y))

        pt1_x, pt1_y, pt2_x, pt2_y = self.get_box()

        x3 = np.interp(cx, (pt1_x, pt2_x), (-30, self.screen_w + 30))
        y3 = np.interp(cy, (pt1_y, pt2_y), (-30, self.screen_h + 30))

        curr_x = self.p_loc_x + (x3 - self.p_loc_x) / self.smoothening
        curr_y = self.p_loc_y + (y3 - self.p_loc_y) / self.smoothening

        pyautogui.moveTo(curr_x, curr_y)
        self.p_loc_x, self.p_loc_y = curr_x, curr_y

    def left_click(self): pyautogui.click()
    def right_click(self): pyautogui.right_click()
    def close_app(self): pyautogui.hotkey('alt', 'f4')
    def volume_up(self): pyautogui.press('volumeup')
    def volume_down(self): pyautogui.press('volumedown')
    def play_pause(self): pyautogui.press('playpause')
    def scroll(self, clicks): pyautogui.scroll(clicks)

    def launch_app(self, app_path):
        try:
            os.startfile(app_path)
        except Exception as e:
            print(f"Error opening {app_path}: {e}")